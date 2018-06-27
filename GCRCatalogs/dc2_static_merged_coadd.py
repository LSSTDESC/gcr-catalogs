"""
DC2 Static Merged Coadd Catalog reader
"""

import os
import re
import warnings
import numpy as np
import tables
import pandas as pd
from GCR import BaseGenericCatalog

__all__ = ['DC2StaticMergedCoaddCatalog']

class DC2StaticMergedCoaddCatalog(BaseGenericCatalog):
    r"""
    DC2 Static Merged Coadd Catalog reader

    Parameters
    ----------
    base_dir: str
    filename_pattern: str, optional (default: r'merged_tract_\d+\.hdf5')
    groupname_pattern: str, optional (default: r'coadd_\d+_\d\d$')
    use_cache : bool, optional (default: True)
    """

    _native_filter_quantities = {'tract', 'patch'}

    def _subclass_init(self, **kwargs):
        self._base_dir = kwargs.get('base_dir', '/global/projecta/projectdirs/lsst/global/in2p3/Run1.1/summary')
        self._filename_re = re.compile(kwargs.get('filename_pattern', r'merged_tract_\d+\.hdf5'))
        self._groupname_re = re.compile(kwargs.get('groupname_pattern', r'coadd_\d+_\d\d$'))
        self.use_cache = bool(kwargs.get('use_cache', True))

        if not os.path.isdir(self._base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self._base_dir))
        self._datasets, self._columns = self._generate_native_datasets_and_columns()
        if not self._datasets:
            raise RuntimeError('No catalogs were found in `base_dir` {}'.format(self._base_dir))

        self._dataset_cache = dict()

        self._quantity_modifiers = {
            'ra': 'coord_ra',
            'dec': 'coord_dec',
        }

        for band in 'ugrizy':
            self._quantity_modifiers['mag_{}_lsst'.format(band)] = '{}_mag'.format(band.lower())
            self._quantity_modifiers['magerr_{}_lsst'.format(band)] = '{}_mag_err'.format(band.lower())

    def _generate_native_datasets_and_columns(self):
        datasets = list()
        columns = set()
        for fname in sorted((f for f in os.listdir(self._base_dir) if self._filename_re.match(f))):
            fpath = os.path.join(self._base_dir, fname)
            datasets_this = list()
            columns_this = set()
            try:
                with tables.open_file(fpath, 'r') as fh:
                    for key in fh.root._v_children: #pylint: disable=W0212
                        if not self._groupname_re.match(key):
                            warnings.warn('{} does not have correct group names; skipped'.format(fname))
                            break
                        if 'axis0' not in fh.root[key]:
                            warnings.warn('{} does not have correct hdf5 format; skipped'.format(fname))
                            break
                        datasets_this.append((fpath, key))
                        columns_this.update((c.decode() for c in fh.root[key].axis0))
                    else:
                        datasets.extend(datasets_this)
                        columns.update(columns_this)
            except (IOError, OSError):
                warnings.warn('Cannot access {}; skipped'.format(fpath))
        return datasets, columns

    @staticmethod
    def get_dataset_info(dataset):
        items = dataset[1].split('_')
        return dict(tract=int(items[1]), patch=','.join(items[2]))

    @property
    def available_tracts_and_patches(self):
        return [self.get_dataset_info(dataset) for dataset in self._datasets]

    @property
    def available_tracts(self):
        return sorted(set(self.get_dataset_info(dataset)['tract'] for dataset in self._datasets))

    @property
    def base_dir(self):
        return self._base_dir

    def clear_cache(self):
        self._dataset_cache.clear()

    def _load_dataset(self, dataset):
        return pd.read_hdf(*dataset, mode='r')

    def load_dataset(self, dataset):
        if not self.use_cache:
            return self._load_dataset(dataset)
        if dataset not in self._dataset_cache:
            try:
                self._dataset_cache[dataset] = self._load_dataset(dataset)
            except MemoryError:
                self.clear_cache()
                self._dataset_cache[dataset] = self._load_dataset(dataset)
        return self._dataset_cache[dataset]

    def _generate_native_quantity_list(self):
        return self._columns.union(self._native_filter_quantities)

    def _iter_native_dataset(self, native_filters=None):
        for dataset in self._datasets:
            dataset_info = self.get_dataset_info(dataset)
            if native_filters and \
                    not all(native_filter[0](*(dataset_info[c] for c in native_filter[1:])) \
                    for native_filter in native_filters):
                continue
            d = self.load_dataset(dataset)
            def _native_quantity_getter(native_quantity):
                # pylint: disable=W0640
                if native_quantity in self._native_filter_quantities:
                    return np.repeat(dataset_info[native_quantity], len(d))
                elif native_quantity not in d:
                    return np.repeat(np.nan, len(d))
                else:
                    return d[native_quantity].values
            yield _native_quantity_getter

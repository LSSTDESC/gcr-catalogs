import os
import re
import warnings

from GCR import BaseGenericCatalog
import numpy as np
import pandas as pd
import tables

BASE_DIR = '/global/projecta/projectdirs/lsst/global/in2p3/Run1.1-test2/summary'
FILE_PATTERN = r'merged_tract_\d+\.hdf5'
GROUP_PATTERN = r'coadd_\d+_\d\d$'

__all__ = ['DC2StaticCoaddCatalog']


class DC2StaticCoaddCatalog(BaseGenericCatalog):
    _native_filter_quantities = {'tract', 'patch'}

    def _subclass_init(self,
                       base_dir=BASE_DIR,
                       filename_pattern=FILE_PATTERN,
                       groupname_pattern=GROUP_PATTERN,
                       use_cache=True,
                       **kwargs):

        self._base_dir = base_dir
        self._filename_re = re.compile(filename_pattern)
        self._groupname_re = re.compile(groupname_pattern)
        self.use_cache = bool(use_cache)

        if not os.path.isdir(self._base_dir):
            err_msg = '`base_dir` {} is not a valid directory'
            raise ValueError(err_msg.format(self._base_dir))

        self._datasets, self._columns = self._generate_native_datasets_and_columns()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self._base_dir))

        self._dataset_cache = dict()
        self._quantity_modifiers = {
            'ra': 'coord_ra',
            'dec': 'coord_dec',
        }

        for band in 'ugrizy':
            self._quantity_modifiers[
                'mag_{}_lsst'.format(band)] = '{}_mag'.format(band.lower())

            self._quantity_modifiers[
                'magerr_{}_lsst'.format(band)] = '{}_mag_err'.format(
                band.lower())

    def _generate_native_datasets_and_columns(self):
        datasets = list()
        columns = set()
        for fname in sorted((f for f in os.listdir(self._base_dir) if
                             self._filename_re.match(f))):
            fpath = os.path.join(self._base_dir, fname)
            datasets_this = list()
            columns_this = set()
            try:
                with tables.open_file(fpath, 'r') as fh:
                    for key in fh.root._v_children:
                        if not self._groupname_re.match(key):
                            warn_msg = '{} does not have correct group names; skipped'
                            warnings.warn(warn_msg.format(fname))
                            break

                        if 'axis0' not in fh.root[key]:
                            warn_msg = '{} does not have correct hdf5 format; skipped'
                            warnings.warn(warn_msg.format(fname))
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
        return sorted(set(
            self.get_dataset_info(dataset)['tract'] for dataset in
            self._datasets))

    @property
    def base_dir(self):
        return self._base_dir

    def clear_cache(self):
        self._dataset_cache = dict()

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
                    not all(native_filter[0](
                        *(dataset_info[c] for c in native_filter[1:])) \
                            for native_filter in native_filters):
                continue

            d = self.load_dataset(dataset)

            def native_quantity_getter(native_quantity):
                if native_quantity in self._native_filter_quantities:
                    return np.repeat(dataset_info[native_quantity], len(d))

                elif native_quantity not in d:
                    return np.repeat(np.nan, len(d))

                else:
                    return d[native_quantity].values

            yield native_quantity_getter

import os
import re
import warnings

from GCR import BaseGenericCatalog
import numpy as np
import pandas as pd
import tables

BASE_DIR = '/global/projecta/projectdirs/lsst/global/in2p3/Run1.1/summary'
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

        self._datasets, self._columns = self._generate_native_datasets_and_columns()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self._base_dir))

        self._dataset_cache = dict()
        self._quantity_modifiers = self._generate_modifiers()

    def _generate_native_datasets_and_columns(self):
        datasets = list()
        columns = set()
        file_list = (f for f in os.listdir(self._base_dir) if self._filename_re.match(f))
        for fname in sorted(file_list):
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

                        group = getattr(fh.root, key)
                        if 'axis0' not in group:
                            warn_msg = '{} does not have correct hdf5 format; skipped'
                            warnings.warn(warn_msg.format(fname))
                            break

                        datasets_this.append((fpath, key))
                        columns_this.update((c.decode() for c in group.axis0))

                    else:
                        datasets.extend(datasets_this)
                        columns.update(columns_this)

            except (IOError, OSError):
                warnings.warn('Cannot access {}; skipped'.format(fpath))

        return datasets, columns

    @staticmethod
    def _generate_modifiers():
        # Creates a dictionary relating native and homogenized column names

        modifiers = {
            'objectId': 'id',
            'parentObjectId': 'parent',
            'ra': 'coord_ra',
            'dec': 'coord_dec',
            'centroidX': 'slot_Centroid_x',
            'centroidY': 'slot_Centroid_y',
            'centroidX_err':'slot_Centroid_xSigma',
            'centroidY_err':'slot_Centroid_ySigma',
            'centroid_flag': 'slot_Centroid_flag',
            'psNdata': 'base_PsfFlux_area',
            'extendedness': 'base_ClassificationExtendedness_value'
        }

        for band in 'ugrizy':
            modifiers['{}_magLSST'.format(band)] = '{}_mag'.format(band)
            modifiers['{}_magLSST_err'.format(band)] = '{}_mag_err'.format(band)
            modifiers['{}_psFlux'.format(band)] = '{}_slot_ModelFlux_flux'.format(band)
            modifiers['{}_psFlux_flag'.format(band)] = '{}_slot_ModelFlux_flag'.format(band)
            modifiers['{}_psFlux_err'.format(band)] = '{}_slot_ModelFlux_fluxSigma'.format(band)

            modifiers['{}_I_flag'.format(band)] = '{}_slot_Shape_flag'.format(band)
            for ax in ['xx', 'xy', 'yy']:
                modifiers['{}_I{}'.format(band, ax)] = '{}_slot_Shape_{}'.format(band, ax)
                #modifiers['I{}Cov_{}'.format(ax, band)] = 'base_SdssShape_flux_{}_Cov'.format(ax)
                modifiers['{}_I{}PSF'.format(band, ax)] = '{}_slot_PsfShape_{}'.format(band, ax)

        return modifiers

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

            try:
                d = self.load_dataset(dataset)

            except tables.NoSuchNodeError:
                war_msg = 'Missing node for tract {}, patch {} in {} '
                warnings.warn(war_msg.format(dataset_info['tract'],
                                             dataset_info['patch'],
                                             dataset[0]))
                continue

            def native_quantity_getter(native_quantity):
                if native_quantity in self._native_filter_quantities:
                    return np.repeat(dataset_info[native_quantity], len(d))

                elif native_quantity not in d:
                    return np.repeat(np.nan, len(d))

                else:
                    return d[native_quantity].values

            yield native_quantity_getter

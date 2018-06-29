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


def calc_cov(*args):
    arg_array = np.array([a[~np.isnan(a)] for a in args])
    return np.cov(arg_array)


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
        self._dataset_cache = dict()

        self._quantity_modifiers = self.generate_modifiers()
        self._datasets, self._columns = self._generate_datasets_and_columns()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self._base_dir))

    @staticmethod
    def generate_modifiers():
        """Creates a dictionary relating native and homogenized column names

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

        modifiers = {
            'objectId': 'id',
            'parentObjectId': 'parent',
            'ra': (np.rad2deg, 'coord_ra'),
            'dec': (np.rad2deg, 'coord_dec'),
            'centroidX': 'slot_Centroid_x',
            'centroidY': 'slot_Centroid_y',
            'centroidX_err': 'slot_Centroid_xSigma',
            'centroidY_err': 'slot_Centroid_ySigma',
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
            cov_args = []
            for ax in ['xx', 'yy', 'xy']:
                cov_args.append('{}_slot_Shape_{}'.format(band, ax))
                modifiers['{}_I{}'.format(band, ax)] = '{}_slot_Shape_{}'.format(band, ax)
                modifiers['{}_I{}PSF'.format(band,ax)] = '{}_slot_PsfShape_{}'.format(band, ax)

            modifiers['{}_ICov'.format(band)] = (calc_cov, *cov_args)

        return modifiers

    @property
    def quantity_modifiers(self):
        """Return the mapping from native to homogonized value names as a dict"""

        return self._quantity_modifiers

    def _read_hdf5_meta(self, fpath):
        """Read an HDF5 file and returns the file's keys and columns

        If any formatting issues are detected, a warning is raised and the
        returned containers will be empty.

        Args:
            fpath (str): The path of the file to read

        Returns:
            A list of tuples (fpath, <key>) for all keys in the file
            A set of column names from the file
        """

        columns = set()
        data_sets = list()
        with tables.open_file(fpath, 'r') as ofile:
            for key in ofile.root._v_children:
                if not self._groupname_re.match(key):
                    warn_msg = '{} has incorrect group names; skipped'
                    warnings.warn(warn_msg.format(os.path.basename(fpath)))
                    return list(), set()

                group = getattr(ofile.root, key)
                if 'axis0' not in group:
                    warn_msg = '{} has incorrect hdf5 format; skipped'
                    warnings.warn(warn_msg.format(os.path.basename(fpath)))
                    return list(), set()

                data_sets.append((fpath, key))
                columns.update((c.decode() for c in group.axis0))

        return data_sets, columns

    def _generate_datasets_and_columns(self):
        """Return viable data sets and columns from all files in self._base_dir

        Returns:
            A list of tuples (<file path>, <key>) for all files and keys
            A set of column names from all files
        """

        datasets = list()
        columns = set()
        file_names = (f for f in os.listdir(self._base_dir) if
                      self._filename_re.match(f))
        for fname in sorted(file_names):
            fpath = os.path.join(self._base_dir, fname)

            try:
                datasets_this, columns_this = self._read_hdf5_meta(fpath)
                datasets.extend(datasets_this)
                columns.update(columns_this)

            except (IOError, OSError):
                warnings.warn('Cannot access {}; skipped'.format(fpath))

        return datasets, columns

    @staticmethod
    def get_dataset_info(dataset):
        """Return the tract and patch information for a dataset

        Args:
            dataset (tuple): Of the form (<file path (str)>, <group id (str)>)

        Returns:
            A dictionary {"tract": <tract (int)>, "patch": <patch (int)>}
        """

        items = dataset[1].split('_')
        return dict(tract=int(items[1]), patch=','.join(items[2]))

    @property
    def available_tracts_and_patches(self):
        """Return a list of available tracts and patches as dict objects

        Returns:
            A list of dictionaries of the form:
               [{"tract": <tract (int)>, "patch": <patch (int)>}, ...]
        """

        return [self.get_dataset_info(dataset) for dataset in self._datasets]

    @property
    def available_tracts(self):
        """Returns a sorted list of available tracts

        Args:
            A sorted list of available tracts as integers
        """

        tract_gen = (self.get_dataset_info(dataset)['tract'] for dataset in
                     self._datasets)
        return sorted(set(tract_gen))

    def get_patches_in_tract(self, tract):
        """Return the patches available for a given tract

        Patches are represented as strings (eg. '4,1')

        Args:
            tract (int): The desired tract id

        Returns:
            A list of available patches
        """

        patches = []
        for dataset in self._datasets:
            dataset_info = self.get_dataset_info(dataset)
            if dataset_info['tract'] == int(tract):
                patches.append(dataset_info['patch'])

        return patches

    @property
    def base_dir(self):
        """The directory where data files are stored"""

        return self._base_dir

    def clear_cache(self):
        """Empties the catalog reader cache and frees up memory allocation"""

        self._dataset_cache = dict()

    def _load_dataset(self, dataset):
        """Return the contents of an HDF5 file

        Args:
            dataset (tuple): Of the form (<file path (str)>, <group id (str)>)

        Returns:
            The contents of the specified file's group
        """

        return pd.read_hdf(*dataset, mode='r')

    def load_dataset(self, dataset):
        """Return the data table corresponding to a dataset

        Args:
            dataset (tuple): Of the form (<file path (str)>, <group id (str)>)

        Returns:
            A pandas data frame
        """

        if not self.use_cache:
            return self._load_dataset(dataset)

        if dataset not in self._dataset_cache:
            try:
                self._dataset_cache[dataset] = self._load_dataset(dataset)

            except MemoryError:
                self.clear_cache()
                self._dataset_cache[dataset] = self._load_dataset(dataset)

        return self._dataset_cache[dataset]

    def read_tract_patch(self, tract, patch):
        """Return data for a given tract and patch

        Args:
            tract (int): The desired tract id
            patch (str): The desired patch (eg. '4,1')

        Returns:
            A pandas data frame
        """

        if not int(tract) in self.available_tracts:
            raise ValueError('Invalid tract value: {}'.format(tract))

        if not patch in self.get_patches_in_tract(tract):
            err_msg = 'Invalid patch {} for tract {}'
            raise ValueError(err_msg.format(patch, tract))

        file_name = FILE_PATTERN.replace('\d+\\', str(tract))
        file_path = os.path.join(self.base_dir, file_name)
        group_id = 'coadd_4850_{}'.format(patch.replace(',', ''))

        return self.load_dataset((file_path, group_id))

    def _generate_native_quantity_list(self):
        """Return a set of native quantity names as strings"""

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

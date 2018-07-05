"""
DC2 Coadd Catalog Reader
"""

import os
import re
import warnings

import numpy as np
import pandas as pd
import tables
from GCR import BaseGenericCatalog

__all__ = ['DC2CoaddCatalog']

FILE_PATTERN = r'merged_tract_\d+\.hdf5'
GROUP_PATTERN = r'coadd_\d+_\d\d$'


def calc_cov(ixx_err, iyy_err, ixy_err):
    """Calculate the covariance between three arrays of second moments

    Args:
        ixx_err (float): The error in the second moment Ixx
        iyy_err (float): The error in the second moment Iyy
        ixy_err (float): The error in the second moment Ixy

    Returns:
        Elements of the covariance matrix ordered as
        [ixx * ixx, ixx * ixy, ixx * iyy, ixy * ixy, ixy * iyy, iyy * iyy]
    """

    # This array is missing the off-diagonal correlation coefficients
    out_data = np.array([
        ixx_err * ixx_err,
        ixx_err * ixy_err,
        ixx_err * iyy_err,
        ixy_err * ixy_err,
        ixy_err * iyy_err,
        iyy_err * iyy_err
    ])

    return out_data.transpose()


def create_basic_flag_mask(*flags):
    """
    generate a mask for a set of flags
    for each item, mask will be true if and only if all flags are false
    """
    out = np.ones(len(flags[0]), np.bool)
    for flag in flags:
        out &= (~flag)
    return out


class DC2CoaddCatalog(BaseGenericCatalog):
    r"""DC2 Coadd Catalog reader

    Parameters
    ----------
    base_dir          (str): Directory of data files being served, required
    filename_pattern  (str): The optional regex pattern of served data files
    groupname_pattern (str): The optional regex pattern of groups in data files
    use_cache         (str): Whether to cache returned data (default: True)

    Attributes
    ----------
    base_dir                      (str): The directory of data files being served
    use_cache                    (bool): Whether to cache returned data
    quantity_modifiers           (dict): The mapping from native to homogonized value names
    available_tracts             (list): Sorted list of available tracts
    available_tracts_and_patches (list): Available tracts and patches as dict objects

    Methods
    -------
    get_dataset_info               : Return the tract and patch information for a dataset
    clear_cache                    : Empty the catalog reader cache and frees up memory allocation
    """

    _native_filter_quantities = {'tract', 'patch'}

    def _subclass_init(self, **kwargs):
        self._base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', r'merged_tract_\d+\.hdf5'))
        self._groupname_re = re.compile(kwargs.get('groupname_pattern', r'coadd_\d+_\d\d$'))
        self.use_cache = bool(kwargs.get('use_cache', True))

        if not os.path.isdir(self._base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self._base_dir))

        self._dataset_cache = dict()

        self._quantity_modifiers = self._generate_modifiers()
        self._datasets, self._columns = self._generate_datasets_and_columns()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self._base_dir))

    @staticmethod
    def _generate_modifiers():
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
            'extendedness': 'base_ClassificationExtendedness_value',
        }

        modifiers['good'] = (
            create_basic_flag_mask,
            'deblend_skipped',
            'base_PixelFlags_flag_edge',
            'base_PixelFlags_flag_interpolatedCenter',
            'base_PixelFlags_flag_saturatedCenter',
            'base_PixelFlags_flag_crCenter',
            'base_PixelFlags_flag_bad',
            'base_PixelFlags_flag_suspectCenter',
            'base_PixelFlags_flag_clipped',
        )

        # cross-band average, second moment values
        modifiers['I_flag'] = 'slot_Shape_flag'
        for ax in ['xx', 'yy', 'xy']:
            modifiers['I{}'.format(ax)] = 'slot_Shape_{}'.format(ax)
            modifiers['I{}PSF'.format(ax)] = 'slot_PsfShape_{}'.format(ax)

        for band in 'ugrizy':
            modifiers['mag_{}_lsst'.format(band)] = '{}_mag'.format(band)
            modifiers['magerr_{}_lsst'.format(band)] = '{}_mag_err'.format(band)
            modifiers['{}_psFlux'.format(band)] = '{}_slot_ModelFlux_flux'.format(band)
            modifiers['{}_psFlux_flag'.format(band)] = '{}_slot_ModelFlux_flag'.format(band)
            modifiers['{}_psFlux_err'.format(band)] = '{}_slot_ModelFlux_fluxSigma'.format(band)

            # Band specific second moment values
            modifiers['{}_I_flag'.format(band)] = '{}_slot_Shape_flag'.format(band)

            for ax in ['xx', 'yy', 'xy']:
                modifiers['{}_I{}'.format(band, ax)] = '{}_slot_Shape_{}'.format(band, ax)
                modifiers['{}_I{}PSF'.format(band, ax)] = '{}_slot_PsfShape_{}'.format(band, ax)

            modifiers['{}_mag_CModel'.format(band)] = (
                lambda x: -2.5 * np.log10(x) + 27.0,
                '{}_modelfit_CModel_flux'.format(band),
            )

            modifiers['{}_SN_CModel'.format(band)] = (
                np.divide,
                '{}_modelfit_CModel_flux'.format(band),
                '{}_modelfit_CModel_fluxSigma'.format(band),
            )

            modifiers['{}_psf_size'.format(band)] = (
                lambda xx, yy, xy: 0.168 * 2.355 * (xx * yy - xy * xy) ** 0.25,
                '{}_base_SdssShape_psf_xx'.format(band),
                '{}_base_SdssShape_psf_yy'.format(band),
                '{}_base_SdssShape_psf_xy'.format(band),
            )

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
            for key in ofile.root._v_children:  # pylint: disable=W0212
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

    def _get_available_patches_in_tract(self, tract):
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
        """Empty the catalog reader cache and frees up memory allocation"""
        self._dataset_cache.clear()

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
        warnings.warn('This function is not a not GCR API, but only for convenience. '
                      'Only use this function for testing.')

        if not int(tract) in self.available_tracts:
            raise ValueError('Invalid tract value: {}'.format(tract))

        if patch not in self._get_available_patches_in_tract(tract):
            err_msg = 'Invalid patch {} for tract {}'
            raise ValueError(err_msg.format(patch, tract))

        file_name = FILE_PATTERN.replace(r'\d+', str(tract)).replace(r'\.', '.')
        file_path = os.path.join(self.base_dir, file_name)
        group_id = GROUP_PATTERN.replace(r'\d+', str(tract)).replace(r'\d\d', patch.replace(',', ''))

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

            def _native_quantity_getter(native_quantity):
                # pylint: disable=W0640
                if native_quantity in self._native_filter_quantities:
                    return np.repeat(dataset_info[native_quantity], len(d))
                elif native_quantity not in d:
                    return np.repeat(np.nan, len(d))
                else:
                    return d[native_quantity].values

            yield _native_quantity_getter

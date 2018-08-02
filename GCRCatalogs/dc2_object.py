"""
DC2 Object Catalog Reader
"""

import os
import re
import warnings

import numpy as np
import pandas as pd
import yaml
from GCR import BaseGenericCatalog

__all__ = ['DC2ObjectCatalog']

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATTERN = r'(?:merged|object)_tract_\d+\.hdf5$'
GROUP_PATTERN = r'(?:coadd|object)_\d+_\d\d$'
META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_object_meta.yaml')


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
    """Generate a mask for a set of flags

    For each item the mask will be true if and only if all flags are false

    Args:
        *flags (ndarray): Variable number of arrays with booleans or equivalent

    Returns:
        The combined mask array
    """

    out = np.ones(len(flags[0]), np.bool)
    for flag in flags:
        out &= (~flag)

    return out


class TableWrapper(object):
    """Wrapper class for pandas HDF5 storer

    Provides a unified API to access both fixed and table formats.
    """

    def __init__(self, file_handle, key):
        if not file_handle.is_open:
            raise ValueError('file handle has been closed!')

        self.storer = file_handle.get_storer(key)
        self.is_table = self.storer.is_table

        if not self.is_table and not self.storer.format_type == 'fixed':
            raise ValueError('storer format type not supported!')

        self._columns = None
        self._len = None
        self._cache = None

    @property
    def columns(self):
        if self._columns is None:
            if self.is_table:
                self._columns = set(self.storer.non_index_axes[0][1])
            else:
                self._columns = set(c.decode() for c in self.storer.group.axis0)
        return self._columns

    def __len__(self):
        if self._len is None:
            if self.is_table:
                self._len = self.storer.nrows
            else:
                self._len = self.storer.group.axis1.nrows
        return self._len

    def __contains__(self, item):
        return item in self.columns

    def __getitem__(self, key):
        if self._cache is None:
            self._cache = self.storer.read()
        return self._cache[key].values

    def clear_cache(self):
        self._cache = None


class ObjectTableWrapper(TableWrapper):
    """Same as TableWrapper but add tract and patch info"""

    def __init__(self, file_handle, key):
        key_items = key.split('_')
        self.tract = int(key_items[1])
        self.patch = ','.join(key_items[2])
        super(ObjectTableWrapper, self).__init__(file_handle, key)

    @property
    def tract_and_patch(self):
        return {'tract': self.tract, 'patch': self.patch}


class DC2ObjectCatalog(BaseGenericCatalog):
    r"""DC2 Object Catalog reader

    Parameters
    ----------
    base_dir          (str): Directory of data files being served, required
    filename_pattern  (str): The optional regex pattern of served data files
    groupname_pattern (str): The optional regex pattern of groups in data files
    pixel_scale     (float): scale to convert pixel to arcsec (default: 0.2)
    use_cache        (bool): Whether or not to cache read data in memory

    Attributes
    ----------
    base_dir                     (str): The directory of data files being served
    available_tracts             (list): Sorted list of available tracts
    available_tracts_and_patches (list): Available tracts and patches as dict objects
    """

    _native_filter_quantities = {'tract', 'patch'}

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', FILE_PATTERN))
        self._groupname_re = re.compile(kwargs.get('groupname_pattern', GROUP_PATTERN))
        self.pixel_scale = float(kwargs.get('pixel_scale', 0.2))
        self.use_cache = bool(kwargs.get('use_cache', True))

        if not os.path.isdir(self.base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self.base_dir))

        self._file_handles = dict()
        self._datasets = self._generate_datasets()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self.base_dir))

        self._columns = self._generate_columns(self._datasets)
        bands = [col[0] for col in self._columns if len(col) == 5 and col.endswith('_mag')]
        self._quantity_modifiers = self._generate_modifiers(self.pixel_scale, bands)
        self._quantity_info_dict = self._generate_info_dict(META_PATH, bands)

    def __del__(self):
        self.close_all_file_handles()

    @staticmethod
    def _generate_modifiers(pixel_scale=0.2, bands='ugrizy'):
        """Creates a dictionary relating native and homogenized column names

        Args:
            pixel_scale (float): Scale of pixels in coadd images
            bands        (list): List of photometric bands as strings

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

        modifiers = {
            'objectId': 'id',
            'parentObjectId': 'parent',
            'ra': (np.rad2deg, 'coord_ra'),
            'dec': (np.rad2deg, 'coord_dec'),
            'x': 'base_SdssCentroid_x',
            'y': 'base_SdssCentroid_y',
            'xErr': 'base_SdssCentroid_xSigma',
            'yErr': 'base_SdssCentroid_ySigma',
            'xy_flag': 'base_SdssCentroid_flag',
            'psNdata': 'base_PsfFlux_area',
            'extendedness': 'base_ClassificationExtendedness_value',
            'blendedness': 'base_Blendedness_abs_flux',
        }

        not_good_flags = (
            'base_PixelFlags_flag_edge',
            'base_PixelFlags_flag_interpolatedCenter',
            'base_PixelFlags_flag_saturatedCenter',
            'base_PixelFlags_flag_crCenter',
            'base_PixelFlags_flag_bad',
            'base_PixelFlags_flag_suspectCenter',
            'base_PixelFlags_flag_clipped',
        )

        modifiers['good'] = (create_basic_flag_mask,) + not_good_flags
        modifiers['clean'] = (
            create_basic_flag_mask,
            'deblend_skipped',
        ) + not_good_flags

        # cross-band average, second moment values
        modifiers['I_flag'] = 'ext_shapeHSM_HsmSourceMoments_flag'
        for ax in ['xx', 'yy', 'xy']:
            modifiers['I{}'.format(ax)] = 'ext_shapeHSM_HsmSourceMoments_{}'.format(ax)
            modifiers['I{}PSF'.format(ax)] = 'base_SdssShape_psf_{}'.format(ax)

        for band in bands:
            modifiers['mag_{}'.format(band)] = '{}_mag'.format(band)
            modifiers['magerr_{}'.format(band)] = '{}_mag_err'.format(band)
            modifiers['psFlux_{}'.format(band)] = '{}_base_PsfFlux_flux'.format(band)
            modifiers['psFlux_flag_{}'.format(band)] = '{}_base_PsfFlux_flag'.format(band)
            modifiers['psFluxErr_{}'.format(band)] = '{}_base_PsfFlux_fluxSigma'.format(band)
            modifiers['I_flag_{}'.format(band)] = '{}_base_SdssShape_flag'.format(band)

            for ax in ['xx', 'yy', 'xy']:
                modifiers['I{}_{}'.format(ax, band)] = '{}_base_SdssShape_{}'.format(band, ax)
                modifiers['I{}PSF_{}'.format(ax, band)] = '{}_base_SdssShape_psf_{}'.format(band, ax)

            modifiers['mag_{}_cModel'.format(band)] = (
                lambda x: -2.5 * np.log10(x) + 27.0,
                '{}_modelfit_CModel_flux'.format(band),
            )

            modifiers['magerr_{}_cModel'.format(band)] = (
                lambda flux, err: (2.5 * err) / (flux * np.log(10)),
                '{}_modelfit_CModel_flux'.format(band),
                '{}_modelfit_CModel_fluxSigma'.format(band),
            )

            modifiers['snr_{}_cModel'.format(band)] = (
                np.divide,
                '{}_modelfit_CModel_flux'.format(band),
                '{}_modelfit_CModel_fluxSigma'.format(band),
            )

            modifiers['psf_fwhm_{}'.format(band)] = (
                lambda xx, yy, xy: pixel_scale * 2.355 * (xx * yy - xy * xy) ** 0.25,
                '{}_base_SdssShape_psf_xx'.format(band),
                '{}_base_SdssShape_psf_yy'.format(band),
                '{}_base_SdssShape_psf_xy'.format(band),
            )

        return modifiers

    @staticmethod
    def _generate_info_dict(meta_path, bands='ugrizy'):
        """Creates a 2d dictionary with information for each homonogized quantity

        Separate entries for each band are created for any key in the yaml
        dictionary at meta_path containing the substring '<band>'.

        Args:
            meta_path (path): Path of yaml config file with object meta data
            bands     (list): List of photometric bands as strings

        Returns:
            Dictionary of the form
                {<homonogized value (str)>: {<meta value (str)>: <meta data>}, ...}
        """

        with open(meta_path, 'r') as ofile:
            base_dict = yaml.load(ofile)

        info_dict = dict()
        for quantity, info_list in base_dict.items():
            quantity_info = dict(
                description=info_list[0],
                unit=info_list[1],
                in_GCRbase=info_list[2],
                in_DPDD=info_list[3]
            )

            if '<band>' in quantity:
                for band in bands:
                    band_quantity = quantity.replace('<band>', band)
                    band_quantity_info = quantity_info.copy()
                    band_quantity_info['description'] = band_quantity_info['description'].replace('`<band>`','{} band'.format(band))
                    info_dict[band_quantity] = band_quantity_info

            else:
                info_dict[quantity] = quantity_info

        return info_dict

    def _get_quantity_info_dict(self, quantity, default=None):
        """Return a dictionary with descriptive information for a quantity

        Returned information includes a quantity description, quantity units, whether
        the quantity is defined in the DPDD, and if the quantity is available in GCRbase.

        Args:
            quantity   (str): The quantity to return information for
            default (object): Value to return if no information is available (default None)

        Returns:
            A dictionary with information about the provided quantity
        """

        return self._quantity_info_dict.get(quantity, default)

    def _generate_datasets(self):
        """Return viable data sets from all files in self.base_dir

        Returns:
            A list of tuples (<file path>, <key>) for all files and keys
        """

        datasets = list()
        for fname in sorted(os.listdir(self.base_dir)):
            if not self._filename_re.match(fname):
                continue

            file_path = os.path.join(self.base_dir, fname)
            try:
                fh = self._open_hdf5(file_path)

            except (IOError, OSError):
                warnings.warn('Cannot access {}; skipped'.format(file_path))
                continue

            for key in fh:
                if self._groupname_re.match(key.lstrip('/')):
                    datasets.append(ObjectTableWrapper(fh, key))
                    continue

                warn_msg = 'incorrect group name "{}" in {}; skipped this group'
                warnings.warn(warn_msg.format(os.path.basename(file_path), key))

        return datasets

    @staticmethod
    def _generate_columns(datasets):
        """Return unique column names for given datasets

        Args:
            datasets (list): A list of tuples (<file path>, <key>)

        Returns:
            A set of unique column names found in all data sets
        """

        columns = set()
        for dataset in datasets:
            columns.update(dataset.columns)

        return columns

    @property
    def available_tracts_and_patches(self):
        """Return a list of available tracts and patches as dict objects

        Returns:
            A list of dictionaries of the form:
               [{"tract": <tract (int)>, "patch": <patch (str)>}, ...]
        """

        return [dataset.tract_and_patch for dataset in self._datasets]

    @property
    def available_tracts(self):
        """Returns a sorted list of available tracts

        Returns:
            A sorted list of available tracts as integers
        """

        return sorted(set(dataset.tract for dataset in self._datasets))

    def clear_cache(self):
        """Empty the catalog reader cache and frees up memory allocation"""

        for dataset in self._datasets:
            dataset.clear_cache()

    def _open_hdf5(self, file_path):
        """Return the file handle of an HDF5 file as an pd.HDFStore object

        Cache and return the file handle for the HDF5 file at <file_path>

        Args:
            file_path (str): The path of the desired file

        Return:
            The cached file handle
        """

        if (file_path not in self._file_handles or
                not self._file_handles[file_path].is_open):
            self._file_handles[file_path] = pd.HDFStore(file_path, 'r')

        return self._file_handles[file_path]

    def close_all_file_handles(self):
        """Clear all cached file handles"""

        for fh in self._file_handles.values():
            fh.close()

        self._file_handles.clear()

    def _generate_native_quantity_list(self):
        """Return a set of native quantity names as strings"""

        return self._columns.union(self._native_filter_quantities)

    def _iter_native_dataset(self, native_filters=None):
        for dataset in self._datasets:
            if native_filters is not None and \
                    not native_filters.check_scalar(dataset.tract_and_patch):
                continue

            def _native_quantity_getter(native_quantity, d=dataset):
                try:
                    return d[native_quantity]
                except KeyError:
                    if native_quantity in self._native_filter_quantities:
                        return np.repeat(getattr(d, native_quantity), len(d))
                    return np.repeat(np.nan, len(d))

            yield _native_quantity_getter
            if not self.use_cache:
                dataset.clear_cache()

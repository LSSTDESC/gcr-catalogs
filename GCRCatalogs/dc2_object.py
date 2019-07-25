"""
DC2 Object Catalog Reader
"""

import os
import re
import warnings
import itertools
import shutil

import numpy as np
import pandas as pd
import yaml
from GCR import BaseGenericCatalog

from .dc2_dm_catalog import DC2DMTractCatalog
from .dc2_dm_catalog import convert_flux_to_nanoJansky, convert_nanoJansky_to_mag, convert_flux_err_to_mag_err

__all__ = ['DC2ObjectCatalog', 'DC2ObjectParquetCatalog']

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATTERN = r'(?:merged|object)_tract_\d+\.hdf5$'
GROUP_PATTERN = r'(?:coadd|object)_\d+_\d\d$'
SCHEMA_FILENAME = 'schema.yaml'
META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_object_meta.yaml')


def convert_dm_ref_zp_flux_to_nanoJansky(flux, dm_ref_zp=27):
    """Convert the listed DM coadd-reported flux values to nanoJansky.

    Eventually this function should be a no-op.  But presently
    The processing of Run 1.1, 1.2 to date (2019-02-17) have
    calibrated flux values with respect to a reference ZP=27 mag
    The reference catalog is on an AB system.
    Re-check dm_ref_zp if calibration is updated.
    Eventually we will get nJy from the final calibrated DRP processing.
    """
    AB_mag_zp_wrt_Jansky = 8.90  # Definition of AB
    AB_mag_zp_wrt_nanoJansky = 2.5 * 9 + AB_mag_zp_wrt_Jansky  # 9 is from nano=10**(-9)
    calibrated_flux_to_nanoJansky = 10**((AB_mag_zp_wrt_nanoJansky - dm_ref_zp)/2.5)

    return calibrated_flux_to_nanoJansky * flux


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


class TableWrapper():
    """Wrapper class for pandas HDF5 storer

    Provides a unified API to access both fixed and table formats.

    Takes a file_handle to the HDF5 file
    An HDF group key
    And a schema to specify dtypes and default values for missing columns.
    """

    _default_values = {'i': -1, 'b': False, 'U': ''}

    def __init__(self, file_handle, key, schema=None):
        if not file_handle.is_open:
            raise ValueError('file handle has been closed!')

        self.storer = file_handle.get_storer(key)
        self.is_table = self.storer.is_table

        if not self.is_table and not self.storer.format_type == 'fixed':
            raise ValueError('storer format type not supported!')

        self._schema = {} if schema is None else dict(schema)
        self._native_schema = None
        self._len = None
        self._cache = None
        self._constant_arrays = dict()

    @property
    def native_schema(self):
        """Get the native schema from either 'fixed' or 'table' formatted HDF5 files."""
        if self._native_schema is None:
            self._native_schema = {}
            if self.is_table:
                for i in itertools.count():
                    try:
                        dtype = getattr(self.storer.table.attrs, 'values_block_{}_dtype'.format(i))
                    except AttributeError:
                        break
                    for col in getattr(self.storer.table.attrs, 'values_block_{}_kind'.format(i)):
                        self._native_schema[col] = {'dtype': dtype}
            else:
                for i in range(self.storer.nblocks):
                    dtype = getattr(self.storer.group, 'block{}_values'.format(i)).dtype.name
                    for col in getattr(self.storer.group, 'block{}_items'.format(i)):
                        self._native_schema[col.decode()] = {'dtype': dtype}
        return self._native_schema

    @property
    def columns(self):
        """Get columns from either 'fixed' or 'table' formatted HDF5 files."""
        return set(self.native_schema)

    def __len__(self):
        if self._len is None:
            if self.is_table:
                self._len = self.storer.nrows
            else:
                self._len = self.storer.group.axis1.nrows
        return self._len

    def __contains__(self, item):
        return item in self.native_schema

    def __getitem__(self, key):
        """Return the values of the column specified by 'key'

        Uses cached values, if available.
        """
        if self._cache is None:
            self._cache = self.storer.read()

        try:
            return self._cache[key].values
        except KeyError:
            return self._get_constant_array(key)

    get = __getitem__

    @classmethod
    def _get_default_value(cls, dtype, key=None): # pylint: disable=W0613
        return cls._default_values.get(np.dtype(dtype).kind, np.nan)

    def _get_constant_array(self, key):
        """
        Get a constant array for a column; `key` should be the column name.
        Find dtype and default value in `self._schema`.
        If not found, default to np.float64 and np.nan.
        """
        schema_this = self._schema.get(key, {})
        dtype = schema_this.get('dtype', np.float64)
        default = schema_this.get(
            'default',
            self._get_default_value(dtype, key)
        )
        return self._generate_constant_array(dtype=dtype, value=default)

    def _generate_constant_array(self, dtype, value):
        """
        Actually generate a constant array according to `dtype` and `value`
        """
        dtype = np.dtype(dtype)
        # here `key` is used to cache the constant array
        # has nothing to do with column name
        key = (dtype.str, value)
        if key not in self._constant_arrays:
            self._constant_arrays[key] = np.asarray(np.repeat(value, len(self)), dtype=dtype)
            self._constant_arrays[key].setflags(write=False)
        return self._constant_arrays[key]

    def clear_cache(self):
        """
        clear cached data
        """
        self._native_schema = self._len = self._cache = None
        self._constant_arrays.clear()


class ObjectTableWrapper(TableWrapper):
    """Same as TableWrapper but add tract and patch info"""

    def __init__(self, file_handle, key, schema=None):
        key_items = key.split('_')
        self.tract = int(key_items[1])
        self.patch = ','.join(key_items[2])
        super(ObjectTableWrapper, self).__init__(file_handle, key, schema)
        # Add the schema info for tract, path
        # These values will be read by `get_constant_array`
        self._schema['tract'] = {'dtype': 'int64', 'default': self.tract}
        self._schema['patch'] = {'dtype': '<U', 'default': self.patch}

    @classmethod
    def _get_default_value(cls, dtype, key=None):
        if np.dtype(dtype).kind == 'b' and key and (
                key.endswith('_flag_bad') or key.endswith('_flag_noGoodPixels')):
            return True
        return super()._get_default_value(dtype, key)

    @property
    def tract_and_patch(self):
        """Return a dict of the tract and patch info."""
        return {'tract': self.tract, 'patch': self.patch}


class DC2ObjectCatalog(BaseGenericCatalog):
    r"""DC2 Object Catalog reader

    Parameters
    ----------
    base_dir          (str): Directory of data files being served, required
    filename_pattern  (str): The optional regex pattern of served data files
    groupname_pattern (str): The optional regex pattern of groups in data files
    schema_filename   (str): The optional location of the schema file
                             Relative to base_dir, unless specified as absolute path.
    pixel_scale     (float): scale to convert pixel to arcsec (default: 0.2)
    use_cache        (bool): Whether or not to cache read data in memory
    is_dpdd          (bool): Whether or not to the files are already in DPDD-format

    Attributes
    ----------
    base_dir                     (str): The directory of data files being served
    available_tracts             (list): Sorted list of available tracts
    available_tracts_and_patches (list): Available tracts and patches as dict objects

    Notes
    -----
    The initialization sets the version of the catalog based on the existence
    of certain columns and sets a version accordingly.
    This version setting should be improved and standardized as we work towardj
    providing the version in the catalog files in the scripts in `DC2-production`.
    """
    # pylint: disable=too-many-instance-attributes

    _native_filter_quantities = {'tract', 'patch'}

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', FILE_PATTERN))
        self._groupname_re = re.compile(kwargs.get('groupname_pattern', GROUP_PATTERN))

        _schema_filename = kwargs.get('schema_filename', SCHEMA_FILENAME)
        # If _schema_filename is an absolute path, os.path.join will just return _schema_filename
        self._schema_path = os.path.join(self.base_dir, _schema_filename)

        self.pixel_scale = float(kwargs.get('pixel_scale', 0.2))
        self.use_cache = bool(kwargs.get('use_cache', True))

        if not os.path.isdir(self.base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self.base_dir))

        self._schema = None
        if self._schema_path and os.path.isfile(self._schema_path):
            self._schema = self._generate_schema_from_yaml(self._schema_path)

        self._file_handles = dict()
        self._datasets = self._generate_datasets() # uses self._schema when available
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self.base_dir))

        if not self._schema:
            warnings.warn('Falling back to reading all datafiles for column names')
            self._schema = self._generate_schema_from_datafiles(self._datasets)

        if kwargs.get('is_dpdd'):
            self._quantity_modifiers = {col: None for col in self._schema}
            bands = [col[0] for col in self._schema if len(col) == 5 and col.startswith('mag_')]

        else:
            # A slightly crude way of checking for version of schema to have modelfit mag
            # A future improvement will be to explicitly store version information in the datasets
            # and just rely on that versioning.
            has_modelfit_mag = any(col.endswith('_modelfit_mag') for col in self._schema)

            if any(col.endswith('_fluxSigma') for col in self._schema):
                dm_schema_version = 1
            elif any(col.endswith('_fluxErr') for col in self._schema):
                dm_schema_version = 2
            elif any(col == 'base_Blendedness_abs_instFlux' for col in self._schema):
                dm_schema_version = 3
            else:
                dm_schema_version = 4

            bands = [col[0] for col in self._schema if len(col) == 5 and col.endswith('_mag')]

            self._quantity_modifiers = self._generate_modifiers(
                    self.pixel_scale, bands, has_modelfit_mag, dm_schema_version)

        self._quantity_info_dict = self._generate_info_dict(META_PATH, bands)
        self._len = None

    def __del__(self):
        self.close_all_file_handles()

    @staticmethod
    def _generate_modifiers(pixel_scale=0.2, bands='ugrizy',
                            has_modelfit_mag=True, dm_schema_version=4):
        """Creates a dictionary relating native and homogenized column names

        Args:
            pixel_scale (float): Scale of pixels in coadd images
            bands       (list):  List of photometric bands as strings
            has_modelfit_mag (bool): Whether or not pre-calculated model fit magnitudes are present
            dm_schema_version (int): DM schema version (1, 2, 3, 4)

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

        if dm_schema_version not in (1, 2, 3, 4):
            raise ValueError('Only supports dm_schema_version == 1, 2, 3, 4')

        FLUX = 'flux' if dm_schema_version <= 2 else 'instFlux'
        ERR = 'Sigma' if dm_schema_version <= 1 else 'Err'
        BLENDEDNESS_SUFFIX = '_%s' % FLUX if dm_schema_version <= 3 else ''

        modifiers = {
            'objectId': 'id',
            'parentObjectId': 'parent',
            'ra': (np.rad2deg, 'coord_ra'),
            'dec': (np.rad2deg, 'coord_dec'),
            'x': 'base_SdssCentroid_x',
            'y': 'base_SdssCentroid_y',
            'xErr': 'base_SdssCentroid_x{}'.format(ERR),
            'yErr': 'base_SdssCentroid_y{}'.format(ERR),
            'xy_flag': 'base_SdssCentroid_flag',
            'psNdata': 'base_PsfFlux_area',
            'extendedness': 'base_ClassificationExtendedness_value',
            'blendedness': 'base_Blendedness_abs{}'.format(BLENDEDNESS_SUFFIX),
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
            modifiers['psFlux_{}'.format(band)] = (convert_dm_ref_zp_flux_to_nanoJansky,
                                                   '{}_base_PsfFlux_{}'.format(band, FLUX))
            modifiers['psFlux_flag_{}'.format(band)] = '{}_base_PsfFlux_flag'.format(band)
            modifiers['psFluxErr_{}'.format(band)] = (convert_dm_ref_zp_flux_to_nanoJansky,
                                                      '{}_base_PsfFlux_{}{}'.format(band, FLUX, ERR))

            modifiers['I_flag_{}'.format(band)] = '{}_base_SdssShape_flag'.format(band)

            modifiers['cModelFlux_{}'.format(band)] = (convert_dm_ref_zp_flux_to_nanoJansky,
                                                       '{}_modelfit_CModel_{}'.format(band, FLUX))
            modifiers['cModelFluxErr_{}'.format(band)] = (convert_dm_ref_zp_flux_to_nanoJansky,
                                                          '{}_modelfit_CModel_{}{}'.format(band, FLUX, ERR))
            modifiers['cModelFlux_flag_{}'.format(band)] = '{}_modelfit_CModel_flag'.format(band)

            for ax in ['xx', 'yy', 'xy']:
                modifiers['I{}_{}'.format(ax, band)] = '{}_base_SdssShape_{}'.format(band, ax)
                modifiers['I{}PSF_{}'.format(ax, band)] = '{}_base_SdssShape_psf_{}'.format(band, ax)

            modifiers['psf_fwhm_{}'.format(band)] = (
                lambda xx, yy, xy: pixel_scale * 2.355 * (xx * yy - xy * xy) ** 0.25,
                '{}_base_SdssShape_psf_xx'.format(band),
                '{}_base_SdssShape_psf_yy'.format(band),
                '{}_base_SdssShape_psf_xy'.format(band),
            )

            modifiers['mag_{}_cModel'.format(band)] = '{}_modelfit_mag'.format(band)
            modifiers['magerr_{}_cModel'.format(band)] = '{}_modelfit_mag_err'.format(band)
            modifiers['snr_{}_cModel'.format(band)] = '{}_modelfit_SNR'.format(band)

            if not has_modelfit_mag:
                # The zp=27.0 is based on the default calibration for the coadds
                # as specified in the DM code.  It's correct for Run 1.1p.
                modifiers['mag_{}_cModel'.format(band)] = (
                    lambda x: -2.5 * np.log10(x) + 27.0,
                    '{}_modelfit_CModel_{}'.format(band, FLUX),
                )
                modifiers['magerr_{}_cModel'.format(band)] = (
                    lambda flux, err: (2.5 * err) / (flux * np.log(10)),
                    '{}_modelfit_CModel_{}'.format(band, FLUX),
                    '{}_modelfit_CModel_{}{}'.format(band, FLUX, ERR),
                )
                modifiers['snr_{}_cModel'.format(band)] = (
                    np.divide,
                    '{}_modelfit_CModel_{}'.format(band, FLUX),
                    '{}_modelfit_CModel_{}{}'.format(band, FLUX, ERR),
                )

        return modifiers

    @staticmethod
    def _generate_info_dict(meta_path, bands='ugrizy'):
        """Creates a 2d dictionary with information for each homogenized quantity

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
            base_dict = yaml.safe_load(ofile)

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
                    band_quantity_info['description'] = band_quantity_info['description'].replace('`<band>`', '{} band'.format(band))
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
            A list of ObjectTableWrapper(<file path>, <key>) objects
            for all files and keys
        """
        datasets = list()
        for fname in sorted(os.listdir(self.base_dir)):
            if not self._filename_re.match(fname):
                continue

            file_path = os.path.join(self.base_dir, fname)
            try:
                fh = self._open_hdf5(file_path)

            except (IOError, OSError) as e:
                warnings.warn('Cannot access {}; skipped'.format(file_path))
                print(e)
                continue

            for key in fh:
                if self._groupname_re.match(key.lstrip('/')):
                    datasets.append(ObjectTableWrapper(fh, key, self._schema))
                    continue

                warn_msg = 'incorrect group name "{}" in {}; skipped this group'
                warnings.warn(warn_msg.format(os.path.basename(file_path), key))

        return datasets

    @staticmethod
    def _generate_schema_from_yaml(schema_path):
        """Return a dictionary of columns based on schema in YAML file

        Args:
            schema_path (string): <file path> to schema file.

        Returns:
            The columns defined in the schema.
            A dictionary of {<column_name>: {'dtype': ..., 'default': ...}, ...}

        Warns:
            If one or more column names are repeated.
        """

        schema = None
        try:
            with open(schema_path, 'r') as schema_stream:
                schema = yaml.safe_load(schema_stream)
        except (IOError, OSError, yaml.YAMLError):
            pass

        if schema is None:
            warn_msg = 'No schema found or loaded in schema file {}'
            warnings.warn(warn_msg.format(schema_path))

        return schema

    @staticmethod
    def _generate_schema_from_datafiles(datasets):
        """Return the native schema for given datasets

        Args:
            datasets (list): A list of tuples (<file path>, <key>)

        Returns:
            A dict of schema ({col_name: {'dtype': dtype}}) found in all data sets
        """

        schema = {}
        for dataset in datasets:
            schema.update(dataset.native_schema)

        return schema

    def generate_schema_yaml(self, overwrite=False):
        """
        Generate the schema from the datafiles and write as a yaml file.
        This function write the schema yaml file to the schema location specified for the catalog.
        One needs to set `overwrite=True` to overwrite an existing schema file.
        """
        if self._schema_path and os.path.isfile(self._schema_path):
            if not overwrite:
                raise RuntimeError('Schema file `{}` already exists! Set `overwrite=True` to overwrite.'.format(self._schema_path))
            warnings.warn('Overwriting schema file `{0}`, which is backed up at `{0}.bak`'.format(self._schema_path))
            shutil.copyfile(self._schema_path, self._schema_path + '.bak')

        schema = self._generate_schema_from_datafiles(self._datasets)

        for col, schema_this in schema.items():
            if np.dtype(schema_this['dtype']).kind == 'b' and (
                    col.endswith('_flag_bad') or col.endswith('_flag_noGoodPixels')):
                schema_this['default'] = True

        with open(self._schema_path, 'w') as schema_stream:
            yaml.dump(schema, schema_stream)

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

        return set(self._schema).union(self._native_filter_quantities)

    def _iter_native_dataset(self, native_filters=None):
        # pylint: disable=C0330
        for dataset in self._datasets:
            if (native_filters is None or
                native_filters.check_scalar(dataset.tract_and_patch)):
                yield dataset.get
                if not self.use_cache:
                    dataset.clear_cache()

    def __len__(self):
        if self._len is None:
            # pylint: disable=attribute-defined-outside-init
            self._len = sum(len(dataset) for dataset in self._datasets)
        return self._len


class DC2ObjectParquetCatalog(DC2DMTractCatalog):
    r"""DC2 Object (Parquet) Catalog reader

    Parameters
    ----------
    base_dir          (str): Directory of data files being served, required
    filename_pattern  (str): The optional regex pattern of served data files
    is_dpdd          (bool): File are already in DPDD-format.  No translation.

    Attributes
    ----------
    base_dir          (str): The directory of data files being served

    Notes
    -----
    """
    # pylint: disable=too-many-instance-attributes
    FILE_DIR = FILE_DIR
    FILE_PATTERN = r'object_tract_\d+\.parquet$'
    META_PATH = META_PATH

    def _subclass_init(self, **kwargs):

        # hack to skip the call of `_generate_modifiers` in the base class
        # TODO: fix this some day
        super()._subclass_init(**dict(kwargs, is_dpdd=True))

        self.pixel_scale = float(kwargs.get('pixel_scale', 0.2))

        if kwargs.get('is_dpdd'):
            self._quantity_modifiers = {col: None for col in self._columns}
        else:
            # The following is in principle fragile, but in practice we
            bands = [col[-1] for col in self._columns if len(col) == 8 and col.beginswith('psFlux_')]

            self._quantity_modifiers = self._generate_modifiers(
                self.pixel_scale, bands)

    @staticmethod
    def _generate_modifiers(pixel_scale=0.2, bands='ugrizy'):
        """Creates a dictionary relating native and homogenized column names

        Args:
            pixel_scale (float): Scale of pixels in coadd images
            bands       (list):  List of photometric bands as strings

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

        FLUX = 'instFlux'
        ERR = 'Err'

        modifiers = {
            'objectId': 'id',
            'parentObjectId': 'parent',
            'ra': (np.rad2deg, 'coord_ra'),
            'dec': (np.rad2deg, 'coord_dec'),
            'x': 'base_SdssCentroid_x',
            'y': 'base_SdssCentroid_y',
            'xErr': f'base_SdssCentroid_x{ERR}',
            'yErr': f'base_SdssCentroid_y{ERR}',
            'xy_flag': 'base_SdssCentroid_flag',
            'psNdata': 'base_PsfFlux_area',
            'extendedness': 'base_ClassificationExtendedness_value',
            'blendedness': 'base_Blendedness_abs',
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
            modifiers[f'I{ax}'] = f'ext_shapeHSM_HsmSourceMoments_{ax}'
            modifiers[f'I{ax}PSF'] = f'base_SdssShape_psf_{ax}'

        for band in bands:
            modifiers[f'psFlux_{band}'] = (convert_flux_to_nanoJansky,
                                           f'{band}_base_PsfFlux_{FLUX}')
            modifiers[f'psFlux_flag_{band}'] = f'{band}_base_PsfFlux_flag'
            modifiers[f'psFluxErr_{band}'] = (convert_dm_ref_zp_flux_to_nanoJansky,
                                              f'{band}_base_PsfFlux_{FLUX}{ERR}')
            modifiers[f'mag_{band}'] = (convert_nanoJansky_to_mag,
                                        f'psFlux_{band}')
            modifiers[f'magerr_{band}'] = (convert_flux_err_to_mag_err,
                                           f'psFlux_{band}',
                                           f'psFluxErr_{band}')

            modifiers[f'cModelFlux_{band}'] = (convert_dm_ref_zp_flux_to_nanoJansky,
                                               f'{band}_modelfit_CModel_{FLUX}')
            modifiers[f'cModelFluxErr_{band}'] = (convert_dm_ref_zp_flux_to_nanoJansky,
                                                  f'{band}_modelfit_CModel_{FLUX}{ERR}')
            modifiers[f'cModelFlux_flag_{band}'] = (convert_flux_err_to_mag_err,
                                                    f'{band}_modelfit_CModel_flag')
            modifiers[f'mag_{band}_cModel'] = (convert_nanoJansky_to_mag,
                                               f'cModelFlux_{band}')
            modifiers[f'magerr_{band}_cModel'] = (convert_flux_err_to_mag_err,
                                                  f'cModelFlux_{band}',
                                                  f'cModelFluxErr_{band}')

            # Per-band shape information
            modifiers[f'I_flag_{band}'] = f'{band}_base_SdssShape_flag'

            for ax in ['xx', 'yy', 'xy']:
                modifiers[f'I{ax}_{band}'] = f'{band}_base_SdssShape_{ax}'
                modifiers[f'I{ax}PSF_{band}'] = f'{band}_base_SdssShape_psf_{ax}'

            modifiers[f'psf_fwhm_{band}'] = (
                lambda xx, yy, xy: pixel_scale * 2.355 * (xx * yy - xy * xy) ** 0.25,
                f'IxxPSF_{band}', f'IyyPSF_{band}', f'IxyPSF_{band}')

        return modifiers


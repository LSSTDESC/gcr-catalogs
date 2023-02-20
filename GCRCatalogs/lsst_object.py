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
from .utils import decode

__all__ = ['LSSTCatalog']

#        'DC2ObjectCatalog', 'DC2ObjectParquetCatalog','DP02ObjectParquetCatalog','DP02TruthMatchCatalog','DP02TruthParquetCatalog','CosmoDC2AddonCatalog']

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATTERN = r'(?:merged|object)_tract_\d+\.hdf5$'
GROUP_PATTERN = r'(?:coadd|object)_\d+_\d\d$'
SCHEMA_FILENAME = 'schema.yaml'
META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_object_meta.yaml')



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
                        self._native_schema[decode(col)] = {'dtype': dtype}
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
    def _get_default_value(cls, dtype, key=None):  # pylint: disable=W0613
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


class LSSTCatalog(DC2DMTractCatalog):
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

        self.FILE_PATTERN = r'object_tract_\d+\.parquet$'
        self.META_PATH = META_PATH
        self._default_pixel_scale = 0.2
        self.pixel_scale = float(kwargs.get('pixel_scale', self._default_pixel_scale))

        super()._subclass_init(**kwargs)

    def _detect_available_bands(self):
        """
        This method should return available bands in the catalog file.
        For object catalog files generated by DC2-production/scripts/make_object_catalog.py,
        columns `<band>_FLUXMAG0` would exist.
        For DPDD-only object catalog files generated by DC2-production/scripts/write_gcr_to_parquet.py,
        columns `psFlux_<band>` would exist.
        This function first checks for `<band>_FLUXMAG0` columns.
        If none exists, then checks for `psFlux_<band>` columns.
        If neither set of columns exists, it returns an empty list.
        Note that band name may contain underscores.
        """
        return (
            [col.rpartition('_')[0] for col in self._columns if col.endswith('_FLUXMAG0')] or
            [col.partition('_')[2] for col in self._columns if col.startswith('psFlux_')]
        )

    def _subclass_init(self, **kwargs):

        self.FILE_PATTERN = r'object_tract_\d+\.parquet$'
        self.META_PATH = META_PATH
        self._default_pixel_scale = 0.2
        self.pixel_scale = float(kwargs.get('pixel_scale', self._default_pixel_scale))

        super()._subclass_init(**kwargs)

    def __del__(self):
        self.close_all_file_handles()

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


    @staticmethod
    def _generate_modifiers(pixel_scale=0.2, bands='ugrizy',
                            has_modelfit_mag=True, has_modelfit_flux=True, has_modelfit_flag=True,
                            dm_schema_version=4):
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

        modifiers = {}


        # cross-band average, second moment values

        return modifiers


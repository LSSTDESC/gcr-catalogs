"""
Rubin LSST Object Catalog Reader
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

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_lsst_object_meta.yaml')


class LSSTCatalog(DC2DMTractCatalog):
    r"""Rubin LSST Object Catalog reader

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
    This is a preliminary catalog wrapper for use of the LSST DP0.2 object catalogs 
    in their native form. 
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
        This method should return available bands in the catalog file.a
        These object catalogs should match the schema found here
        https://dm.lsst.org/sdm_schemas/browser/dp02.html
        which has band_psfFlux columns.
        """
        return (
            [col.rpartition('_')[0] for col in self._columns if col.endswith('_psfFlux')] 
        )

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




"""
DC2 Forced Source Catalog Reader
"""

import os
import re
import warnings
import shutil

import numpy as np
import pyarrow.parquet as pq
import yaml

from GCR import BaseGenericCatalog
from .dc2_catalog import DC2Catalog

__all__ = ['DC2ForcedSourceCatalog']

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATTERN = r'fourced_source_visit_\d+\.parquet$'
SCHEMA_FILENAME = 'schema.yaml'
META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_forced_source_meta.yaml')


class DC2ForcedSourceCatalog(DC2Catalog):
    r"""DC2 Forced Source Catalog reader

    Parameters
    ----------
    base_dir          (str): Directory of data files being served, required
    filename_pattern  (str): The optional regex pattern of served data files
    use_cache        (bool): Cache read data in memory
    is_dpdd          (bool): File are already in DPDD-format.  No translation.

    Attributes
    ----------
    base_dir          (str): The directory of data files being served

    Notes
    -----
    """
    # pylint: disable=too-many-instance-attributes

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', FILE_PATTERN))
        self.use_cache = bool(kwargs.get('use_cache', True))

        if not os.path.isdir(self.base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self.base_dir))

        _schema_filename = kwargs.get('schema_filename', SCHEMA_FILENAME)
        # If _schema_filename is an absolute path, os.path.join will just return _schema_filename
        self._schema_path = os.path.join(self.base_dir, _schema_filename)

        self._schema = None
        if self._schema_path and os.path.isfile(self._schema_path):
            self._schema = self._generate_schema_from_yaml(self._schema_path)

        self._file_handles = dict()
        self._datasets = self._generate_datasets()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self.base_dir))

        if not self._schema:
            warnings.warn('Falling back to reading all datafiles for column names')
            self._schema = self._generate_schema_from_datafiles(self._datasets)

        if kwargs.get('is_dpdd'):
            self._quantity_modifiers = {col: None for col in self._schema}
        else:
            if any(col.endswith('_fluxSigma') for col in self._schema):
                dm_schema_version = 1
            elif any(col.endswith('_fluxErr') for col in self._schema):
                dm_schema_version = 2
            else:
                dm_schema_version = 3

            self._quantity_modifiers = self._generate_modifiers(dm_schema_version)

        self._quantity_info_dict = self._generate_info_dict(META_PATH)
        self._native_filter_quantities = self._generate_native_quantity_list()

    @staticmethod
    def _generate_modifiers(dm_schema_version=3):
        """Creates a dictionary relating native and homogenized column names

        Args:
            dm_schema_version (int): DM schema version (1, 2, or 3)

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

        if dm_schema_version not in (1, 2, 3):
            raise ValueError('Only supports dm_schema_version == 1, 2, or 3')

        flux_name = 'flux' if dm_schema_version <= 2 else 'instFlux'
        flux_err_name = 'Sigma' if dm_schema_version <= 1 else 'Err'

        modifiers = {
            'visit': 'visit',
            'detector': 'detector',
            'filter': 'filter',
            'id': 'id',
            'objectId': 'objectId',
            'psFlux': (convert_flux_to_nanoJansky,
                       'base_PsfFlux_{}'.format(flux_name),
                       'fluxmag0'),
            'psFluxErr': (convert_flux_to_nanoJansky,
                          'base_PsfFlux_{}{}'.format(flux_name, flux_err_name),
                          'fluxmag0'),
            'psFlux_flag': 'base_PsfFlux_flag',
            'mag': 'mag',
            'magerr': 'mag_err',
            'fluxmag0': 'fluxmag0',
        }

        not_good_flags = (
            'base_PixelFlags_flag_edge',
            'base_PixelFlags_flag_interpolatedCenter',
            'base_PixelFlags_flag_saturatedCenter',
            'base_PixelFlags_flag_crCenter',
            'base_PixelFlags_flag_bad',
            'base_PixelFlags_flag_suspectCenter',
        )

        modifiers['good'] = (create_basic_flag_mask,) + not_good_flags
        modifiers['clean'] = modifiers['good']  # No distinction for forced

        return modifiers

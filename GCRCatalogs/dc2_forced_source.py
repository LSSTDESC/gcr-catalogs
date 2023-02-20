"""
DC2 Forced Source Catalog Reader
"""

import os

from .dc2_dm_catalog import DC2DMVisitCatalog, convert_flux_to_nanoJansky, create_basic_flag_mask

__all__ = ['DC2ForcedSourceCatalog']


class DC2ForcedSourceCatalog(DC2DMVisitCatalog):
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

    FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    FILE_PATTERN = r'fourced_source_visit_\d+\.parquet$'
    META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_forced_source_meta.yaml')

    @staticmethod
    def _generate_modifiers(dm_schema_version=3, **kwargs):
        """Creates a dictionary relating native and homogenized column names

        Args:
            dm_schema_version (int): DM schema version (1, 2, or 3)

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

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

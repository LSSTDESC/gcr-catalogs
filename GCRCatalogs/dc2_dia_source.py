"""
DC2 Source Catalog Reader
"""

import os

import numpy as np

from .dc2_dm_catalog import DC2DMVisitCatalog, convert_flux_to_nanoJansky, create_basic_flag_mask

__all__ = ['DC2DiaSourceCatalog']


class DC2DiaSourceCatalog(DC2DMVisitCatalog):
    r"""DC2 DIA Source Catalog reader

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
    FILE_PATTERN = r'dia_src_visit_\d+\.parquet$'
    META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_dia_source_meta.yaml')

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
            'diaSourceId': 'id',
            'diaObjectId': 'objectId',
            'visit': 'visit',
            'mjd': 'mjd',
            'filter': 'filter',
            'detector': 'detector',
            'parentDiaSourceId': 'parent',
#            'midPointTai': 'dateobs'?  I don't know what this is called
            'ra': (np.rad2deg, 'coord_ra'),
            'dec': (np.rad2deg, 'coord_dec'),
            'x': 'slot_Centroid_x',
            'y': 'slot_Centroid_y',
            'xErr': 'slot_Centroid_xErr',
            'yErr': 'slot_Centroid_yErr',
            'apFlux': (convert_flux_to_nanoJansky,
                       'slot_ApFlux_{}'.format(flux_name),
                       'fluxmag0'),
            'apFluxErr': (convert_flux_to_nanoJansky,
                          'slot_ApFlux_{}{}'.format(flux_name, flux_err_name),
                          'fluxmag0'),
            'psFlux': (convert_flux_to_nanoJansky,
                       'slot_PsfFlux_{}'.format(flux_name),
                       'fluxmag0'),
            'psFluxErr': (convert_flux_to_nanoJansky,
                          'slot_PsfFlux_{}{}'.format(flux_name, flux_err_name),
                          'fluxmag0'),
            'dipAngle': 'ip_diffim_DipoleFit_orientation',
            'dipChi2': 'ip_diffim_DipoleFit_chi2dof',
            'totFlux': 'ip_diffim_forced_PsfFlux_instFlux',
            'totFluxErr': 'ip_diffim_forced_PsfFlux_instFluxErr',
            'isDipole': 'ip_diffim_DipoleFit_flag_classification',
            'ixyPSF': 'slot_PsfShape_xy',
            'xy_flag': 'slot_Centroid_flag',
            'I_flag': 'slot_Shape_flag',
            'Ixx': 'slot_Shape_xx',
            'IxxPSF': 'slot_PsfShape_xx',
            'Iyy': 'slot_Shape_yy',
            'IyyPSF': 'slot_PsfShape_yy',
            'Ixy': 'slot_Shape_xy',
            'IxyPSF': 'slot_PsfShape_xy',
            'mag': 'mag',
            'magerr': 'mag_err',
            'fluxmag0': 'fluxmag0',
            'apFlux_flag': 'slot_ApFlux_flag',
            'psFlux_flag': 'slot_PsfFlux_flag',
            'psNdata': 'slot_PsfFlux_area',
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
        modifiers['clean'] = modifiers['good']

        return modifiers

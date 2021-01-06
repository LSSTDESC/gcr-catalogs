"""
DC2 Source Catalog Reader
"""

import os

import numpy as np

from .dc2_dm_catalog import DC2DMVisitCatalog, convert_flux_to_nanoJansky, create_basic_flag_mask

__all__ = ['DC2SourceCatalog']


class DC2SourceCatalog(DC2DMVisitCatalog):
    r"""DC2 Source Catalog reader

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
    FILE_PATTERN = r'source_visit_\d+\.parquet$'
    META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_source_meta.yaml')

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
            'sourceId': 'id',
            'visit': 'visit',
            'detector': 'detector',
            'filter': 'filter',
            'objectId': 'objectId',
            'parentObjectId': 'parent',
            'ra': (np.rad2deg, 'coord_ra'),
            'dec': (np.rad2deg, 'coord_dec'),
            'x': 'slot_Centroid_x',
            'y': 'slot_Centroid_y',
            'xErr': 'slot_Centroid_x{}'.format(flux_err_name),
            'yErr': 'slot_Centroid_y{}'.format(flux_err_name),
            'xy_flag': 'slot_Centroid_flag',
            'sky': (convert_flux_to_nanoJansky,
                    'base_LocalBackground_{}'.format(flux_name),
                    'fluxmag0'),
            'skyErr': (convert_flux_to_nanoJansky,
                       'base_LocalBackground_{}{}'.format(flux_name, flux_err_name),
                       'fluxmag0'),
            'sky_flag': 'base_LocalBackground_flag',
            'I_flag': 'slot_Shape_flag',
            'Ixx_pixel': 'slot_Shape_xx',
            'IxxPSF_pixel': 'slot_PsfShape_xx',
            'Iyy_pixel': 'slot_Shape_yy',
            'IyyPSF_pixel': 'slot_PsfShape_yy',
            'Ixy_pixel': 'slot_Shape_xy',
            'IxyPSF_pixel': 'slot_PsfShape_xy',
            'mag': 'mag',
            'magerr': 'mag_err',
            'fluxmag0': 'fluxmag0',
            'apFlux': (convert_flux_to_nanoJansky,
                       'slot_ApFlux_{}'.format(flux_name),
                       'fluxmag0'),
            'apFluxErr': (convert_flux_to_nanoJansky,
                          'slot_ApFlux_{}{}'.format(flux_name, flux_err_name),
                          'fluxmag0'),
            'apFlux_flag': 'slot_ApFlux_flag',
            'psFlux': (convert_flux_to_nanoJansky,
                       'slot_PsfFlux_{}'.format(flux_name),
                       'fluxmag0'),
            'psFluxErr': (convert_flux_to_nanoJansky,
                          'slot_PsfFlux_{}{}'.format(flux_name, flux_err_name),
                          'fluxmag0'),
            'psFlux_flag': 'slot_PsfFlux_flag',
            'psNdata': 'slot_PsfFlux_area',
            'psf_fwhm_pixel': (
                lambda xx, yy, xy: 2.355 * (xx * yy - xy * xy) ** 0.25,
                'slot_PsfShape_xx',
                'slot_PsfShape_yy',
                'slot_PsfShape_xy',
            ),
            # There are no 'slot_*' values for the extendedness and blendedness
            # in the Run 1.2i processing (as of 2019-03-05)
            'extendedness': 'base_ClassificationExtendedness_value',
            'blendedness': 'base_Blendedness_abs_{}'.format(flux_name),
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
        modifiers['clean'] = (
            create_basic_flag_mask,
            'deblend_skipped',
        ) + not_good_flags

        return modifiers

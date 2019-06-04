"""
DC2 DIA Object Catalog Reader
"""

import os
import re
import warnings

import numpy as np

from .dc2_dm_catalog import DC2DMCatalog, convert_flux_to_nanoJansky, create_basic_flag_mask


__all__ = ['DC2DiaObjectCatalog']


class DC2DiaObjectCatalog(DC2DMCatalog):
    r"""DC2 DIA Object Catalog reader

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
    FILE_PATTERN = r'dia_object_\d+\.parquet$'
    SCHEMA_FILENAME = 'schema.yaml'
    META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_dia_object_meta.yaml')

    @staticmethod
    def _generate_modifiers(dm_schema_version=3, bands='ugrizy'):
        """Creates a dictionary relating native and homogenized column names

        Args:
            dm_schema_version (int): DM schema version (1, 2, or 3)

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """
        # Quantities defined in the DPDD but that we don't know how
        # to calculate yet are commented out in the dict below.
        # Based on the LSST DPDD 2018-10-24 +
        # https://jira.lsstcorp.org/browse/RFC-517
        #    which clarifies DIASource vs DIAForceSource
        #    and how to calculate various DIAObject properties based on DIASources
        modifiers = {
            'diaObjectId': 'dia_object_id',
            'ra': (np.rad2deg, 'coord_ra'),
            'dec': (np.rad2deg, 'coord_dec'),
#            'radecCov': A covariance matrix for the uncertainty in ra, dec
#            'radecTai': 'dateobs'?  I don't know what this is called
# 'pm': 
# 'pmParallaxCov': 
# 'pmParallaxLnl': 
# 'pmParallaxChi2': 
# 'pmParallaxNdata': 
#            'psFluxMean': (convert_flux_to_nanoJansky,
#                           'slot_PsfFlux_{}'.format(flux_name),
#                           'fluxmag0'),
#            'psFluxMeanErr': (convert_flux_to_nanoJansky,
#                              'slot_PsfFlux_{}{}'.format(flux_name, flux_err_name),
#                              'fluxmag0'),
#            'psFluxSigma':  # std of distribution of psFlux
#            'psFluxChi2':
#            'psFluxNdata':
#            'totFluxMean': 'ip_diffim_forced_PsfFlux_instFlux',
#            'totFluxMeanErr': 'ip_diffim_forced_PsfFlux_instFluxErr',
#            'totFluxSigma': 'ip_diffim_forced_PsfFlux_instFluxErr',
#  'lcPeriodic'
#  'lcNonPeriodic'
#  These are possible to calculate if you require the Object Table
#            'nearbyObj':
#            'nearbyObjDist':
#            'nearbyObjLnP':
        }

        modifiers['good'] = (create_basic_flag_mask,)
        modifiers['clean'] = modifiers['good']

        for band in bands:
            modifiers['mag_{}'.format(band)] = '{}_mag'.format(band)
            modifiers['magerr_{}'.format(band)] = '{}_mag_err'.format(band)
            modifiers['psFluxMean_{}'.format(band)] = (convert_flux_to_nanoJansky,
                                                       '{}_base_PsfFlux_{}'.format(band, FLUX))
            modifiers['psFluxMean_flag_{}'.format(band)] = '{}_base_PsfFlux_flag'.format(band)
            modifiers['psFluxMeanErr_{}'.format(band)] = (convert_flux_to_nanoJansky,
                                                          '{}_base_PsfFlux_{}{}'.format(band, FLUX, ERR))
#            modifiers['psFluxSigma_{}'.format(band)] = (convert_flux_to_nanoJansky,
#                                                          '{}_base_PsfFlux_{}{}'.format(band, FLUX, ERR))
            modifiers['totFluxMean_{}'.format(band)] = (convert_flux_to_nanoJansky,
                                                       '{}_base_PsfFlux_{}'.format(band, FLUX))
            modifiers['totFluxMean_flag_{}'.format(band)] = '{}_base_PsfFlux_flag'.format(band)
            modifiers['totFluxMeanErr_{}'.format(band)] = (convert_flux_to_nanoJansky,
                                                          '{}_base_PsfFlux_{}{}'.format(band, FLUX, ERR))

        return modifiers

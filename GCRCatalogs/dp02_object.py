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
from .dc2_dm_catalog import convert_flux_to_mag, convert_flux_to_nanoJansky, convert_nanoJansky_to_mag, convert_flux_err_to_mag_err
from .utils import decode

__all__ = ['DP02ObjectParquetCatalog']

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATTERN = r'(?:merged|object)_tract_\d+\.hdf5$'
GROUP_PATTERN = r'(?:coadd|object)_\d+_\d\d$'
SCHEMA_FILENAME = 'schema.yaml'
META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_object_meta.yaml')


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




class DP02ObjectParquetCatalog(DC2DMTractCatalog):
    r"""DC2 Object (Parquet) Catalog reader

    Parameters
    ----------
    base_dir          (str): Directory of data files being served, required
    filename_pattern  (str): The optional regex pattern of served data files
    is_dpdd          (bool): File are already in DPDD-format.  No translation.

    Attributes
    ----------
    base_dir          (str): The directory of data files being served
    """

    def _subclass_init(self, **kwargs):

        self.FILE_PATTERN = r'objectTable_tract_\d+\_DC2_2_2i_runs_DP0_2_v23_0_1_PREOPS-905_step3_\d+_\w+Z.parq$'
        self.META_PATH = META_PATH
        self._default_pixel_scale = 0.2
        self.pixel_scale = float(kwargs.get('pixel_scale', self._default_pixel_scale))

        super()._subclass_init(**kwargs)

    def _detect_available_bands(self):
        """
        This method should return available bands in the catalog file.
    
        For the DP02 catalog columns `<band>_psfFlux` should exist. 
        This function checks for `psFlux_<band>` columns.
        If columns do not exist, it returns an empty list.
        Note that band name may contain underscores. 
        There are bands labelled, e.g. r_free in this output
        """
        return (
            [col.partition('_')[0] for col in self._columns if col.endswith('_psfFlux')]
        )

    @staticmethod
    def _generate_modifiers(dm_schema_version=5, bands=None, pixel_scale=0.2, **kwargs):  # pylint: disable=arguments-differ
        """Creates a dictionary relating native and homogenized column names

        Args:
            pixel_scale (float): Scale of pixels in coadd images
            bands       (list):  List of photometric bands as strings

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

        bands = bands or 'ugrizy'
        FLUX = 'Flux'
        ERR = 'Err'


        modifiers = {
            'objectId': 'objectId', #I think this doesn't exist for this catalog 
            'parentObjectId': 'parentObjectId',
            'ra':  'coord_ra',
            'dec':  'coord_dec',
            'x': 'x',
            'y': 'y',
            'xErr': f'x{ERR}',
            'yErr': f'y{ERR}',
            'xy_flag': 'xy_flag',
            'psNdata': 'base_psfFlux_area', # now band-specific 
            'extendedness': 'refExtendedness', # band-specific, not sure what the ref one is
            'blendedness': 'base_blendedness', # band-specific  
        }

        not_good_flags = (
            # do we have any "not good" flags?
            # r_pixelFlags_clipped is an option here 
            'z_pixelFlags_sensor_edge', # just adding one in case it crashes otherwise
            'detect_isDeblendedSource',
            #'detect_isPrimary',
            #'detect_isTractInner',
            #'base_PixelFlags_flag_edge',
            #'base_PixelFlags_flag_interpolatedCenter',
            #'base_PixelFlags_flag_saturatedCenter',
            #'base_PixelFlags_flag_crCenter',
            #'base_PixelFlags_flag_bad',
            #'base_PixelFlags_flag_suspectCenter',
            #'base_PixelFlags_flag_clipped',
        )

        modifiers['good'] = (create_basic_flag_mask,) + not_good_flags
        modifiers['clean'] = (
            create_basic_flag_mask,
            'deblend_skipped',
        ) + not_good_flags

        # cross-band average, second moment values
        modifiers['I_flag'] = 'shape_flag'

        for ax in ['xx', 'yy', 'xy']:
            modifiers[f'I{ax}_pixel'] = f'shape_{ax}'
            #modifiers[f'I{ax}PSF_pixel'] = f'base_SdssShape_psf_{ax}'

        for band in bands:
            # NOTE: for this catalog all flux units are in nJy
            # this differs from the previous dm object catalog
            
            modifiers[f'psFlux_{band}'] = f'{band}_psf{FLUX}'
            modifiers[f'psFlux_flag_{band}'] = f'{band}_psf{FLUX}_flag'
            
            modifiers[f'psFluxErr_{band}'] = f'{band}_psf{FLUX}{ERR}'
            
            modifiers[f'mag_{band}'] = (convert_nanoJansky_to_mag,  
                                           f'{band}_psf{FLUX}')
            
            modifiers[f'magerr_{band}'] = (convert_flux_err_to_mag_err,
                                           f'{band}_psf{FLUX}', 
                                           f'{band}_psf{FLUX}{ERR}')
                                           
            modifiers[f'cModelFlux_{band}'] = f'{band}_cModel{FLUX}'
            modifiers[f'cModelFluxErr_{band}'] = f'{band}_cModel{FLUX}{ERR}'
            
    
            modifiers[f'cModelFlux_flag_{band}'] = f'{band}_cModel_flag'
        
            modifiers[f'mag_{band}_cModel'] = (convert_nanoJansky_to_mag,
                                               f'{band}_cModel{FLUX}')

            modifiers[f'magerr_{band}_cModel'] = (convert_flux_err_to_mag_err,
                                                  f'{band}_cModel{FLUX}',
                                                  f'{band}_cModel{FLUX}{ERR}')
            
            modifiers[f'snr_{band}_cModel'] = (np.divide,
                                               f'{band}_cModel{FLUX}',
                                               f'{band}_cModel{FLUX}{ERR}')

            # Per-band shape information
            modifiers[f'I_flag_{band}'] = f'{band}_i_flag'

            for ax in ['xx', 'yy', 'xy']:
                modifiers[f'I{ax}_pixel_{band}'] = f'{band}_i{ax}'
                modifiers[f'I{ax}PSF_pixel_{band}'] = f'{band}_i{ax}PSF'

            modifiers[f'psf_fwhm_{band}'] = (
                lambda xx, yy, xy: pixel_scale * 2.355 * (xx * yy - xy * xy) ** 0.25,
                f'{band}_ixxPSF',
                f'{band}_iyyPSF',
                f'{band}_ixyPSF') # need to check if this holds 

        return modifiers

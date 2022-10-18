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

def shear_from_moments(Ixx,Ixy,Iyy,kind='eps'):
    '''
    Get shear components from second moments
    '''
    if kind=='eps':
        denom = Ixx + Iyy + 2.*np.sqrt(Ixx*Iyy - Ixy**2)
    elif kind=='chi':
        denom = Ixx + Iyy
    return (Ixx-Iyy)/denom, 2*Ixy/denom


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
            'psNdata': 'r_psfFlux_area', # now band-specific 
            'extendedness': 'refExtendedness', # band-specific, not sure what the ref one is
            'blendedness': 'r_blendedness', # band-specific  
            # we should probably change this to the reference band 
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

        # detect_isPrimary
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
 
            # double check if this is right - do these not need a PSF in the label?
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



            modifiers[f'calibFlux_{band}'] = f'{band}_calib{FLUX}'
            modifiers[f'calibFluxErr_{band}'] = f'{band}_calib{FLUX}{ERR}'


            modifiers[f'calibFlux_flag_{band}'] = f'{band}_calib_flag'

            modifiers[f'mag_{band}_calib'] = (convert_nanoJansky_to_mag,
                                               f'{band}_calib{FLUX}')

            modifiers[f'magerr_{band}_calib'] = (convert_flux_err_to_mag_err,
                                                  f'{band}_calib{FLUX}',
                                                  f'{band}_calib{FLUX}{ERR}')

            modifiers[f'snr_{band}_calib'] = (np.divide,
                                               f'{band}_calib{FLUX}',
                                               f'{band}_calib{FLUX}{ERR}')





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

            modifiers['shear_1_{band}'] = (shear_from_moments,f'Ixx_pixel_{band}',f'Ixy_pixel_{band}',f'Iyy_pixel_{band}')[0]
            modifiers['shear_2_{band}'] = (shear_from_moments,f'Ixx_pixel_{band}',f'Ixy_pixel_{band}',f'Iyy_pixel_{band}')[1]
        modifiers['shear_1'] = (shear_from_moments,'shape_xx','shape_xy','shape_yy')[0]
        modifiers['shear_2'] = (shear_from_moments,'shape_xx','shape_xy','shape_yy')[1]


        not_good_flags = (            
            #'detect_isPrimary',
            #'deblend_skipped',
            #'i_blendedness_flag',
            #'i_cModel_flag',
            #'i_centroid_flag',
            #'i_hsmShapeRegauss_flag',
            #'i_pixelFlags_bad',
            #'i_pixelFlags_clippedCenter',
            #'i_pixelFlags_crCenter',
            #'i_pixelFlags_interpolatedCenter',
            #'i_pixelFlags_edge',
            #'i_pixelFlags_suspectCenter' # check which of these are true
            )
        modifiers['clean'] = (
            create_basic_flag_mask,
            'deblend_skipped',
            'i_blendedness_flag',
            'i_cModel_flag',
            'i_centroid_flag',
            'i_hsmShapeRegauss_flag',
            'i_pixelFlags_bad',
            'i_pixelFlags_clippedCenter',
            'i_pixelFlags_crCenter',
            'i_pixelFlags_interpolatedCenter',
            'i_pixelFlags_edge',
            'i_pixelFlags_suspectCenter' # check which of these are true

        ) #+ not_good_flags
        modifiers['clean'] = 'detect_isIsolated'

            #'bad_centroid'
            #'flags_pixel_edge'
            #'flags_interpolated_center'
            #'saturated_cente'
            #'cr_center'
            #'pixel_bad'
            #'suspect'
            #'pixel_clipped_any'
            #'hsm_regauss_flags'

            #'detect_isTractInner',
            #'base_PixelFlags_flag_edge',
            #'base_PixelFlags_flag_interpolatedCenter',
            #'base_PixelFlags_flag_saturatedCenter',
            #'base_PixelFlags_flag_crCenter',
            #'base_PixelFlags_flag_bad',
            #'base_PixelFlags_flag_suspectCenter',
            #'base_PixelFlags_flag_clipped',



        return modifiers


class DC2TruthMatchCatalog(DC2DMTractCatalog):
    r"""
    DC2 Truth-Match (parquet) Catalog reader

    This reader is intended for reading the truth-match catalog that is in
    parquet format and partitioned by tracts.

    Two options, `as_object_addon` and `as_truth_table` further control,
    respectively, whether the returned table contains only rows that match
    to the object catalog (`as_object_addon=True`), or only unique truth
    entries (`as_truth_table=True`).

    When `as_object_addon` is set, most column names will also be decorated
    with a `_truth` postfix.

    The underlying truth-match catalog files contain fluxes but not magnitudes.
    The reader provides translation to magnitude (using `_flux_to_mag`) for
    convenience. No other translation is applied.

    Parameters
    ----------
    base_dir            (str): Directory of data files being served, required
    filename_pattern    (str): The optional regex pattern of served data files
    as_object_addon    (bool): If set, return rows in the the same row order as object catalog
    as_truth_table     (bool): If set, remove duplicated truth rows
    as_matchdc2_schema (bool): If set, use column names in Javi's matchDC2 catalog.
    """

    def _subclass_init(self, **kwargs):
        self.META_PATH = META_PATH

        super()._subclass_init(**dict(kwargs, is_dpdd=True))  # set is_dpdd=True to obtain bare modifiers

        self._as_object_addon = bool(kwargs.get("as_object_addon"))
        self._as_truth_table = bool(kwargs.get("as_truth_table"))
        self._as_matchdc2_schema = bool(kwargs.get("as_matchdc2_schema"))
        if self._as_matchdc2_schema:
            self._as_object_addon = True

        if self._as_object_addon and self._as_truth_table:
            raise ValueError("Reader options `as_object_addon` and `as_truth_table` cannot both be set to True.")

        if self._as_matchdc2_schema:
            self._use_matchdc2_quantity_modifiers()
            return

        flux_cols = [k for k in self._quantity_modifiers if k.startswith("flux_")]
        for col in flux_cols:
            self._quantity_modifiers["mag_" + col.partition("_")[2]] = (_flux_to_mag, col)

        if self._as_object_addon:
            no_postfix = ("truth_type", "match_objectId", "match_sep", "is_good_match", "is_nearest_neighbor", "is_unique_truth_entry")
            self._quantity_modifiers = {
                (k + ("" if k in no_postfix else "_truth")): (v or k) for k, v in self._quantity_modifiers.items()
            }


    def _detect_available_bands(self):
        return ["_".join(col.split("_")[1:-1]) for col in self._columns if col.startswith('flux_') and col.endswith('_noMW')]

    def _obtain_native_data_dict(self, native_quantities_needed, native_quantity_getter):
        """
        When `as_object_addon` or `as_truth_table` is set, we need to filter the table
        based on `match_objectId` or `is_unique_truth_entry` before the data is returned .
        To achieve such, we have to overwrite this method to inject the additional columns
        and to apply the masks.
        """
        native_quantities_needed = set(native_quantities_needed)
        if self._as_object_addon:
            native_quantities_needed.add("match_objectId")
        elif self._as_truth_table:
            native_quantities_needed.add("is_unique_truth_entry")

        columns = list(native_quantities_needed)
        d = native_quantity_getter.read_columns(columns, as_dict=False)
        if self._as_object_addon:
            n = np.count_nonzero(d["match_objectId"].values > -1)
            return {c: d[c].values[:n] for c in columns}
        elif self._as_truth_table:
            mask = d["is_unique_truth_entry"].values
            return {c: d[c].values[mask] for c in columns}
        return {c: d[c].values for c in columns}


    def __len__(self):
        if self._len is None:
            # pylint: disable=attribute-defined-outside-init
            if self._as_object_addon:
                self._len = sum(
                    np.count_nonzero(d["match_objectId"] > -1)
                    for d in self.get_quantities(["match_objectId"], return_iterator=True)
                )
            elif self._as_truth_table:
                self._len = sum(
                    np.count_nonzero(d["is_unique_truth_entry"])
                    for d in self.get_quantities(["is_unique_truth_entry"], return_iterator=True)
                )
            else:
                self._len = sum(len(dataset) for dataset in self._datasets)
        return self._len
    def _use_matchdc2_quantity_modifiers(self):
        """
        To recreate column names in dc2_matched_table.py
        cf. https://github.com/fjaviersanchez/MatchDC2/blob/master/python/matchDC2.py
        """

        quantity_modifiers = {
            "truthId": (lambda i, t: np.where(t < 3, i, "-1").astype(np.int64), "id", "truth_type"),
            "objectId": "match_objectId",
            "is_matched": "is_good_match",
            "is_star": (lambda t: t > 1, "truth_type"),
            "ra": "ra",
            "dec": "dec",
            "redshift_true": "redshift",
            "dist": "match_sep",
        }

        for col in self._columns:
            if col.startswith("flux_") and col.endswith("_noMW"):
                quantity_modifiers["mag_" + col.split("_")[1] + "_lsst"] = (_flux_to_mag, col)

        quantity_modifiers['galaxy_match_mask'] = (lambda t, m: (t == 1) & m, "truth_type", "is_good_match")
        quantity_modifiers['star_match_mask'] = (lambda t, m: (t == 2) & m, "truth_type", "is_good_match")

        # put these into self for `self.add_derived_quantity` to work
        self._quantity_modifiers = quantity_modifiers
        self._native_quantities = set(self._columns)

        for col in list(quantity_modifiers):
            if col in ("is_matched", "is_star", "galaxy_match_mask", "star_match_mask"):
                continue
            for t in ("galaxy", "star"):
                self.add_derived_quantity(
                    "{}_{}".format(col, t),
                    lambda d, m: np.ma.array(d, mask=m),
                    col,
                    "{}_match_mask".format(t),
                )
    def _get_quantity_info_dict(self, quantity, default=None):
        """
        Befere calling the parent method, check if `quantity` has an added "_truth" postfix
        due to the `if self._as_object_addon:...` part in _subclass_init. If so, remove the postfix.
        """
        if (
            quantity not in self._quantity_info_dict and
            quantity in self._quantity_modifiers and
            quantity.endswith("_truth")
        ):
            quantity = quantity[:-6]
        return super()._get_quantity_info_dict(quantity, default)

class CosmoDC2AddonCatalog(CosmoDC2ParentClass):
    def _get_group_names(self, fh): # pylint: disable=W0613
        return [self.get_catalog_info('addon_group')]


"""
DC2 Object Catalog Reader
"""

import os
import re
import numpy as np

from .utils import first

from .dc2_dm_catalog import DC2DMCatalog, convert_flux_to_nanoJansky, create_basic_flag_mask

__all__ = ['DC2ObjectCatalog']


class DC2ObjectCatalog(DC2DMCatalog):
    r"""DC2 Object Source Catalog reader

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
    FILE_PATTERN = r'object_tract_\d+\.parquet$'
    META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_object_meta.yaml')

    
    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', self.FILE_PATTERN))

        if not os.path.isdir(self.base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self.base_dir))

        self.pixel_scale = float(kwargs.get('pixel_scale', 0.2))
        
        self._datasets = self._generate_datasets()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self.base_dir))

        self._columns = first(self._datasets).columns
        if kwargs.get('is_dpdd'):
            self._quantity_modifiers = {col: None for col in self._columns}
        else:
            # A slightly crude way of checking for version of schema to have modelfit mag
            # A future improvement will be to explicitly store version information in the datasets
            # and just rely on that versioning.
            has_modelfit_mag = any(col.endswith('_modelfit_mag') for col in self._columns)
            
            if any(col.endswith('_fluxSigma') for col in self._columns):
                dm_schema_version = 1
            elif any(col.endswith('_fluxErr') for col in self._columns):
                dm_schema_version = 2
            elif any(col == 'base_Blendedness_abs_instFlux' for col in self._columns):
                dm_schema_version = 3
            else:
                dm_schema_version = 4
    
            bands = [col[0] for col in self._columns if len(col) == 5 and col.endswith('_mag')]
    
            self._quantity_modifiers = self._generate_modifiers(
                    self.pixel_scale, bands, has_modelfit_mag, dm_schema_version)

        self._quantity_info_dict = self._generate_info_dict(self.META_PATH)
        self._native_filter_quantities = {'tract'}
        self._len = None

    @staticmethod
    def _generate_modifiers(pixel_scale=0.2, bands='ugrizy',
                            has_modelfit_mag=True,
                            dm_schema_version=4):
        """Creates a dictionary relating native and homogenized column names

        Args:
            dm_schema_version (int): DM schema version (1, 2, or 3)

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
            modifiers['psFlux_{}'.format(band)] = (convert_flux_to_nanoJansky,
                                                   '{}_base_PsfFlux_{}'.format(band, FLUX))
            modifiers['psFlux_flag_{}'.format(band)] = '{}_base_PsfFlux_flag'.format(band)
            modifiers['psFluxErr_{}'.format(band)] = (convert_flux_to_nanoJansky,
                                                      '{}_base_PsfFlux_{}{}'.format(band, FLUX, ERR))

            modifiers['I_flag_{}'.format(band)] = '{}_base_SdssShape_flag'.format(band)

            modifiers['cModelFlux_{}'.format(band)] = (convert_flux_to_nanoJansky,
                                                       '{}_modelfit_CModel_{}'.format(band, FLUX))
            modifiers['cModelFluxErr_{}'.format(band)] = (convert_flux_to_nanoJansky,
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

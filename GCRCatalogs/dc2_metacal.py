"""
DC2 Metacal Catalog Reader
"""

import os

from .dc2_dm_catalog import DC2DMCatalog, convert_flux_to_nanoJansky, create_basic_flag_mask

__all__ = ['DC2MetacalCatalog']


class DC2MetacalCatalog(DC2DMCatalog):
    r"""DC2 Metacal Catalog reader

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
    FILE_PATTERN = r'metacal_tract_\d+\.parquet$'
    SCHEMA_FILENAME = 'schema.yaml'
    META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_metacal_meta.yaml')

    @staticmethod
    def _generate_modifiers(bands='riz'):
        """Creates a dictionary relating native and homogenized column names

        Args:
            Bands availble: r,i,z

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

        modifiers = {
            'objectId': 'id',
            'mcal_psf_g1': 'mcal_psf_g1_mean',
            'mcal_psf_g2': 'mcal_psf_g2_mean',
            'mcal_T_psf' : 'mcal_psf_T_mean',
            'mcal_flags' : 'mcal_flags'
        }

        # Additional metacal values and their variants
        for variant in ['','_1p','_1m','_2p','_2m']:
            # Shape
            modifiers['mcal_g1{}'.format(variant)] = 'mcal_gauss_g1{}'.format(variant)
            modifiers['mcal_g2{}'.format(variant)] = 'mcal_gauss_g2{}'.format(variant)
            # Size
            modifiers['mcal_T{}'.format(variant)] = 'mcal_gauss_T{}'.format(variant)
            # SNR
            modifiers['mcal_s2n{}'.format(variant)] = 'mcal_gauss_s2n{}'.format(variant)

            # Adds band dependent info and their variants
            for band in bands:
                modifiers['mcal_flux_{}{}'.format(band,variant)] = (lambda x: x / 0.2**2,
                'mcal_gauss_flux_{}{}'.format(band,variant))
                modifiers['mcal_flux_err_{}{}'.format(band,variant)] =  (lambda x: x / 0.2**2,
                'mcal_gauss_flux_err_{}{}'.format(band,variant))

                modifiers['mcal_mag_{}{}'.format(band, variant)] = (
                    lambda x: -2.5 * np.log10(x) + 27.0,
                    'mcal_flux_{}{}'.format(band, variant),
                )
                modifiers['mcal_mag_err_{}{}'.format(band, variant)] = (
                    lambda flux, err: (2.5 * err) / (flux * np.log(10)),
                    'mcal_flux_{}{}'.format(band, variant),
                    'mcal_flux_err_{}{}'.format(band, variant),
                )

        return modifiers

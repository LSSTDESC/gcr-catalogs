"""
DC2 Parquet Photo-z Catalog Reader
"""

import os
import numpy as np
from .dc2_dm_catalog import DC2DMTractCatalog

__all__ = ['DC2PhotozCatalog']


class DC2PhotozCatalog(DC2DMTractCatalog):
    r"""DC2 Parquet Photoz Catalog reader

    Parameters
    ----------
    file_dir          (str): Directory of data files being served, required
    file_pattern      (str): The optional regex pattern of served data files
    meta_path         (str): path to yaml entries for quantities

    Attributes
    ----------
    base_dir          (str): The directory of data files being served

    Notes
    -----
    """
    # pylint: disable=too-many-instance-attributes

    FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    FILE_PATTERN = r'photoz_pdf_Run\d\.[0-9a-z]+_tract_\d+\.parquet$'
    META_PATH = os.path.join(FILE_DIR,
                             'catalog_configs/_dc2_photoz_parquet.yaml')

    _PDF_BIN_INFO = {
        'start': 0.005,
        'stop': 3.0055,
        'step': 0.01,
        'decimals_to_round': 3,
    }

    def _subclass_init(self, **kwargs):
        """
        Wraps default init method to apply various corrections to the catalog.
        """

        # grab bin info as kwarg, or default to run2.2i values.
        self._pdf_bin_info = kwargs.get('pdf_bin_info', self._PDF_BIN_INFO)
        self._pdf_bin_centers = np.round(np.arange(self._pdf_bin_info['start'],
                                                   self._pdf_bin_info['stop'],
                                                   self._pdf_bin_info['step'],
        ), self._pdf_bin_info['decimals_to_round'])
        self._n_pdf_bins = len(self._pdf_bin_centers)

        super(DC2PhotozCatalog, self)._subclass_init(**kwargs)

    @staticmethod
    def _generate_modifiers(**kwargs):
        """Creates a dictionary relating native and homogenized column names

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """

        modifiers = {
            'photoz_odds': 'ODDS',
            'photoz_mode': 'z_mode',
            'photoz_median': 'z_median',
            'photoz_mean': 'z_mean',
            'photoz_pdf': 'pdf',
            'ID': 'galaxy_id',
            'photoz_mode_ml': 'z_mode_ml',
            'photoz_mode_ml_red_chi2': 'z_mode_ml_red_chi2',
        }
        return modifiers

    @property
    def photoz_pdf_bin_centers(self):
        return self._pdf_bin_centers

    @property
    def n_pdf_bins(self):
        return self._n_pdf_bins

"""
DC2 Parquet Photo-z Catalog Reader
"""

import os
import re
import warnings
import numpy as np
from .dc2_dm_catalog import DC2DMCatalog, DC2DMTractCatalog
from GCR import BaseGenericCatalog
from .parquet import ParquetFileWrapper

__all__ = ['DC2PhotozMixin', 'CosmoDC2Parquet', 'DC2PhotozGalaxyCatalog',
           'DC2PhotozCatalog', 'PZSKRFCatalog']


class DC2PhotozMixin:

    _PDF_BIN_INFO = {
        'start': 0.005,
        'stop': 3.005,
        'nbins': 301,
        'decimals_to_round': 3,
    }

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

    def _process_pdf_bins(self, pdf_bin_info=None):
        self._pdf_bin_info = pdf_bin_info or self._PDF_BIN_INFO
        self._pdf_bin_centers = np.round(np.linspace(
            self._pdf_bin_info['start'],
            self._pdf_bin_info['stop'],
            self._pdf_bin_info['nbins'],
        ), self._pdf_bin_info['decimals_to_round'])
        self._n_pdf_bins = len(self._pdf_bin_centers)

    @property
    def photoz_pdf_bin_centers(self):
        return self._pdf_bin_centers

    @property
    def n_pdf_bins(self):
        return self._n_pdf_bins


class CosmoDC2Parquet(DC2DMCatalog):

    _native_filter_quantities = {'healpix_pixel', 'redshift_block_lower'}

    def _subclass_init(self, **kwargs):
        self._healpix_pixels = None
        if kwargs.get('healpix_pixels') is not None:
            self._healpix_pixels = [int(t) for t in kwargs['healpix_pixels']]
        super()._subclass_init(**kwargs)

    def _extract_dataset_info(self, filename):
        match = re.match(self.FILE_PATTERN, filename)
        try:
            zlo, _, hpx = tuple(map(int, match.groups()))
        except (ValueError, TypeError, AttributeError):
            warnings.warn('Filename {} does not contain correct z/healpix info or not in correct format. Skipped')
            return False
        return {'redshift_block_lower': zlo, 'healpix_pixel': hpx}

    def _sort_datasets(self, datasets):
        current_healpix_pixels = set(dataset.info['healpix_pixel'] for dataset in datasets)
        if self._healpix_pixels and not all(t in current_healpix_pixels for t in self._healpix_pixels):
            warnings.warn('Not all healpix pixels that were requested are loaded. Use `available_healpix_pixels` to see what pixels have been loaded.')
        return sorted(datasets, key=lambda d: (d.info['redshift_block_lower'], d.info['healpix_pixel']))

    @property
    def available_healpix_pixels(self):
        """Returns a sorted list of available tracts
        Returns:
            A sorted list of available tracts as integers
        """
        return [dataset.info['healpix_pixel'] for dataset in self._datasets]


class DC2PhotozGalaxyCatalog(DC2PhotozMixin, CosmoDC2Parquet):
    """Parquet Photoz Catalog reader (for cosmoDC2 galaxy catalog)

    Parameters
    ----------
    base_dir          (str): The directory of data files being served
    file_pattern      (str): The optional regex pattern of served data files
    meta_path         (str): path to yaml entries for quantities
    healpix_pixels   (list): List of tracts (integer)
    """
    FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    FILE_PATTERN = r'fzboost_photoz_pdf_z_(\d)_(\d).step_all.healpix_(\d+).parquet'
    META_PATH = os.path.join(FILE_DIR, 'catalog_configs', '_dc2_photoz_parquet.yaml')

    # FlexZBoost has slightly different binning than BPZ
    _PDF_BIN_INFO = {
        'start': 0.0,
        'stop': 3.0,
        'nbins': 301,
        'decimals_to_round': 3,
    }

    def _subclass_init(self, **kwargs):
        super(DC2PhotozGalaxyCatalog, self)._subclass_init(**kwargs)
        self._process_pdf_bins(kwargs.get("pdf_bin_info"))


class DC2PhotozCatalog(DC2PhotozMixin, DC2DMTractCatalog):
    """DC2 Parquet Photoz Catalog reader

    Parameters
    ----------
    base_dir          (str): The directory of data files being served
    file_pattern      (str): The optional regex pattern of served data files
    meta_path         (str): path to yaml entries for quantities
    tracts           (list): List of tracts (integer)
    """
    FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    FILE_PATTERN = r'photoz_pdf_Run\d\.[0-9a-z]+_tract_\d+\.parquet$'
    META_PATH = os.path.join(FILE_DIR, 'catalog_configs', '_dc2_photoz_parquet.yaml')

    def _subclass_init(self, **kwargs):
        super(DC2PhotozCatalog, self)._subclass_init(**kwargs)
        self._process_pdf_bins(kwargs.get("pdf_bin_info"))


class PZSKRFCatalog(DC2PhotozMixin,BaseGenericCatalog):
    """
    SK-learn Random Forest-based Photo-z catalog class.  Borrowed some structur
    from Scott Daniel's AGN catalog, as it also uses one single file to load 
    everything.  Columns available are different than other PZ catalogs, so
    we will need this custom subclass.
    """

    # Olivia's data has different binning and numbins than BPZ
    _PDF_BIN_INFO = {
        'start': 0.015,
        'stop': 2.985,
        'nbins': 100,
        'decimals_to_round': 3,
    }

    
    def _subclass_init(self, base_dir, filename, **kwargs): 
        if not os.path.isdir(base_dir):
            raise RuntimeError("Catalog directory %s does not exist." % (base_dir))

        self._path = os.path.join(base_dir, filename)
        self._dataset = ParquetFileWrapper(self._path,None)
        self._columns = self._dataset.columns
        self._quantity_modifiers = self._generate_quantity_modifiers()
        self._columns = self._dataset.columns
        self._process_pdf_bins(kwargs.get("pdf_bin_info"))
        
    def __del__(self):
        self._dataset = None

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
            'galaxy_id': 'galid',
            'mag_i_photoz': 'mag_i',
            'rz_real': 'rz_real',
            'photoz_mode': 'photoz_mode',
            'photoz_pdf': 'photoz_pdf',
        }
        return quantity_modifiers
    
    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise RuntimeError("*native_filters* not supported")
        yield self._dataset

    def _generate_native_quantity_list(self):
        return self._columns
    
    @staticmethod
    def _obtain_native_data_dict(native_quantities_needed, native_quantity_getter):
        return native_quantity_getter.read_columns(list(native_quantities_needed), as_dict = True)

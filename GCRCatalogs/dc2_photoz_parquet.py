"""
DC2 Parquet Photo-z Catalog Reader
"""

import os
import re
import pandas as pd
import numpy as np
import yaml
import pyarrow.parquet as pq
from .dc2_dm_catalog import DC2DMTractCatalog, ParquetFileWrapper
from .cosmodc2 import CosmoDC2ParentClass
from .utils import first
from GCR import BaseGenericCatalog

__all__ = ['DC2PhotozMixin','DC2PhotozGalaxyCatalog','DC2PhotozCatalog']

class DC2PhotozMixin(object):

    @staticmethod
    def _generate_modifiers():
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


class DC2PhotozGalaxyCatalog(CosmoDC2ParentClass,DC2PhotozMixin):
    r"""
    catalog reader class for cosmoDC2 galaxy catalogs

    Parameters
    ----------
    catalog_root_dir           (str): Directory of data files being served 
                                      required
    catalog_filename_template  (str): regex pattern of served data files, 
                                      should match pattern used in main
                                      galaxy catalog
    healpix_pattern            (str): should match regex pattern, but with {}
                                      because this pattern is used in 
                                      CosmoDC2ParentClass
    """

    _FILE_PATTERN = r'fzboost_photoz_pdf_z_(\d)_(\d).step_all.healpix_(\d+).parquet'
    FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    META_PATH = os.path.join(FILE_DIR,
                             'catalog_configs/_dc2_photoz_parquet.yaml')
    
    # FlexZBoost has slightly different binning than BPZ
    _PDF_BIN_INFO = {
        'start': 0.0,
        'stop': 3.0,
        'nbins': 301,
        'decimals_to_round': 3,
    }


    def _subclass_init(self, catalog_root_dir, catalog_filename_template, healpix_pattern, **kwargs):
        # pylint: disable=W0221
        self._pdf_bin_info = kwargs.get('pdf_bin_info', self._PDF_BIN_INFO)
        self._pdf_bin_centers = np.round(np.linspace(self._pdf_bin_info['start'],
                                                   self._pdf_bin_info['stop'],
                                                   self._pdf_bin_info['nbins'],
        ), self._pdf_bin_info['decimals_to_round'])
        self._n_pdf_bins = len(self._pdf_bin_centers)
        
        if not os.path.isdir(catalog_root_dir):
            raise ValueError('Catalog directory {} does not exist'.format(catalog_root_dir))
        self._native_filter_quantities = {'healpix_pixel', 'redshift_block_lower'}
        self._quantity_modifiers = self._generate_modifiers()
        self.base_dir = catalog_root_dir
        self.healpix_pattern = healpix_pattern
        self._filename_pattern = kwargs.get('catalog_filename_template', self._FILE_PATTERN)
        self._filename_re = re.compile(self._filename_pattern)

        self._file_list = self._get_healpix_file_list(catalog_root_dir,
                                        healpix_pattern,
                                        **kwargs)

        self._healpix_files = self._file_list # needed in CosmoDC2ParentClass
        self._datasets = self._generate_datasets()
        self._columns = first(self._datasets).columns


    @staticmethod
    def _obtain_native_data_dict(native_quantities_needed, native_quantity_getter):
        """                                                               
        Overloading this so that we can query the database backend
        for multiple columns at once
        """
        return native_quantity_getter.read_columns(list(native_quantities_needed), as_dict=True)

    def _extract_dataset_info(self, filename):
        """
        Should return a dict that contains infomation of each dataset
        that is parsed from the filename
        Should return None if no infomation need to be stored
        Should return False if this dataset needs to be skipped
        Parameters:
        ----------
        filename (str)
          the filename of the chunk of data
        Returns:
        -------
        data_info: (dict)
          a dictionary of file attributes, in this case zlo, zhi, and
          healpix_pixel
        """
        fname_pattern = self.healpix_pattern.format(r'(\d)', r'(\d)', r'(\d+)')
        mat = re.match(fname_pattern, filename)
        zlo_x, _, hpx_x = tuple(map(int, mat.groups()))
        data_info = {'zlo':zlo_x, 'healpix_pixel':hpx_x}
        return data_info

    def _generate_native_quantity_list(self):
        return pd.read_parquet(first(self._healpix_files.values()),engine='pyarrow').columns.tolist()

    def _generate_datasets(self):
        """Return viable data sets from all files in self.base_dir
        Returns:
            A list of ObjectTableWrapper(<file path>, <key>) objects 
            for all files and keys
        """
        datasets = list()
        for xfname in self._file_list.values():
            fname = xfname.split(self.base_dir+"/")[-1]
            if not self._filename_re.match(fname):
                continue
            info = self._extract_dataset_info(fname)
            if info is False:
                continue
            datasets.append(ParquetFileWrapper(xfname, info))
        return datasets

    def _iter_native_dataset(self, native_filters=None):
        for dataset in self._datasets:
            if native_filters is not None and not native_filters.check_scalar(dataset.info):
                continue
            yield dataset


class DC2PhotozCatalog(DC2DMTractCatalog,DC2PhotozMixin):
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



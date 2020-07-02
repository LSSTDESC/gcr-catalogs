"""
PZ mag err catalog (matched to cosmoDC2) reader

This reader was designed by Yao-Yuan Mao,
based a catalog provided by Sam Schmidt.
"""

import re
import os
import numpy as np
import glob
import pandas as pd
import h5py
from GCR import BaseGenericCatalog

from .utils import first

__all__ = ['PZMagErrCatalog', 'PZMagErrPDFsCatalog']

FILE_PATTERN = r'z_(\d)\S+withmask.healpix_(\d+)_magwerr\.h5$'
FILE_PATTERN_PDF = r'photoz_pdf_z_(\d)\S+healpix_(\d+).hdf5'
FILE_GLOB_PATTERN_PDF = 'photoz_pdf_z_*.hdf5'

class PZMagErrCatalog(BaseGenericCatalog):
    """
    Class to handle mock errors on CosmoDC2v1.1.4 truth catalog
    """
    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', FILE_PATTERN))
        self._healpix_pixels = kwargs.get('healpix_pixels')

        self._healpix_files = dict()
        for f in sorted(os.listdir(self.base_dir)):
            m = self._filename_re.match(f)
            if m is None:
                continue
            key = tuple(map(int, m.groups()))
            if self._healpix_pixels and key[1] not in self._healpix_pixels:
                continue
            self._healpix_files[key] = os.path.join(self.base_dir, f)

        self._native_filter_quantities = {'healpix_pixel', 'redshift_block_lower'}
        self._quantity_modifiers = {
            'redshift': 'redshift',
            'galaxy_id': 'baseDC2/galaxy_id',
            'photoz_mask': 'photoz_mask'
        }
        for band in ['u','g','r','i','z','y']:
            self._quantity_modifiers['mag_%s_photoz'%band] = 'scatmag_%s'%band
            self._quantity_modifiers['mag_err_%s_photoz'%band] = 'scaterr_%s'%band
        self._info_dict = {}
        self._info_dict['galaxy_id']={'units':'unitless',
                                 'description': 'ID of galaxy matching the entry '
                                      'from the main catalog'}
        self._info_dict['photoz_mode_ml_red_chi2']={'units':'unitless',
                                                    'description':'reduced chi sq '
                                                    'at the max likelihood '
                                                    'redshift and type.  A high '
                                                    'chi2 value indicates a '
                                                    'potentially bad fit'}
        self._info_dict['photoz_pdf']={'units':'unitless','description':'posterior'
                                       ' probability distributions for individual'
                                       ' galaxies computed on a redshift grid.  '
                                       'The specific redshift grid is stored in '
                                       'pdf/zgrid'}
        self._info_dict['photoz_mode']={'units':'unitless','description':'mode of'
                                        ' the posterior pdf for an individual '
                                        'galaxy'}
        self._info_dict['photoz_mean']={'units':'unitless','description':'mean '
                                        'value of the posterior pdf for an '
                                        'individual galaxy'}
        self._info_dict['photoz_median']={'units':'unitless',
                                          'description':'median value of the '
                                          'posterior pdf for an individual galaxy,'
                                          ' defined by where the CDF of the '
                                          'distribution is 0.5 '}
        self._info_dict['photoz_mode_ml']={'units':'unitless',
                                           'description':'index value of pdf/zgrid'
                                           ' corresponding to the max likelihood '
                                           'redshift *before* the magnitude/type '
                                           'prior is applied'}
        self._info_dict['photoz_odds']={'units':'unitless',
                                        'description':'ODDS parameter: the '
                                        'integral of the posterior within a fixed'
                                        ' interval around the mode of the posterior'
                                        ' used to quantify photo-z quality.  A high'
                                        ' ODDS value close to 1.0 indicated a '
                                        'compact, single peaked posterior, while'
                                        ' low ODDS values could indicate multiple'
                                        ' peaks or a broad posterior'}
        self._info_dict['photoz_mask']={'units':'unitless',
                                        'description':'photoz_mask is a boolean'
                                        ' mask to match the arrays of the set of'
                                        ' magnitudes and errors to the subset '
                                        'with i<26.5 that have photozs computed'}

    def _get_quantity_info_dict(self, quantity, default=None):
        return self._info_dict.get(quantity,default)
 
    def _generate_native_quantity_list(self):
        return pd.read_hdf(first(self._healpix_files.values())).columns.tolist()

    def _iter_native_dataset(self, native_filters=None):
        for (zlo_this, hpx_this), file_path in self._healpix_files.items():
            d = {'healpix_pixel': hpx_this, 'redshift_block_lower': zlo_this}
            if native_filters is not None and not native_filters.check_scalar(d):
                continue
            df = pd.read_hdf(file_path)
            yield lambda col: df[col].values # pylint: disable=cell-var-from-loop


class PZMagErrPDFsCatalog(BaseGenericCatalog):
    """
    Class to handle hdf5 photoz PDF output files
    """

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs.get('base_dir')
        self._file_glob_pattern = kwargs.get('filename_glob_pattern',
                                             FILE_GLOB_PATTERN_PDF)
        self._filename_re = re.compile(kwargs.get('filename_pattern',
                                                  FILE_PATTERN_PDF))
        self._healpix_pixels = kwargs.get('healpix_pixels')

        self._healpix_files = dict()
        for f in sorted(os.listdir(self.base_dir)):
            m = self._filename_re.match(f)
            if m is None:
                continue
            key = tuple(map(int, m.groups()))
            if self._healpix_pixels and key[1] not in self._healpix_pixels:
                continue
            self._healpix_files[key] = os.path.join(self.base_dir, f)

        self._datasets = self._generate_datasets()
        self._quantity_modifiers = {
            'galaxy_id': 'id/galaxy_id',
            'photoz_pdf': 'pdf/pdf',
            'photoz_mode': 'point_estimates/z_mode',
            'photoz_mean': 'point_estimates/z_mean',
            'photoz_median': 'point_estimates/z_median',
            'photoz_mode_ml': 'point_estimates/z_mode_ml',
            'photoz_mode_ml_red_chi2': 'point_estimates/z_mode_ml_red_chi2',
            'photoz_odds': 'point_estimates/ODDS',
        }

        self._native_filter_quantities = {'healpix_pixel', 'redshift_block_lower'}
        self._info_dict={}
        self._info_dict['galaxy_id']={'units':'unitless',
                                 'description': 'ID of galaxy matching the entry '
                                      'from the main catalog'}
        self._info_dict['photoz_mode_ml_red_chi2']={'units':'unitless',
                                                    'description':'reduced chi sq at '
                                                    'the max likelihood redshift and '
                                                    'type.  A high chi2 value '
                                                    'indicates a potentially bad fit'}
        self._info_dict['photoz_pdf']={'units':'unitless','description':'posterior '
                                       'probability distributions for individual '
                                       'galaxies computed on a redshift grid.  The '
                                       'specific redshift grid is stored in pdf/zgrid'}
        self._info_dict['photoz_mode']={'units':'unitless','description':'mode of the '
                                        'posterior pdf for an individual galaxy'}
        self._info_dict['photoz_mean']={'units':'unitless','description':'mean value '
                                        'of the posterior pdf for an individual galaxy'}
        self._info_dict['photoz_median']={'units':'unitless','description':'median '
                                          'value of the posterior pdf for an individual '
                                          'galaxy, defined by where the CDF of the '
                                          'distribution is 0.5 '}
        self._info_dict['photoz_mode_ml']={'units':'unitless','description':'index value'
                                           ' of pdf/zgrid corresponding to the max '
                                           'likelihood redshift *before* the magnitude/'
                                           'type prior is applied'}
        self._info_dict['photoz_odds']={'units':'unitless','description':'ODDS parameter:'
                                        ' the integral of the posterior within a fixed '
                                        'interval around the mode of the posterior used '
                                        'to quantify photo-z quality.  A high ODDS value'
                                        ' close to 1.0 indicated a compact, single '
                                        'peaked posterior, while low ODDS values could'
                                        ' indicate multiple peaks or a broad posterior'}

    def _get_quantity_info_dict(self, quantity, default=None):
        return self._info_dict.get(quantity,default)


    def _generate_datasets(self):
        datasets = list()
        for path in glob.glob(os.path.join(self.base_dir,
                                           self._file_glob_pattern)):
            try:
                dataset = PhotoZFileObject3(path, self._filename_re)
            except ValueError:
                continue
            datasets.append(dataset)
        return sorted(datasets, key=(lambda d: d.healpix_pixel))

    def _generate_native_quantity_list(self):
        return first(self._datasets).keys()

    def _iter_native_dataset(self, native_filters=None):
        for (zlo_this, hpx_this), file_path in self._healpix_files.items():
            pix_block = {'healpix_pixel':hpx_this,
                         'redshift_block_lower': zlo_this}
            if native_filters and not native_filters.check_scalar(pix_block):
                continue
            dataset = PhotoZFileObject3(file_path, self._filename_re)
            yield dataset.get
            dataset.close() # to avoid OS complaining too many open files

    def close_all_file_handles(self):
        """Clear all cached file handles"""
        for dataset in self._datasets:
            dataset.close()

    @property
    def photoz_pdf_bin_centers(self):
        """
        expose self._pdf_bin_centers as a public property.
        """
        return first(self._datasets).pdf_bins
            
class PhotoZFileObject3():
    """
    HDF5 file wrapper for PhotoZCatalog3
    """
    _KEY_PDF_BINS = 'pdf/zgrid'
    def __init__(self, path, filename_pattern=None):

        if isinstance(filename_pattern, re.Pattern): # pylint: disable=no-member
            filename_re = filename_pattern
        else:
            filename_re = re.compile(filename_pattern)

        basename = os.path.basename(path)
        match = filename_re.match(basename)
        if match is None:
            raise ValueError('filename {} does not match required pattern')

        z_block_lower, pixelid = tuple(map(int, match.groups()))
        self.z_block_lower = int(z_block_lower)
        self.healpix_pixel = int(pixelid)
        self.path = path
        self._handle = None
        self._keys = None
        self._len = None

    def keys(self):
        if self._keys is None:
            collector = set()
            def collect(name, obj):
                if isinstance(obj, h5py.Dataset) and name != self._KEY_PDF_BINS:
                    collector.add(name)
            self.handle.visititems(collect)
            self._keys = tuple(collector)
        return list(self._keys)

    def __len__(self):
        if self._len is None:
            self._len = self.handle[first(self.keys())].shape[0]
        return self._len

    def __getitem__(self, key):
        if key == 'healpix_pixel':
            return np.repeat(self.healpix_pixel, len(self))
        if key == 'redshift_block_lower':
            return np.repeat(self.z_block_lower, len(self))
        return self.handle[key][()]

    get = __getitem__

    @property
    def handle(self):
        if self._handle is None:
            try:
                self._handle = h5py.File(self.path, mode='r')
            except OSError:
                print(f'could not open {self.path}')
        return self._handle

    def open(self):
        return self.handle

    def close(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    @property
    def pdf_bins(self):
        return self[self._KEY_PDF_BINS]

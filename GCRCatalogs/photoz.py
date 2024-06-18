"""
Photo-z catalog reader

The PhotoZCatalog reader was designed by Yao-Yuan Mao,
based a photo-z catalog provided by Sam Schmidt, in Feb 2019.

The PhotoZCatalog2 reader, which uses PhotoZFileObject, was designed by Yao-Yuan Mao,
based a photo-z catalog provided by Sam Schmidt, in Jul 2019.
"""

import re
import os
import warnings
import shutil
import glob

import yaml
import numpy as np
import pandas as pd
import h5py
from GCR import BaseGenericCatalog

from .utils import first

__all__ = ['PhotoZCatalog', 'PhotoZCatalog2']


class PhotoZCatalog(BaseGenericCatalog):

    _FILE_PATTERN = r'run\d\.\d+[a-z]+_PZ_tract_\d+\.h5$'
    _METADATA_FILENAME = 'metadata.yaml'
    _PDF_BIN_INFO = {
        'start': 0.005,
        'stop': 1.01,
        'step': 0.01,
        'decimals_to_round': 3,
    }

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', self._FILE_PATTERN))
        _metadata_filename = kwargs.get('metadata_filename', self._METADATA_FILENAME)
        self._metadata_path = os.path.join(self.base_dir, _metadata_filename)

        self._pdf_bin_info = kwargs.get('pdf_bin_info', self._PDF_BIN_INFO)
        self._pdf_bin_centers = np.round(np.arange(
            self._pdf_bin_info['start'],
            self._pdf_bin_info['stop'],
            self._pdf_bin_info['step'],
        ), self._pdf_bin_info['decimals_to_round'])
        self._n_pdf_bins = len(self._pdf_bin_centers)

        if self._metadata_path and os.path.isfile(self._metadata_path):
            with open(self._metadata_path, 'r') as meta_stream:
                self._metadata = yaml.safe_load(meta_stream)
        else:
            self._metadata = self.generate_metadata()

        self._quantity_modifiers = {
            'photoz_mode': 'z_peak',
            'photoz_pdf': '_FULL_PDF',
        }

        self._native_filter_quantities = {'tract', 'patch'}
        self._info_dict = {}
        self._info_dict['galaxy_id']={'units':'unitless',
                                 'description': 'ID of galaxy matching the entry from the main catalog'}
        self._info_dict['photoz_mode_ml_red_chi2']={'units':'unitless',
                                                    'description':'reduced chi sq at the max likelihood redshift and type.  A high chi2 value indicates a potentially bad fit'}
        self._info_dict['photoz_pdf']={'units':'unitless','description':'posterior probability distributions for individual galaxies computed on a redshift grid.  The specific redshift grid is stored in pdf/zgrid'}
        self._info_dict['photoz_mode']={'units':'unitless','description':'mode of the posterior pdf for an individual galaxy'}
        self._info_dict['photoz_mean']={'units':'unitless','description':'mean value of the posterior pdf for an individual galaxy'}
        self._info_dict['photoz_median']={'units':'unitless','description':'median value of the posterior pdf for an individual galaxy, defined by where the CDF of the distribution is 0.5 '}
        self._info_dict['photoz_mode_ml']={'units':'unitless','description':'index value of pdf/zgrid corresponding to the max likelihood redshift *before* the magnitude/type prior is applied'}
        self._info_dict['photoz_odds']={'units':'unitless','description':'ODDS parameter: the integral of the posterior within a fixed interval around the mode of the posterior used to quantify photo-z quality.  A high ODDS value close to 1.0 indicated a compact, single peaked posterior, while low ODDS values could indicate multiple peaks or a broad posterior'}

    def _get_quantity_info_dict(self, quantity, default=None):
        return self._info_dict.get(quantity,default)

    def _generate_native_quantity_list(self):
        return list(self._quantity_modifiers.values()) + list(self._native_filter_quantities)

    @property
    def photoz_pdf_bin_centers(self):
        """
        expose self._pdf_bin_centers as a public property.
        """
        return self._pdf_bin_centers

    def generate_metadata(self, write_to_yaml=False):
        """
        generate metadata
        """
        meta = list()
        for fname in sorted(os.listdir(self.base_dir)):
            if not self._filename_re.match(fname):
                continue

            file_path = os.path.join(self.base_dir, fname)
            try:
                df = pd.read_hdf(file_path, 'df')

            except (IOError, OSError):
                warnings.warn('Cannot access {}; skipped'.format(file_path))
                continue

            meta_tract = {
                'tract': int(df['tract'].iloc[0]),
                'filename': fname,
            }

            # Each file contains all patches in one tract,
            # but we want to be able to iterate over patches as well.
            # Here, we find the indices where the adjacent patch values differ,
            # and we record the slice indices for each patch.
            patches = df['patch'].values.astype('<U')
            indices = np.flatnonzero(np.concatenate(([True], patches[1:] != patches[:-1], [True])))
            indices = np.vstack((indices[:-1], indices[1:])).T
            meta_tract['patches'] = [{'patch': str(patches[i]), 'slice': [int(i), int(j)]} for i, j in indices]

            meta.append(meta_tract)

        if write_to_yaml:
            if self._metadata_path and os.path.isfile(self._metadata_path):
                warnings.warn('Overwriting metadata file `{0}`, which is backed up at `{0}.bak`'.format(self._metadata_path))
                shutil.copyfile(self._metadata_path, self._metadata_path + '.bak')
            with open(self._metadata_path, 'w') as meta_stream:
                yaml.dump(meta, meta_stream)

        return meta

    def _iter_native_dataset(self, native_filters=None):
        current_fname = None
        for meta_tract in self._metadata:
            for meta_patch in meta_tract['patches']:
                tract_patch = {'tract': meta_tract['tract'], 'patch': meta_patch['patch']}
                if native_filters and not native_filters.check_scalar(tract_patch):
                    continue

                if current_fname != meta_tract['filename']:
                    current_fname = meta_tract['filename']
                    df = pd.read_hdf(os.path.join(self.base_dir, current_fname), 'df')

                slice_this = slice(*meta_patch['slice'])
                def native_quantity_getter(native_quantity):
                    # pylint: disable=W0640,E0606
                    # variables (df and slice_this) intentionally defined in loop
                    if native_quantity == '_FULL_PDF':
                        return df.iloc[slice_this, :self._n_pdf_bins].values
                    return df[native_quantity].values[slice_this]
                yield native_quantity_getter

    # Native quantity names in the photo-z catalog are too uninformative
    # Since native quantities will become regular quantities in composite catalog,
    # let us hide them all.
    def list_all_quantities(self, include_native=False, with_info=False):
        """
        Return a list of all available quantities in this catalog.
        If *with_info* is `True`, return a dict with quantity info.
        See also: list_all_native_quantities
        """
        return super(PhotoZCatalog, self).list_all_quantities(with_info=with_info)


class PhotoZFileObject():
    """
    HDF5 file wrapper for PhotoZCatalog2
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

        tract, patch_x, patch_y, index = match.groups()

        self.path = path
        self.tract = int(tract)
        self.patch = '{},{}'.format(patch_x, patch_y)
        self.index = int(index)
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
        return list(self._keys) + ['tract', 'patch']

    def __len__(self):
        if self._len is None:
            self._len = self.handle[first(self.keys())].shape[0]
        return self._len

    def __getitem__(self, key):
        if key == 'tract':
            return np.repeat(self.tract, len(self))
        if key == 'patch':
            return np.repeat(self.patch, len(self))
        return self.handle[key][()]

    get = __getitem__

    @property
    def handle(self):
        if self._handle is None:
            self._handle = h5py.File(self.path, mode='r')
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


class PhotoZCatalog2(BaseGenericCatalog):

    _FILE_RE_PATTERN = r'photoz_pdf_Run\d\.[0-9a-z]+_tract_(\d{4})_patch_(\d)_(\d)_idx_(\d+).hdf5'
    _FILE_GLOB_PATTERN = 'photoz_*.hdf5'
    _TRACT_GLOB_PATTERN = '*'

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', self._FILE_RE_PATTERN))
        self._file_glob_pattern = kwargs.get('filename_glob_pattern', self._FILE_GLOB_PATTERN)
        self._tract_glob_pattern = kwargs.get('tract_glob_pattern', self._TRACT_GLOB_PATTERN)
        self._datasets = self._generate_datasets()

        self._quantity_modifiers = {
            'id': 'id/galaxy_id',
            'photoz_pdf': 'pdf/pdf',
            'photoz_mode': 'point_estimates/z_mode',
            'photoz_mean': 'point_estimates/z_mean',
            'photoz_median': 'point_estimates/z_median',
            'photoz_mode_ml': 'point_estimates/z_mode_ml',
            'photoz_mode_ml_red_chi2': 'point_estimates/z_mode_ml_red_chi2',
            'photoz_odds': 'point_estimates/ODDS',
        }

        self._native_filter_quantities = {'tract', 'patch'}
        self._info_dict = {}
        self._info_dict['galaxy_id']={'units':'unitless',
                                 'description': 'ID of galaxy matching the entry from the main catalog'}
        self._info_dict['photoz_mode_ml_red_chi2']={'units':'unitless',
                                                    'description':'reduced chi sq at the max likelihood redshift and type.  A high chi2 value indicates a potentially bad fit'}
        self._info_dict['photoz_pdf']={'units':'unitless','description':'posterior probability distributions for individual galaxies computed on a redshift grid.  The specific redshift grid is stored in pdf/zgrid'}
        self._info_dict['photoz_mode']={'units':'unitless','description':'mode of the posterior pdf for an individual galaxy'}
        self._info_dict['photoz_mean']={'units':'unitless','description':'mean value of the posterior pdf for an individual galaxy'}
        self._info_dict['photoz_median']={'units':'unitless','description':'median value of the posterior pdf for an individual galaxy, defined by where the CDF of the distribution is 0.5 '}
        self._info_dict['photoz_mode_ml']={'units':'unitless','description':'index value of pdf/zgrid corresponding to the max likelihood redshift *before* the magnitude/type prior is applied'}
        self._info_dict['photoz_odds']={'units':'unitless','description':'ODDS parameter: the integral of the posterior within a fixed interval around the mode of the posterior used to quantify photo-z quality.  A high ODDS value close to 1.0 indicated a compact, single peaked posterior, while low ODDS values could indicate multiple peaks or a broad posterior'}

    def _get_quantity_info_dict(self, quantity, default=None):
        return self._info_dict.get(quantity,default)

    def _generate_native_quantity_list(self):
        return first(self._datasets).keys()

    def _generate_datasets(self):
        datasets = list()
        for path in glob.glob(os.path.join(self.base_dir, self._tract_glob_pattern, self._file_glob_pattern)):
            try:
                dataset = PhotoZFileObject(path, self._filename_re)
            except ValueError:
                continue
            datasets.append(dataset)
        return sorted(datasets, key=(lambda d: d.index))

    @property
    def photoz_pdf_bin_centers(self):
        """
        expose self._pdf_bin_centers as a public property.
        """
        return first(self._datasets).pdf_bins

    def _iter_native_dataset(self, native_filters=None):
        for dataset in self._datasets:
            tract_patch = {'tract': dataset.tract, 'patch': dataset.patch}
            if native_filters and not native_filters.check_scalar(tract_patch):
                continue
            yield dataset.get
            dataset.close() # to avoid OS complaining too many open files

    def close_all_file_handles(self):
        """Clear all cached file handles"""
        for dataset in self._datasets:
            dataset.close()

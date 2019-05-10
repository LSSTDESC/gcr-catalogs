"""
Photo-z catalog reader

This reader was designed by Yao-Yuan Mao,
based a photo-z catalog provided by Sam Schmidt, in Feb 2019.
"""

import re
import os
import warnings
import shutil

import yaml
import numpy as np
import pandas as pd

from GCR import BaseGenericCatalog

__all__ = ['PhotoZCatalog']

FILE_PATTERN = r'run\d\.\d+[a-z]+_PZ_tract_\d+\.h5$'
METADATA_FILENAME = 'metadata.yaml'
PDF_BIN_INFO = {
    'start': 0.005,
    'stop': 1.01,
    'step': 0.01,
    'decimals_to_round': 3,
}

class PhotoZCatalog(BaseGenericCatalog):

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', FILE_PATTERN))
        _metadata_filename = kwargs.get('metadata_filename', METADATA_FILENAME)
        self._metadata_path = os.path.join(self.base_dir, _metadata_filename)

        self._pdf_bin_info = kwargs.get('pdf_bin_info', PDF_BIN_INFO)
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
            meta_tract['patches'] = [{'patch': patches[i], 'slice': (i, j)} for i, j in indices]

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
                    # pylint: disable=W0640
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

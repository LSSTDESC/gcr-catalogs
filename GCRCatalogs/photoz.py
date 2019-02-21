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


class PhotoZCatalog(BaseGenericCatalog):

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', FILE_PATTERN))
        _metadata_filename = kwargs.get('metadata_filename', METADATA_FILENAME)
        self._metadata_path = os.path.join(self.base_dir, _metadata_filename)

        if self._metadata_path and os.path.isfile(self._metadata_path):
            with open(self._metadata_path, 'r') as meta_stream:
                self._metadata = yaml.load(meta_stream)
        else:
            self._metadata = self.generate_metadata()

        self._quantity_modifiers = {
            'id': 'ID',
            'pz_z_peak': 'z_peak',
        }
        for i, z in enumerate(self._metadata['pdf_bin_centers']):
            z_str = '{:.3f}'.format(z)
            z_str = z_str.replace('.', '_')
            self._quantity_modifiers['pz_pdf_z{}'.format(z_str)] = i

        self._native_filter_quantities = {'tract', 'patch'}

    def _generate_native_quantity_list(self):
        return list(self._quantity_modifiers.values()) + list(self._native_filter_quantities)

    def generate_metadata(self, write_to_yaml=False):
        """
        generate metadata
        """
        datasets = list()
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

            patches = df['patch'].values.astype('<U')
            indices = np.flatnonzero(np.concatenate(([True], patches[1:] != patches[:-1], [True])))
            indices = np.vstack((indices[:-1], indices[1:])).T
            meta_tract['patches'] = [{'patch': patches[i], 'slice': (i, j)} for i, j in indices]

            datasets.append(meta_tract)

        meta = {
            'datasets': datasets,
            'pdf_bin_centers': np.round(np.linspace(0.005, 1.005, 101), 3).tolist(),
        }

        if write_to_yaml:
            if self._metadata_path and os.path.isfile(self._metadata_path):
                warnings.warn('Overwriting metadata file `{0}`, which is backed up at `{0}.bak`'.format(self._metadata_path))
                shutil.copyfile(self._metadata_path, self._metadata_path + '.bak')
            with open(self._metadata_path, 'w') as meta_stream:
                yaml.dump(meta, meta_stream)

        return meta

    def _iter_native_dataset(self, native_filters=None):
        current_fname = None
        for meta_tract in self._metadata['datasets']:
            for meta_patch in meta_tract['patches']:
                tract_patch = {'tract': meta_tract['tract'], 'patch': meta_patch['patch']}
                if native_filters and not native_filters.check_scalar(tract_patch):
                    continue

                if current_fname != meta_tract['filename']:
                    current_fname = meta_tract['filename']
                    df = pd.read_hdf(os.path.join(self.base_dir, current_fname), 'df')

                slice_this = slice(*meta_patch['slice'])
                def native_quantity_getter(native_quantity):
                    return df[native_quantity].values[slice_this]
                yield native_quantity_getter

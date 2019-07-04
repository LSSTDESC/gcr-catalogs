"""
PZ mag err catalog (matched to cosmoDC2) reader

This reader was designed by Yao-Yuan Mao,
based a catalog provided by Sam Schmidt.
"""

import re
import os
import pandas as pd
from GCR import BaseGenericCatalog

from .utils import first

__all__ = ['PZMagErrCatalog']

FILE_PATTERN = r'z_(\d)\S+healpix_(\d+)_magwerr\.h5$'

class PZMagErrCatalog(BaseGenericCatalog):

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

    def _generate_native_quantity_list(self):
        return pd.read_hdf(first(self._healpix_files.values())).columns.tolist()

    def _iter_native_dataset(self, native_filters=None):
        for (zlo_this, hpx_this), file_path in self._healpix_files.items():
            d = {'healpix_pixel': hpx_this, 'redshift_block_lower': zlo_this}
            if native_filters is not None and not native_filters.check_scalar(d):
                continue
            df = pd.read_hdf(file_path)
            yield lambda col: df[col].values # pylint: disable=cell-var-from-loop

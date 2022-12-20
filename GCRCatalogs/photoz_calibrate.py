"""
PZCalibrate redshift reference objects catalog reader.

This reader was designed by Yao-Yuan Mao,
based a catalog of "spectroscopic" reference objects for use in ensemble
redshift estimation that includes cross-correlation. Catalog created by Chris
Morrison in Mar 2019.
"""

import re
import os

import numpy as np
from GCR import BaseGenericCatalog

from .utils import first

__all__ = ['PZCalibrateCatalog']

FILE_PATTERN = r'z_(\d)\S+healpix_(\d+)_pz_calib\.npz$'


class PZCalibrateCatalog(BaseGenericCatalog):

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

        self._quantity_dict = {
            "QSO": "Flag selecting QSOs by BlackHoleMass and EddingtonRatio. Objects have a mag/redshift "
                   "distributions similar to those in DESI and are meant to be used as reference objects "
                   "in cross-correlation redshift analyses.",
            "LRG": "Flag selecting LRGs by stellar mass. Objects have a mag/redshift "
                   "distributions similar to those in DESI and are meant to be used as reference objects "
                   "in cross-correlation redshift analyses.",
            "ELG": "Flag selecting ELGs by star formation rate. Objects have a mag/redshift "
                   "distributions similar to those in DESI and are meant to be used as reference objects "
                   "in cross-correlation redshift analyses.",
            "MagLim": "Flag selection all objects R<19.4. Objects have a mag/redshift "
                      "distributions similar to those in DESI and are meant to be used as reference objects "
                      "in cross-correlation redshift analyses.",
            "AllReferences": "Union of QSO, LRG, ELG, and MagLim flags. Objects have a mag/redshift "
                             "distributions similar to those in DESI and are meant to be used as reference "
                             "objects in cross-correlation redshift analyses.",
        }
        
        self._quantity_modifiers = {q: q for q in self._quantity_dict}

    def _get_quantity_info_dict(self, quantity, default=None):
        """Return a dictionary with descriptive information for a quantity

        Returned information includes a quantity description, quantity units, whether
        the quantity is defined in the DPDD, and if the quantity is available in GCRbase.

        Args:
            quantity   (str): The quantity to return information for
            default (object): Value to return if no information is available (default None)

        Returns:
            String describing the quantity.
        """
        return self._quantity_dict.get(quantity, default)

    def _generate_native_quantity_list(self):
        return list(np.load(first(self._healpix_files.values())).keys())

    def _iter_native_dataset(self, native_filters=None):
        for (zlo_this, hpx_this), file_path in self._healpix_files.items():
            d = {'healpix_pixel': hpx_this, 'redshift_block_lower': zlo_this}
            if native_filters is not None and not native_filters.check_scalar(d):
                continue
            yield np.load(file_path).__getitem__

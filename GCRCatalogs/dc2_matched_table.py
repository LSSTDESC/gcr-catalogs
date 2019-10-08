"""
DC2 matched table reader

This reader was written by Eve Kovacs
based on a matching table provided by Javier Sanchez .
"""

import numpy as np
import numpy.ma as ma
from astropy.io import fits
from GCRCatalogs import BaseGenericCatalog

__all__ = ['DC2MatchedTable']

class DC2MatchedTable(BaseGenericCatalog):

    def _subclass_init(self, **kwargs):

        """
        DC2MatchedTable reader, inherited from BaseGenericCatalog class 
        """
        self._filename = kwargs.get('filename', None)
        if not self._filename:
            print('Filename for matching table required')
            return
        object_id = kwargs.get('object_id', 'objectId')
        truth_id = kwargs.get('truth_id', 'truthId')
        match_flag = kwargs.get('match_flag', 'is_matched')
        is_star = kwargs.get('is_star', 'is_star')
        self._version = kwargs.get('version', '')
        self._truth_version = kwargs.get('truth_version', '')

        # check matched table quantities
        with fits.open(self._filename) as hdul:
            cols = hdul[1].columns.names
            if not object_id in cols or not match_flag in cols or not is_star in cols or not truth_id in cols:
                print('Matching table does not have minimal expected columns')
                return

            self._galaxy_match_mask = (~hdul[1].data[is_star]) & (hdul[1].data[match_flag])
            self._matched_galaxy_count = np.count_nonzero(self._galaxy_match_mask)
            self._star_match_mask = (hdul[1].data[is_star]) & (hdul[1].data[match_flag])
            self._matched_star_count = np.count_nonzero(self._star_match_mask)
            
        # modify native quantities
        self._quantity_modifiers = {}
        modified_quantity_list = [c for c in cols if not is_star in c and not match_flag in c]
        for q in modified_quantity_list:
            self._quantity_modifiers[q + '_galaxy'] =  (lambda x: x[self._galaxy_match_mask], q)
            self._quantity_modifiers[q + '_star'] =  (lambda x: x[self._star_match_mask], q)


    def _generate_native_quantity_list(self):
        """
        Return an iterable of all native quantity names.
        """
        with fits.open(self._filename) as hdul:
            return hdul[1].columns.names

        
    def _iter_native_dataset(self, native_filters=None):
        """
        Must yield a callable, *native_quantity_getter*.
        Must return a numpy 1d array.
        """
        assert not native_filters, '*native_filters* is not supported'
        with fits.open(self._filename) as hdul:
            def native_quantity_getter(native_quantity):
                return hdul[1].data[native_quantity]
            yield native_quantity_getter

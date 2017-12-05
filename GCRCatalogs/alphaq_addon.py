"""
Add-on catalogs for alpha q.
"""
from __future__ import division
import os
import numpy as np
import h5py
from itertools import product
from GCR import BaseGenericCatalog

__all__ = ['AlphaQTidalCatalog']


class AlphaQTidalCatalog(BaseGenericCatalog):
    """
    Alpha Q tidal catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """
    is_addon = True

    def _subclass_init(self, **kwargs):

        self._filename = kwargs['filename']
        assert os.path.isfile(self._filename), 'Catalog file {} does not exist'.format(self._filename)

        self._quantity_modifiers = {
            'galaxy_id': None,
            'tidal_eigvals': 'eigvals',
            'tidal_eigvects': 'eigvects',
        }
        for i in range(3):
            self._quantity_modifiers['tidal_eigvals[{}]'.format(i)] = 'eigvals/{}'.format(i)
        for i, j in product(range(3), repeat=2):
            self._quantity_modifiers['tidal_eigvects[{}][{}]'.format(i, j)] = 'eigvects/{}/{}'.format(i, j)


    def _generate_native_quantity_list(self):
        native_quantities = set()
        with h5py.File(self._filename, 'r') as fh:
            data = fh['tidal'].value
            for name, (dt, _) in data.dtype.fields.items():
                native_quantities.add(name)
                if dt.shape:
                    for indices in product(*map(range, dt.shape)):
                        native_quantities.add((name + '/' + '/'.join(map(str, indices))))
        return native_quantities


    def _iter_native_dataset(self, native_filters=None):
        assert not native_filters, '*native_filters* is not supported'
        with h5py.File(self._filename, 'r') as fh:
            data = fh['tidal'].value
            def native_quantity_getter(native_quantity):
                items = native_quantity.split('/')
                name = items[0]
                cols = tuple(items[1:])
                return data[name][(...,)+cols] if cols else data[name]
            yield native_quantity_getter

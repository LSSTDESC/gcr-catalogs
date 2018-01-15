"""
Add-on catalogs for alpha q.
"""
from __future__ import division
import os
import numpy as np
import h5py
from itertools import product
from GCR import BaseGenericCatalog

from .alphaq import AlphaQGalaxyCatalog

__all__ = ['AlphaQTidalCatalog', 'AlphaAddonCatalog']


class AlphaQAddonCatalog(AlphaQGalaxyCatalog):
    """
    Addon to the AlphaQ catalog that can add extra quanities to the baseline
    catalog
    """
    def _subclass_init(self, **kwargs):
        # Loads main catalog
        super(self.__class__, self)._subclass_init(**kwargs)

        # Sets the filename of the addon
        self._addon_filename = kwargs['addon_filename']
        assert os.path.isfile(self._addon_filename), 'Addon file {} does not exist'.format(self._addon_filename)
        self._addon_group = kwargs['addon_group']

    def _generate_native_quantity_list(self):
        # Generates the native quantity list for the parent catalog
        native_quantities = super(self.__class__, self)._generate_native_quantity_list()

        # Loads the additional data provided by the addon file
        with h5py.File(self._addon_filename, 'r') as fh:
            hgroup = fh[self._addon_group]
            hobjects = []
            #get all the names of objects in this tree
            hgroup.visit(hobjects.append)
            #filter out the group objects and keep the dataste objects
            hdatasets = [hobject for hobject in hobjects if type(hgroup[hobject]) == h5py.Dataset]
            addon_native_quantities = set(hdatasets)

        self._addon_native_quantities = addon_native_quantities

        return native_quantities.union(addon_native_quantities)

    def _iter_native_dataset(self, native_filters=None):
        """
        Caution, fully overiddes parent function
        """
        assert not native_filters, '*native_filters* is not supported'
        with h5py.File(self._file, 'r') as fh:
            with h5py.File(self._addon_filename, 'r') as fh_addon:
                def native_quantity_getter(native_quantity):
                    if native_quantity in self._addon_native_quantities:
                        return fh_addon['{}/{}'.format(self._addon_group,native_quantity)].value
                    else:
                        return fh['galaxyProperties/{}'.format(native_quantity)].value
                yield native_quantity_getter


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
                        native_quantities.add((name + '/' + '/'.join(map(str, indices))).strip('/'))
        return native_quantities


    def _iter_native_dataset(self, native_filters=None):
        with h5py.File(self._filename, 'r') as fh:
            data = fh['tidal'].value
            def native_quantity_getter(native_quantity):
                if '/' not in native_quantity:
                    return data[native_quantity]
                items = native_quantity.split('/')
                name = items[0]
                cols = (slice(None),) + tuple((int(i) for i in items[1:]))
                return data[name][cols]
            yield native_quantity_getter

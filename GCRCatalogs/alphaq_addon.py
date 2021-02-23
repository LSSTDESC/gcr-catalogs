"""
Add-on catalogs for alpha q.
"""
import os
from itertools import product
import h5py
from GCR import BaseGenericCatalog

__all__ = ['AlphaQTidalCatalog', 'AlphaQAddonCatalog']

class AlphaQAddonCatalog(BaseGenericCatalog):
    """
    Addon to the AlphaQ catalog that can add extra quanities to the baseline
    catalog
    """
    def _subclass_init(self, **kwargs):
        # Sets the filename of the addon
        self._addon_filename = kwargs['addon_filename']
        assert os.path.isfile(self._addon_filename), 'Addon file {} does not exist'.format(self._addon_filename)
        self._addon_group = kwargs['addon_group']

    def _generate_native_quantity_list(self):
        # Loads the additional data provided by the addon file
        with h5py.File(self._addon_filename, 'r') as fh:
            hgroup = fh[self._addon_group]
            hobjects = []
            #get all the names of objects in this tree
            hgroup.visit(hobjects.append)
            #filter out the group objects and keep the dataste objects
            hdatasets = [hobject for hobject in hobjects if isinstance(hgroup[hobject], h5py.Dataset)]
            addon_native_quantities = set(hdatasets)
        return addon_native_quantities

    def _iter_native_dataset(self, native_filters=None):
        """
        Caution, fully overiddes parent function
        """
        assert not native_filters, '*native_filters* is not supported'
        with h5py.File(self._addon_filename, 'r') as fh_addon:
            def native_quantity_getter(native_quantity):
                return fh_addon['{}/{}'.format(self._addon_group,native_quantity)][()]
            yield native_quantity_getter


class AlphaQTidalCatalog(BaseGenericCatalog):
    """
    Alpha Q tidal catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """
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
            data = fh['tidal'][()]
            for name, (dt, _) in data.dtype.fields.items():  # pylint: disable=no-member
                native_quantities.add(name)
                if dt.shape:
                    for indices in product(*map(range, dt.shape)):
                        native_quantities.add((name + '/' + '/'.join(map(str, indices))).strip('/'))
        return native_quantities

    def _iter_native_dataset(self, native_filters=None):
        with h5py.File(self._filename, 'r') as fh:
            data = fh['tidal'][()]
            def native_quantity_getter(native_quantity):
                if '/' not in native_quantity:
                    return data[native_quantity]
                items = native_quantity.split('/')
                name = items[0]
                cols = (slice(None),) + tuple((int(i) for i in items[1:]))
                return data[name][cols]
            yield native_quantity_getter

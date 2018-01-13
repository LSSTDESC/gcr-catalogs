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

try:
  import tensorflow as tf
  HAS_TENSORFLOW = True
except ImportError:
  HAS_TENSORFLOW = False

__all__ = ['AlphaQTidalCatalog', 'AlphaQKnotsCatalog']

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


class AlphaQKnotsCatalog(AlphaQGalaxyCatalog):
    """
    Addon to the AlphaQ catalog that adds a RandomWalk component to the galaxy
    """

    def _subclass_init(self, **kwargs):
        super(self.__class__, self)._subclass_init(**kwargs)

        # Adds additional field required by the sampling code
        self._quantity_modifiers['morphology/BTR'] = (lambda x,y : x/(x+y), 'SDSS_filters/spheroidLuminositiesStellar:SDSS_i:observed', 'SDSS_filters/diskLuminositiesStellar:SDSS_i:observed')

        if not HAS_TENSORFLOW:
            raise TypeError('The RandomWalk catalog requires tensorflow')

        self._model_dir = kwargs['model_dir']
        self._function_name = kwargs['function_name']
        self._batch_size = 10000
        assert os.path.exists(self._model_dir), 'Model directory {} does not exist'.format(self._model_dir)

        # Opens tf Session
        self._sess = tf.Session()

        # Load the saved tensorflow model
        model = tf.saved_model.loader.load(self._sess, tags=['serve'], export_dir=self._model_dir)

        # Extracts the signature definition of the function to use
        definition = model.signature_def[self._function_name]

        requested_quantities = tuple([n for n in definition.inputs])
        generated_quantities = tuple([n for n in definition.outputs])

        self._native_quantities = []

        # Define the serving function
        def get_function_mapper(output_name):

            def func(*x):
                x_size = len(x[0])
                n_batches = x_size // self._batch_size
                n_batches += 0 if (x_size % self._batch_size) == 0 else 1

                # list storing the results
                res = []
                # Create data dictionary
                feed_dict = {}
                for b in range(n_batches):
                    for i, n in enumerate(definition.inputs):
                        feed_dict[definition.inputs[n].name] = x[i][b*self._batch_size:min((b+1)*self._batch_size, x_size)].astype('float32')
                    res.append(self._sess.run(definition.outputs[output_name].name, feed_dict=feed_dict))
                return np.concatenate(res)
            return func

        # Add the quantity modifier
        for quantity in generated_quantities:
            self.add_modifier_on_derived_quantities(quantity, get_function_mapper( quantity), *requested_quantities )

"""
redMaGiC catalog class.
"""
import os
import functools
from GCR import BaseGenericCatalog
from .cosmology import FlatLambdaCDM
from .redmapper import FitsFile

__all__ = ['RedmagicCatalog']


class RedmagicCatalog(BaseGenericCatalog):
    """
    redMaGiC red galaxy catalog class.  Uses generic quantity and
    filter mechanism defined by BaseGenericCatalog class.
    """
    def _subclass_init(self, catalog_root_dir,
                       catalog_path_template,
                       use_cache=True,
                       **kwargs): #pylint: disable=W0221

        if not os.path.isdir(catalog_root_dir):
            raise RuntimeError("Catalog directory %s does not exist." % (catalog_root_dir))

        self._catalog_path_template = {k: os.path.join(catalog_root_dir, v) for k, v in catalog_path_template.items()}
        self._file_name = self._catalog_path_template['redmagic']

        self.cosmology = None
        if 'cosmology' in kwargs:
            self.cosmology = FlatLambdaCDM(**kwargs['cosmology'])

        self.lightcone = kwargs.get('lightcone')
        self.sky_area = kwargs.get('sky_area')
        self.cache = dict() if use_cache else None
        self._quantity_modifiers = self._generate_quantity_modifiers()

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
            'id': None,
            'ra': None,
            'dec': None,
            'refmag_z_lsst': 'refmag',
            'z_lum': 'lum',
            'redshift': 'zredmagic',
            'redshift_err': 'zredmagic_e',
            'chisq': None,
            'zspec': None
        }

        for i, band in enumerate(['g', 'r', 'i', 'z', 'y']):
            quantity_modifiers[f'mag_{band}_lsst'] = f'mag/{i}'
            quantity_modifiers[f'magerr_{band}_lsst'] = f'mag_err/{i}'

        for i in range(4):
            quantity_modifiers[f'zredmagic_samp_{i}'] = f'zredmagic_samp/{i}'

        return quantity_modifiers

    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise RuntimeError("*native_filters* not supported")

        yield functools.partial(self._native_quantity_getter)

    def _generate_native_quantity_list(self):
        native_quantities = set()

        f = FitsFile(self._file_name)
        for name, (dt, _) in f.data.dtype.fields.items():
            if dt.shape:
                for i in range(dt.shape[0]):
                    native_quantities.add('/'.join((name, str(i))))
            else:
                native_quantities.add(name)
        return native_quantities

    def _native_quantity_getter(self, native_quantity):
        native_quantity = native_quantity.split('/')
        if len(native_quantity) not in (1, 2):
            raise RuntimeError('something wrong with the native_quantity {}'.format(native_quantity))
        column = native_quantity.pop(0)
        data = FitsFile(self._file_name).data[column]
        if native_quantity:
            data = data[:, int(native_quantity.pop(0))]
        return data.byteswap().newbyteorder()


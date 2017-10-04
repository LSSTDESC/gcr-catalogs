"""
Buzzard galaxy catalog class.
"""
from __future__ import division, print_function
import os
import re
import numpy as np
from astropy.io import fits
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog
from .register import register_reader

__all__ = ['BuzzardGalaxyCatalog']


class FitsFile(object):
    def __init__(self, path):
        self._path = path
        self._file_handle = fits.open(self._path, mode='readonly', memmap=True, lazy_load_hdus=True)
        self.data = self._file_handle[1].data

    def __del__(self):
        del self.data
        del self._file_handle[1].data
        self._file_handle.close()
        del self._file_handle


class BuzzardGalaxyCatalog(BaseGenericCatalog):
    """
    Buzzard galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self,
                       catalog_root_dir,
                       catalog_path_template,
                       cosmology,
                       halo_mass_def='vir',
                       lightcone=True,
                       healpix_pixels=None,
                       high_res=False,
                       **kwargs):

        assert(os.path.isdir(catalog_root_dir)), 'Catalog directory {} does not exist'.format(catalog_root_dir)

        self._catalog_path_template = {k: os.path.join(catalog_root_dir, v) for k, v in catalog_path_template.items()}
        self._default_subset = 'truth' if 'truth' in self._catalog_path_template else next(iter(self._catalog_path_template.keys()))

        self._default_healpix_pixels = tuple(healpix_pixels or self._get_healpix_pixels())
        self.healpix_pixels = None
        self.reset_healpix_pixels()
        self.check_healpix_pixels()
        self._pre_filter_quantities = {'healpix_pixel'}

        self.cosmology = FlatLambdaCDM(**cosmology)
        self.halo_mass_def = halo_mass_def
        self.lightcone = bool(lightcone)

        _c = 299792.458
        _abs_mask_func = lambda x: np.where(x==99.0, np.nan, x + 5 * np.log10(self.cosmology.h))
        _mask_func = lambda x: np.where(x==99.0, np.nan, x)

        if high_res:
            #TODO: add quantity modifiers
            print('Warning! high_res reader has not been fully implemented. For now only native quantities would work!')
            self._quantity_modifiers = {
                'ra_true': 'truth/RA',
                'dec_true': 'truth/DEC',
            }
        else:
            self._quantity_modifiers = {
                'galaxy_id': 'truth/ID',
                'redshift': (lambda zt, x, y, z, vx, vy, vz: zt + (x*vx+y*vy+z*vz)/np.sqrt(x*x+y*y+z*z)/_c,
                    'truth/Z', 'truth/PX', 'truth/PY', 'truth/PZ', 'truth/VX', 'truth/VY', 'truth/VZ'),
                'redshift_true': 'truth/Z',
                'ra': 'truth/RA',
                'dec': 'truth/DEC',
                'ra_true': 'truth/TRA',
                'dec_true': 'truth/TDEC',
                'halo_id': 'truth/HALOID',
                'halo_mass': (lambda x: x/self.cosmology.h, 'truth/M200'),
                'is_central': (lambda x: x.astype(np.bool), 'truth/CENTRAL'),
                'ellipticity_1': 'truth/EPSILON/0',
                'ellipticity_2': 'truth/EPSILON/1',
                'ellipticity_1_true': 'truth/TE/0',
                'ellipticity_2_true': 'truth/TE/1',
                'size': 'truth/SIZE',
                'size_true': 'truth/TSIZE',
                'shear_1': 'truth/GAMMA1',
                'shear_2': 'truth/GAMMA2',
                'convergence': 'truth/KAPPA',
                'magnification': 'truth/MU',
                'position_x': (lambda x: x/self.cosmology.h, 'truth/PX'),
                'position_y': (lambda x: x/self.cosmology.h, 'truth/PY'),
                'position_z': (lambda x: x/self.cosmology.h, 'truth/PZ'),
                'velocity_x': 'truth/VX',
                'velocity_y': 'truth/VY',
                'velocity_z': 'truth/VZ',
            }

            for i, b in enumerate('grizY'):
                self._quantity_modifiers['Mag_true_{}_des_z01'.format(b)] = (_abs_mask_func, 'truth/AMAG/{}'.format(i))
                self._quantity_modifiers['Mag_true_{}_any'.format(b)] = (_abs_mask_func, 'truth/AMAG/{}'.format(i))
                self._quantity_modifiers['mag_{}_des'.format(b)] = (_mask_func, 'truth/OMAG/{}'.format(i))
                self._quantity_modifiers['mag_{}_any'.format(b)] = (_mask_func, 'truth/OMAG/{}'.format(i))
                self._quantity_modifiers['magerr_{}_des'.format(b)] = (_mask_func, 'truth/OMAGERR/{}'.format(i))
                self._quantity_modifiers['magerr_{}_any'.format(b)] = (_mask_func, 'truth/OMAGERR/{}'.format(i))



    def _get_healpix_pixels(self):
        path = self._catalog_path_template[self._default_subset]
        fname_pattern = re.escape(os.path.basename(path)).replace(r'\{', '{').replace(r'\}', '}').format(r'(\d+)')
        path = os.path.dirname(path)
        healpix_pixels = list()
        for f in os.listdir(path):
            m = re.match(fname_pattern, f)
            if m is not None:
                healpix_pixels.append(int(m.groups()[0]))
        healpix_pixels.sort()
        return healpix_pixels


    def check_healpix_pixels(self):
        assert all(os.path.isfile(path.format(i)) for path in self._catalog_path_template.values() for i in self.healpix_pixels)


    def reset_healpix_pixels(self):
        """
        Reset the list of healpixels used by the reader.
        """
        self.healpix_pixels = list(self._default_healpix_pixels)


    def _generate_native_quantity_list(self):
        native_quantities = {'healpix_pixel'}
        healpix = next(iter(self.healpix_pixels))
        for subset in self._catalog_path_template.keys():
            f = self._open_dataset(healpix, subset)
            for name, (dt, size) in f.data.dtype.fields.items():
                if dt.shape:
                    for i in range(dt.shape[0]):
                        native_quantities.add('/'.join((subset, name, str(i))))
                else:
                    native_quantities.add('/'.join((subset, name)))
        return native_quantities


    def _iter_native_dataset(self, pre_filters=None):
        cache = dict()
        for i in self.healpix_pixels:
            args = dict(healpix_pixel=i)
            if (not pre_filters) or all(f[0](*(args[k] for k in f[1:])) for f in pre_filters):
                yield i, cache
        for key in list(cache.keys()):
            del cache[key]


    def _open_dataset(self, healpix, subset, use_cache=None):
        path = self._catalog_path_template[subset].format(healpix)

        if use_cache is None:
            return FitsFile(path)

        key = (healpix, subset)
        if key not in use_cache:
            use_cache[key] = FitsFile(path)
        return use_cache[key]


    def _fetch_native_quantity(self, dataset, native_quantity):
        healpix, cache = dataset
        if native_quantity == 'healpix_pixel':
            data = np.empty(self._open_dataset(healpix, self._default_subset, cache).data.shape, np.int)
            data.fill(healpix)
        else:
            native_quantity = native_quantity.split('/')
            assert len(native_quantity) in {2,3}, 'something wrong with the native_quantity {}'.format(native_quantity)
            subset = native_quantity.pop(0)
            column = native_quantity.pop(0)
            data = self._open_dataset(healpix, subset, cache).data[column]
            if native_quantity:
                data = data[:,int(native_quantity.pop(0))]
        return data


# Registers the reader
register_reader(BuzzardGalaxyCatalog)

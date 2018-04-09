"""
instance catalog reader
"""
from __future__ import division, print_function
import os
import gzip
from functools import partial
from collections import OrderedDict
import numpy as np
import pandas as pd
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog

__all__ = ['InstanceCatalog']


def _mag2flux(mag):
    return 10**(-0.4*mag) * 3631.0e6 #uJy

def _flux2mag(flux):
    return -2.5 * np.log10(flux/3631.0e6)

def _get_total_flux(mag_bulge, mag_disk, result='total_flux'):
    f_bulge = np.where(np.isnan(mag_bulge), 0, _mag2flux(mag_bulge))
    f_disk = np.where(np.isnan(mag_disk), 0, _mag2flux(mag_disk))
    total_flux = f_bulge + f_disk
    if result == 'bulge_frac':
        return f_bulge/total_flux
    if result == 'total_mag':
        return _flux2mag(total_flux)
    return total_flux

_get_total_mag = partial(_get_total_flux, result='total_mag')

_get_bulge_fraction = partial(_get_total_flux, result='bulge_frac')


def _get_one(x, y):
    return np.where(np.isnan(x), y, x)


def sersic_second_moments(n, hlr, q, beta):
    if n == 1:
        cn = 1.06502
    elif n == 4:
        cn = 10.8396
    else:
        raise RuntimeError('Invalid Sersic index n.')
    e_mag = (1.-q)/(1.+q)
    e_mag_sq = e_mag**2
    e1 = e_mag*np.cos(2*beta) # Angles in radians!
    e2 = e_mag*np.sin(2*beta)
    Q11 = 1 + e_mag_sq + 2*e1
    Q22 = 1 + e_mag_sq - 2*e1
    Q12 = 2*e2
    return np.array(((Q11,Q12),(Q12,Q22)))*cn*hlr**2/(1-e_mag_sq)**2

def moments_size_and_shape(Q):
    trQ = np.trace(Q,axis1=-2,axis2=-1)
    detQ = np.linalg.det(Q)
    asymQx = Q[...,0,0] - Q[...,1,1]
    asymQy = 2*Q[...,0,1]
    asymQ = np.sqrt(asymQx**2 + asymQy**2)
    a = np.sqrt(0.5*(trQ + asymQ))
    b = np.sqrt(0.5*(trQ - asymQ))
    beta = 0.5*np.arctan2(asymQy,asymQx)
    e_denom = trQ + 2*np.sqrt(detQ)
    e1 = asymQx/e_denom
    e2 = asymQy/e_denom
    return a, b, beta, e1, e2

def _total_shape(a_bulge, b_bulge, theta_bulge, mag_bulge,
                 a_disk, b_disk, theta_disk, mag_disk, result='all'):

    Q_bulge = np.zeros((2, 2, len(mag_bulge)))
    Q_disk = np.zeros_like(Q_bulge)

    m = np.isfinite(mag_bulge)
    Q_bulge[:,:,m] = sersic_second_moments(4,
                                           np.sqrt(a_bulge[m]*b_bulge[m]),
                                           b_bulge[m]/a_bulge[m],
                                           np.deg2rad(theta_bulge[m]))
    m = np.isfinite(mag_disk)
    Q_disk[:,:,m] = sersic_second_moments(1,
                                          np.sqrt(a_disk[m]*b_disk[m]),
                                          a_disk[m]/b_disk[m],
                                          np.deg2rad(theta_disk[m]))

    f_bulge = _get_bulge_fraction(mag_bulge, mag_disk)
    Q_total = Q_bulge * f_bulge + Q_disk * (1.0 - f_bulge)
    a, b, beta, e1, e2 = np.array([moments_size_and_shape(Q_total[:,:,i]) for i in range(Q_total.shape[-1])]).T
    beta = np.remainder(np.rad2deg(beta), 180.0)
    if result == 'a':
        return a
    if result == 'b':
        return b
    if result == 'beta':
        return beta
    if result == 'e1':
        return e1
    if result == 'e2':
        return e2
    return a, b, beta, e1, e2

_get_total_a = partial(_total_shape, result='a')
_get_total_b = partial(_total_shape, result='b')
_get_total_beta = partial(_total_shape, result='beta')
_get_total_e1 = partial(_total_shape, result='e1')
_get_total_e2 = partial(_total_shape, result='e2')


class InstanceCatalog(BaseGenericCatalog):
    """
    Instance catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    _col_names = {
        'star': OrderedDict([('object', str),
                             ('id', int),
                             ('ra', float),
                             ('dec', float),
                             ('mag_norm', float),
                             ('sed_name', str),
                             ('redshift', float),
                             ('gamma_1', float),
                             ('gamma_2', float),
                             ('kappa', float),
                             ('delta_ra', float),
                             ('delta_dec', float),
                             ('source_type', str),
                             ('params', str),
                             ('dust_name', str),
                             ('A_v', float),
                             ('R_v', float),
                            ]),
        'gal': OrderedDict([('object', str),
                            ('id', int),
                            ('ra', float),
                            ('dec', float),
                            ('mag_norm', float),
                            ('sed_name', str),
                            ('redshift', float),
                            ('gamma_1', float),
                            ('gamma_2', float),
                            ('kappa', float),
                            ('delta_ra', float),
                            ('delta_dec', float),
                            ('source_type', str),
                            ('a', float),
                            ('b', float),
                            ('theta', float),
                            ('sersic_n', float),
                            ('dust_name_ref', str),
                            ('A_v_ref', float),
                            ('R_v_ref', float),
                            ('dust_name_lab', str),
                            ('A_v_lab', float),
                            ('R_v_lab', float),
                           ]),
    }

    def _subclass_init(self, **kwargs):
        self.header_file = kwargs['header_file']
        assert(os.path.isfile(self.header_file)), 'Header file {} does not exist'.format(self.header_file)

        self.header = self.parse_header(self.header_file)
        self.base_dir = os.path.dirname(self.header_file)

        self.cosmology = FlatLambdaCDM(H0=71, Om0=0.265, Ob0=0.0448)
        self.lightcone = True

        self._data = dict()
        self._object_files = dict()
        for filename in self.header['includeobj']:
            for obj_type in self._col_names:
                if filename.startswith(obj_type + '_'):
                    full_path = os.path.join(self.base_dir, filename)
                    if os.path.isfile(full_path):
                        self._object_files[obj_type] = full_path

        shape_quantities = ('gal_a_bulge',
                            'gal_b_bulge',
                            'gal_theta_bulge',
                            'gal_mag_norm_bulge',
                            'gal_a_disk',
                            'gal_b_disk',
                            'gal_theta_disk',
                            'gal_mag_norm_disk')

        self._quantity_modifiers = {
            'galaxy_id': 'gal_total_id',
            'ra_true': (_get_one, 'gal_ra_bulge', 'gal_ra_disk'),
            'dec_true': (_get_one, 'gal_dec_bulge', 'gal_dec_disk'),
            'mag_true_i_lsst': (_get_total_mag, 'gal_mag_norm_bulge', 'gal_mag_norm_disk'),
            'redshift_true': (_get_one, 'gal_redshift_bulge', 'gal_redshift_disk'),
            'bulge_to_total_ratio_i': (_get_bulge_fraction, 'gal_mag_norm_bulge', 'gal_mag_norm_disk'),
            'sersic_disk': 'gal_sersic_n_disk',
            'sersic_bulge': 'gal_sersic_n_bulge',
            'convergence': (_get_one, 'gal_kappa_bulge', 'gal_kappa_disk'),
            'shear_1': (_get_one, 'gal_gamma_1_bulge', 'gal_gamma_1_disk'),
            'shear_2': (_get_one, 'gal_gamma_2_bulge', 'gal_gamma_2_disk'),
            'size_true': (_get_total_a,) + shape_quantities,
            'size_minor_true': (_get_total_b,) + shape_quantities,
            'position_angle_true': (_get_total_beta,) + shape_quantities,
            'ellipticity_1_true': (_get_total_e1,) + shape_quantities,
            'ellipticity_2_true': (_get_total_e2,) + shape_quantities,
            'size_disk_true': 'gal_a_disk',
            'size_disk_minor_true': 'gal_b_disk',
            'size_bulge_true': 'gal_a_bulge',
            'size_bulge_minor_true': 'gal_b_bulge',
        }


    def _generate_native_quantity_list(self):
        native_quantities = []
        for obj_type in self._object_files:
            for col in self._col_names[obj_type]:
                if obj_type == 'gal':
                    native_quantities.append('{}_{}_bulge'.format(obj_type, col))
                    native_quantities.append('{}_{}_disk'.format(obj_type, col))
                else:
                    native_quantities.append('{}_{}'.format(obj_type, col))
            if obj_type == 'gal':
                native_quantities.append('gal_total_id')
        return native_quantities

    def _get_data(self, obj_type):
        if obj_type not in self._data:
            nrows = None
            if obj_type == 'gal': # the galaxy catalog has agn in it...
                this_open = gzip.open if self._object_files[obj_type].endswith('.gz') else open
                with this_open(self._object_files[obj_type], 'rb') as f:
                    for i, line in enumerate(f):
                        if b'agnSED/' in line:
                            nrows = i
                            break
            df = pd.read_table(self._object_files[obj_type],
                               delim_whitespace=True,
                               nrows=nrows,
                               names=list(self._col_names[obj_type]),
                               dtype=self._col_names[obj_type])
            if obj_type == 'gal':
                df['total_id'] = df['id'].values >> 10
                df['sub_type'] = df['id'].values & (2**10-1)
                df = pd.merge(df.query('sub_type == 97'),
                              df.query('sub_type == 107'),
                              how='outer',
                              on='total_id',
                              suffixes=('_bulge', '_disk'))
            self._data[obj_type] = df
        return self._data[obj_type]

    def _native_quantity_getter(self, native_quantity):
        obj_type, _, col_name = native_quantity.partition('_')
        return self._get_data(obj_type)[col_name].values

    def _iter_native_dataset(self, native_filters=None):
        assert not native_filters, '`native_filters` is not supported'
        yield self._native_quantity_getter

    @staticmethod
    def parse_header(header_file):
        header = dict()
        with open(header_file, 'r') as f:
            for line in f:
                key, _, value = line.partition(' ')
                value = value.strip()
                try:
                    value_float = float(value)
                except ValueError:
                    pass
                else:
                    if value_float != int(value_float) or '.' in value or 'e' in value.lower():
                        value = value_float
                    else:
                        value = int(value_float)
                if key in header:
                    try:
                        header[key].append(value)
                    except AttributeError:
                        header[key] = [header[key], value]
                else:
                    header[key] = value
        return header

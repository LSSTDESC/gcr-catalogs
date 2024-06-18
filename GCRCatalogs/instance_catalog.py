"""
instance catalog reader
"""
from __future__ import division, print_function
import os
import gc
import gzip
import warnings
from functools import partial
import numpy as np
import pandas as pd
from GCR import BaseGenericCatalog
from .cosmology import FlatLambdaCDM

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
    a, b, beta, e1, e2 = np.array([moments_size_and_shape(Q_total[:,:,i]) for i in range(Q_total.shape[-1])]).T  # pylint: disable=unpacking-non-sequence
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

    _base_col_names = [
        ('object', str),
        ('id', np.int64),
        ('ra', np.float64),
        ('dec', np.float64),
        ('mag_norm', np.float64),
        ('sed_name', str),
        ('redshift', np.float64),
        ('gamma_1', np.float64),
        ('gamma_2', np.float64),
        ('kappa', np.float64),
        ('delta_ra', np.float64),
        ('delta_dec', np.float64),
        ('source_type', str),
    ]

    _point_col_names = _base_col_names + [
        ('dust_rest_name', str),
        ('dust_lab_name', str),
        ('A_v_lab', np.float64),
        ('R_v_lab', np.float64),
    ]

    _sersic2d_col_names = _base_col_names + [
        ('a', np.float64),
        ('b', np.float64),
        ('theta', np.float64),
        ('sersic_n', np.float64),
        ('dust_rest_name', str),
        ('A_v_rest', np.float64),
        ('R_v_rest', np.float64),
        ('dust_lab_name', str),
        ('A_v_lab', np.float64),
        ('R_v_lab', np.float64),
    ]

    _knots_col_names = _base_col_names + [
        ('a', np.float64),
        ('b', np.float64),
        ('theta', np.float64),
        ('nknots', np.int64),
        ('dust_rest_name', str),
        ('A_v_rest', np.float64),
        ('R_v_rest', np.float64),
        ('dust_lab_name', str),
        ('A_v_lab', np.float64),
        ('R_v_lab', np.float64),
    ]

    _col_names = {
        'star': _point_col_names,
        'bright_stars': _point_col_names,
        'bulge_gal': _sersic2d_col_names,
        'disk_gal': _sersic2d_col_names,
        'agn_gal': _point_col_names,
        'knots': _knots_col_names,
        'MainSurveyHostedSNPositions': _point_col_names,
        'MainSurvey_hostlessSN': _point_col_names,
        'MainSurvey_hostlessSN_highz': _point_col_names,
        'uDDFHostedSNPositions': _point_col_names,
        'uDDF_hostlessSN': _point_col_names,
    }

    _legacy_gal_types = ('agn_gal', 'bulge_gal', 'disk_gal')

    def _subclass_init(self, **kwargs):
        self.header_file = kwargs['header_file']

        if not os.path.isfile(self.header_file):
            raise ValueError('Header file {} does not exist'.format(self.header_file))

        self.header = self.parse_header(self.header_file)
        self.base_dir = os.path.dirname(self.header_file)

        self.cosmology = FlatLambdaCDM(H0=71, Om0=0.265, Ob0=0.0448)
        self.lightcone = True

        self.legacy_gal_catalog = False
        self._data = dict()
        self._object_files = dict()
        for filename in self.header['includeobj']:
            obj_type = filename.partition('_cat_')[0]

            if obj_type == 'gal':
                self.legacy_gal_catalog = True
            elif obj_type not in self._col_names:
                warnings.warn('Unknown object type {}! Skipped!'.format(obj_type))
                continue

            full_path = os.path.join(self.base_dir, filename)
            if not os.path.isfile(full_path):
                warnings.warn('Cannot find file {}! Skipped!'.format(full_path))
                continue

            self._object_files[obj_type] = full_path

        if self.legacy_gal_catalog:
            if any(t in self._object_files for t in self._legacy_gal_types):
                raise ValueError('cannot determine whether this is a legacy instance catalog!')
            for t in self._legacy_gal_types:
                self._object_files[t] = self._object_files['gal']
            del self._object_files['gal']

        try:
            self.visit = int(self.header.get('obshistid'))
        except (TypeError, ValueError):
            warnings.warn('Cannot parse visit id {}'.format(self.header.get('obshistid')))
            self.visit = None

        shape_quantities = ('gal/a_bulge',
                            'gal/b_bulge',
                            'gal/theta_bulge',
                            'gal/mag_norm_bulge',
                            'gal/a_disk',
                            'gal/b_disk',
                            'gal/theta_disk',
                            'gal/mag_norm_disk')

        self._quantity_modifiers = {
            'galaxy_id': 'gal/total_id',
            'ra_true': (_get_one, 'gal/ra_bulge', 'gal/ra_disk'),
            'dec_true': (_get_one, 'gal/dec_bulge', 'gal/dec_disk'),
            'mag_true_i_lsst': (_get_total_mag, 'gal/mag_norm_bulge', 'gal/mag_norm_disk'),
            'redshift_true': (_get_one, 'gal/redshift_bulge', 'gal/redshift_disk'),
            'bulge_to_total_ratio_i': (_get_bulge_fraction, 'gal/mag_norm_bulge', 'gal/mag_norm_disk'),
            'sersic_disk': 'gal/sersic_n_disk',
            'sersic_bulge': 'gal/sersic_n_bulge',
            'convergence': (_get_one, 'gal/kappa_bulge', 'gal/kappa_disk'),
            'shear_1': (_get_one, 'gal/gamma_1_bulge', 'gal/gamma_1_disk'),
            'shear_2': (_get_one, 'gal/gamma_2_bulge', 'gal/gamma_2_disk'),
            'size_true': (_get_total_a,) + shape_quantities,
            'size_minor_true': (_get_total_b,) + shape_quantities,
            'position_angle_true': (_get_total_beta,) + shape_quantities,
            'ellipticity_1_true': (_get_total_e1,) + shape_quantities,
            'ellipticity_2_true': (_get_total_e2,) + shape_quantities,
            'size_disk_true': 'gal/a_disk',
            'size_disk_minor_true': 'gal/b_disk',
            'size_bulge_true': 'gal/a_bulge',
            'size_bulge_minor_true': 'gal/b_bulge',
        }

    def _generate_native_quantity_list(self):
        native_quantities = ['{}/{}'.format(obj_type, col) for obj_type in self._object_files for col, _ in self._col_names[obj_type]]
        for col, _ in self._col_names['bulge_gal']:
            native_quantities.append('gal/{}_bulge'.format(col))
            native_quantities.append('gal/{}_disk'.format(col))
        native_quantities.append('gal/total_id')
        return native_quantities

    def _pd_read_table(self, obj_type, **kwargs):
        return pd.read_csv(
            self._object_files[obj_type],
            delim_whitespace=True,
            names=[c[0] for c in self._col_names[obj_type]],
            dtype=dict(self._col_names[obj_type]),
            **kwargs
        )

    def _load_legacy_gal_catalog(self, obj_type):
        if '_legacy_gal_line_index' not in self._data:
            path = self._object_files[obj_type]
            this_open = gzip.open if path.endswith('.gz') else open
            with this_open(path, 'rb') as f:
                for index, line in enumerate(f):
                    if b' agnSED/' in line:
                        self._data['_legacy_gal_line_index'] = index
                        break

        if obj_type == 'agn_gal':
            return self._pd_read_table(
                obj_type,
                skiprows=self._data['_legacy_gal_line_index'],
            )

        if '_legacy_gal_table' not in self._data:
            df = self._pd_read_table(
                obj_type,
                nrows=self._data['_legacy_gal_line_index'],
            )
            df['sub_type'] = df['id'].values & (2**10-1)
            self._data['_legacy_gal_table'] = df
            del df

        if obj_type == 'bulge_gal':
            return self._data['_legacy_gal_table'].query('sub_type == 97')

        if obj_type == 'disk_gal':
            return self._data['_legacy_gal_table'].query('sub_type == 107')

    def _load_single_catalog(self, obj_type):
        if obj_type == 'gal':
            df1 = self.load_single_catalog('bulge_gal')
            df2 = self.load_single_catalog('disk_gal')
            df1['total_id'] = df1['id'].values >> 10
            df2['total_id'] = df2['id'].values >> 10
            return pd.merge(df1, df2, how='outer',
                            on='total_id',
                            suffixes=('_bulge', '_disk'))

        elif self.legacy_gal_catalog and obj_type in self._legacy_gal_types:
            return self._load_legacy_gal_catalog(obj_type)

        return self._pd_read_table(obj_type)

    def load_single_catalog(self, obj_type):
        if obj_type not in self._data:
            try:
                self._data[obj_type] = self._load_single_catalog(obj_type)
            except MemoryError:
                if not self._data:
                    raise
                self._data.clear()
                gc.collect()
                return self.load_single_catalog(obj_type)
        return self._data[obj_type]

    def _native_quantity_getter(self, native_quantity):
        obj_type, _, col_name = native_quantity.partition('/')
        return self.load_single_catalog(obj_type)[col_name].values

    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise ValueError('`native_filters` is not supported')
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

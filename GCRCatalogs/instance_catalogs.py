from __future__ import division,print_function
import os
import re
import functools
import numpy as np
import pandas as pd
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog
pd.options.mode.chained_assignment = None 
__all__ = ['InstanceCatalog']

def sersic_second_moments(n,hlr,q,beta):
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
    sigma_m = np.power(detQ,0.25)
    sigma_p = np.sqrt(0.5*trQ)
    asymQx = Q[...,0,0] - Q[...,1,1]
    asymQy = 2*Q[...,0,1]
    asymQ = np.sqrt(asymQx**2 + asymQy**2)
    a = np.sqrt(0.5*(trQ + asymQ))
    b = np.sqrt(0.5*(trQ - asymQ))
    beta = 0.5*np.arctan2(asymQy,asymQx)
    e_denom = trQ + 2*np.sqrt(detQ)
    e1 = asymQx/e_denom
    e2 = asymQy/e_denom
    return a,b,beta,e1,e2

def _total_flux(mag_bulge, mag_disk):
    f_bulge = np.zeros_like(mag_bulge)
    f_disk = np.zeros_like(mag_disk)
    m = np.isnan(mag_bulge)
    f_bulge[m]=0.
    f_bulge[~m] = 10**(-0.4*mag_bulge[~m])*3631*1e6 #uJy
    m = np.isnan(mag_disk)
    f_disk[m]=0.
    f_disk[~m] = 10**(-0.4*mag_disk[~m])*3631*1e6 #uJy
    total_flux = f_bulge+f_disk
    total_mag = -2.5*np.log10(total_flux/(3631*1e6))
    return f_bulge/(f_bulge+f_disk), total_flux, total_mag

def _get_one(x,y):
    m =  np.isnan(x)
    x[m]=y[m]
    return x

def _get_total_mag(mag_bulge, mag_disk):
    return _total_flux(mag_bulge,mag_disk)[2]

def _get_bulge_fraction(mag_bulge, mag_disk):
    return _total_flux(mag_bulge,mag_disk)[0]

def _total_shape(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk):
    f_bulge = _get_bulge_fraction(mag_bulge,mag_disk)
    f_disk = 1.-f_bulge
    xlen = len(mag_bulge)
    hlr_bulge = np.zeros(xlen)
    hlr_disk = np.zeros(xlen)
    q_bulge = np.zeros(xlen)
    q_disk = np.zeros(xlen)
    try:
        Q_bulge = np.zeros((2,2,xlen))
        Q_disk = np.zeros((2,2,xlen))
    except:
        Q_bulge = np.zeros((2,2))
        Q_disk = np.zeros((2,2))
    m = f_bulge>0
    hlr_bulge[m] = np.sqrt(galaxy_a_bulge[m]*galaxy_b_bulge[m])
    q_bulge[m] = galaxy_b_bulge[m]/galaxy_a_bulge[m]
    Q_bulge[:,:,m] = sersic_second_moments(4,hlr_bulge[m],q_bulge[m],galaxy_theta_bulge[m]*np.pi/180)
    m = f_disk>0
    hlr_disk[m] = np.sqrt(galaxy_a_disk[m]*galaxy_b_disk[m])
    q_disk[m] = galaxy_b_disk[m]/galaxy_a_disk[m]
    Q_disk[:,:,m] = sersic_second_moments(1,hlr_disk[m],q_disk[m],galaxy_theta_disk[m]*np.pi/180)
    Q_total = f_bulge*Q_bulge + f_disk*Q_disk
    a = np.zeros(xlen); b = np.zeros(xlen); beta = np.zeros(xlen); e1 = np.zeros(xlen); e2 = np.zeros(xlen)
    for i in range(xlen):
        a[i],b[i],beta[i],e1[i],e2[i] = moments_size_and_shape(Q_total[:,:,i])
    return a,b,beta*180/np.pi,e1,e2
    
def _get_total_a(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk):
    return _total_shape(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk)[0]

def _get_total_b(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk):
    return _total_shape(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk)[1]

def _get_total_theta(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk):
    return _total_shape(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk)[2]

def _get_total_e1(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk):
    return _total_shape(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk)[3]

def _get_total_e2(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk):
    return _total_shape(galaxy_a_bulge,galaxy_b_bulge,galaxy_theta_bulge,
                 mag_bulge,mag_disk,galaxy_a_disk,galaxy_b_disk,galaxy_theta_disk)[4]
class BaseInstanceCatalog(BaseGenericCatalog):
    """
    Instance catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self,filename,**kwargs):
        assert(os.path.isfile(filename)), 'Catalog {} does not exist'.format(filename)
        self._file = filename
        self._quantity_modifiers = {
            'pointing_ra': 'rightascension',
            'pointing_dec': 'declination',
            'mjd': 'mjd',
            'pointing_alt': 'altitude',
            'pointing_az': 'azimuth',
            'filter': 'filter',
            'rotskypos': 'rotskypos',
            'camconfig': 'camconfig',
            'dist2moon': 'dist2moon',
            'moon_alt': 'moonalt',
            'moon_dec': 'moondec',
            'moon_phase': 'moonphase',
            'moon_ra': 'moonra',
            'nsnap': 'nsnap',
            'obshistid': 'obshistid',
            'rottelpos': 'rottelpos',
            'seed': 'seed',
            'seeing': 'seeing',
            'sun_alt': 'sunalt',
            'visit_time': 'vistime',
            'min_source': 'minsource',
            'includeobj': 'includeobj'
        } 
    def _generate_native_quantity_list(self):
        """
        Reads input Instance catalog
        """
        fh = pd.read_table(self._file, index_col=0, header=None, sep=' ').T
        return np.unique(fh.keys())
    
    def _iter_native_dataset(self,native_filters=None):
        """
        """
        fh = pd.read_table(self._file, index_col=0, header=None, sep=' ').T
        def native_quantity_getter(native_quantity):
            return fh[native_quantity].values
        yield native_quantity_getter
    def has_stellar_catalog(self):
        return any('star' in x for x in list(self.get_quantities('includeobj').values())[0][0])
    def get_stellar_catalog_name(self):
        assert(self.has_stellar_catalog()), 'Catalog {} does not contain stellar source catalog'
        mask = ['star' in x for x in list(self.get_quantities('includeobj').values())[0][0]]
        return list(self.get_quantities('includeobj').values())[0][0][mask][0] 
    def has_galaxy_catalog(self):
        return any('gal' in x for x in list(self.get_quantities('includeobj').values())[0][0])
    def get_galaxy_catalog_name(self):
        assert(self.has_stellar_catalog()), 'Catalog {} does not contain galaxy source catalog'
        mask = ['gal' in x for x in list(self.get_quantities('includeobj').values())[0][0]]
        return list(self.get_quantities('includeobj').values())[0][0][mask][0] 
    
class InstanceCatalogStar(BaseInstanceCatalog):
    """
    This object takes an instance catalog containing stellar sources
    """
    def _subclass_init(self,filename,**kwargs):
        assert(os.path.isfile(filename)), 'Catalog {} does not exist'.format(filename)
        self.base_ic = BaseInstanceCatalog(filename=filename)
        self._file = os.path.join(os.path.dirname(filename),self.base_ic.get_stellar_catalog_name())
        self._col_names = ['star_object',
                 'star_id',
                 'star_ra',
                 'star_dec',
                 'star_mag_norm',
                 'star_sed_name',
                 'star_redshift',
                 'star_gamma_1',
                 'star_gamma_2',
                 'star_kappa',
                 'star_delta_ra',
                 'star_delta_dec',
                 'star_source_type',
                 'star_params',
                 'star_dust_name',
                 'star_A_v',
                 'star_R_v',
                ]
    def _generate_native_quantity_list(self):
        fh = pd.read_table(self._file, header=None, sep=' ',names=self._col_names)
        return np.unique(fh.keys())
    
    def _iter_native_dataset(self,native_filters=None):
        fh = pd.read_table(self._file, header=None, sep=' ',names=self._col_names)
        def native_quantity_getter(native_quantity):
            return fh[native_quantity].values
        yield native_quantity_getter
        
        
class InstanceCatalogGalaxy(BaseInstanceCatalog):
    """
    This object takes an instance catalog containing galaxy sources
    """
    def _subclass_init(self,filename,**kwargs):
        assert(os.path.isfile(filename)), 'Catalog {} does not exist'.format(filename)
        self.base_ic = BaseInstanceCatalog(filename=filename)
        self._file = os.path.join(os.path.dirname(filename),self.base_ic.get_galaxy_catalog_name())
        self._col_names = ['galaxy_object',
                 'galaxy_id',
                 'ra',
                 'dec',
                 'galaxy_mag_norm',
                 'galaxy_sed_name',
                 'galaxy_redshift',
                 'galaxy_gamma_1',
                 'galaxy_gamma_2',
                 'galaxy_kappa',
                 'delta_ra',
                 'delta_dec',
                 'galaxy_source_type',
                 'galaxy_a',
                 'galaxy_b',
                 'galaxy_theta',
                 'galaxy_sersic_n',
                 'galaxy_dust_name_ref',
                 'galaxy_A_v_ref',
                 'galaxy_R_v_ref',
                 'galaxy_dust_name_lab',
                 'galaxy_A_v_lab',
                 'galaxy_R_v_lab'
                ]
        self._str_columns = ['galaxy_object','galaxy_sed_name','galaxy_source_type',
                            'galaxy_dust_name_ref','galaxy_dust_name_lab']
        self._quantity_modifiers = {
                 'galaxy_id': 'id',
                 'galaxy_ra': (_get_one, 'ra_bulge','ra_disk'),
                 'galaxy_dec': (_get_one, 'dec_bulge','dec_disk'),
                 'galaxy_mag_norm': (_get_total_mag, 
                                     'galaxy_mag_norm_bulge',
                                     'galaxy_mag_norm_disk'),
                 'galaxy_redshift': (_get_one,
                                     'galaxy_redshift_bulge',
                                     'galaxy_redshift_disk'),
                 'galaxy_bulge_fraction': (_get_bulge_fraction, 
                                           'galaxy_mag_norm_bulge',
                                           'galaxy_mag_norm_disk'),
                 'galaxy_a': (_get_total_a, 
                              'galaxy_a_bulge',
                              'galaxy_b_bulge',
                              'galaxy_theta_bulge',
                              'galaxy_mag_norm_bulge',
                              'galaxy_mag_norm_disk',
                              'galaxy_a_disk',
                              'galaxy_b_disk',
                              'galaxy_theta_disk'),
                 'galaxy_b': (_get_total_b, 
                              'galaxy_a_bulge',
                              'galaxy_b_bulge',
                              'galaxy_theta_bulge',
                              'galaxy_mag_norm_bulge',
                              'galaxy_mag_norm_disk',
                              'galaxy_a_disk',
                              'galaxy_b_disk',
                              'galaxy_theta_disk'),
                 'galaxy_theta': (_get_total_theta, 
                                  'galaxy_a_bulge',
                                  'galaxy_b_bulge',
                                  'galaxy_theta_bulge',
                                  'galaxy_mag_norm_bulge',
                                  'galaxy_mag_norm_disk',
                                  'galaxy_a_disk',
                                  'galaxy_b_disk',
                                  'galaxy_theta_disk'),
                 'galaxy_ellipticity_1': (_get_total_e1,
                                          'galaxy_a_bulge',
                                          'galaxy_b_bulge',
                                          'galaxy_theta_bulge',
                                          'galaxy_mag_norm_bulge',
                                          'galaxy_mag_norm_disk',
                                          'galaxy_a_disk',
                                          'galaxy_b_disk',
                                          'galaxy_theta_disk'),
                 'galaxy_ellipticity_2': (_get_total_e2, 
                                          'galaxy_a_bulge',
                                          'galaxy_b_bulge',
                                          'galaxy_theta_bulge',
                                          'galaxy_mag_norm_bulge',
                                          'galaxy_mag_norm_disk',
                                          'galaxy_a_disk',
                                          'galaxy_b_disk',
                                          'galaxy_theta_disk'),
                 
        }
    def _generate_native_quantity_list(self):
        fh = pd.read_table(self._file,header=None,sep=' ',names=self._col_names)
        mask = 0b1111111111
        gal_id = fh['galaxy_id'].values >> 10 
        sub_type = fh['galaxy_id'].values & mask
        df1 = fh[sub_type==97]
        df1['id'] = pd.Series(gal_id[sub_type==97],index=df1.index)
        df2 = fh[sub_type==107]
        df2['id'] = pd.Series(gal_id[sub_type==107],index=df2.index)
        df = pd.merge(df1,df2,how='outer',on='id',suffixes=('_disk','_bulge'))
        return np.unique(df.keys())
    
    def _iter_native_dataset(self,native_filters=None):
        fh = pd.read_table(self._file,header=None,sep=' ',names=self._col_names)
        mask = 0b1111111111
        gal_id = fh['galaxy_id'].values >> 10 
        sub_type = fh['galaxy_id'].values & mask
        df1 = fh[sub_type==97]
        df1['id'] = pd.Series(gal_id[sub_type==97],index=df1.index)
        df2 = fh[sub_type==107]
        df2['id'] = pd.Series(gal_id[sub_type==107],index=df2.index)
        df = pd.merge(df1,df2,how='outer',on='id',suffixes=('_disk','_bulge'))
        def native_quantity_getter(native_quantity):
            if native_quantity not in self._str_columns:
                return df[native_quantity].values.astype(float)
            else:
                return df[native_quantity].values
        yield native_quantity_getter

class InstanceCatalog(BaseInstanceCatalog):
    def _subclass_init(self,filename,**kwargs):
        assert(os.path.isfile(filename)), 'Catalog {} does not exist'.format(filename)
        self._file = filename
        self.base_ic = BaseInstanceCatalog(filename=filename)
        self.has_stars = self.base_ic.has_stellar_catalog()
        self.has_galaxies = self.base_ic.has_galaxy_catalog()
        self._quantity_modifiers={}
        self._quantity_modifiers.update(self.base_ic._quantity_modifiers)
        if self.has_galaxies:
            self.galaxy_ic = InstanceCatalogGalaxy(filename=filename)
            self._galaxy_file = self.galaxy_ic._file
            self._quantity_modifiers.update(self.galaxy_ic._quantity_modifiers)
        if self.has_stars:
            self.star_ic = InstanceCatalogStar(filename=filename)
            self._star_file = self.star_ic._file
    def _generate_native_quantity_list(self):
        return np.concatenate([self.base_ic._generate_native_quantity_list(),  
                  self.galaxy_ic._generate_native_quantity_list(), 
                  self.star_ic._generate_native_quantity_list()
                 ]).ravel()
    def _iter_native_dataset(self,native_filters=None):
        def native_quantity_getter(native_quantity):
            if self.base_ic.has_quantity(native_quantity):
                return list(self.base_ic.get_quantities(native_quantity).values())[0]
            elif self.galaxy_ic.has_quantity(native_quantity):
                return list(self.galaxy_ic.get_quantities(native_quantity).values())[0]
            elif self.star_ic.has_quantity(native_quantity):
                return list(self.star_ic.get_quantities(native_quantity).values())[0]
        yield native_quantity_getter

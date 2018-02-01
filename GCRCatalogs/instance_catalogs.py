from __future__ import division,print_function
import os
import re
import functools
import numpy as np
import pandas as pd
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog

__all__ = ['InstanceCatalog']

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
            'visit_time': 'visitime',
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
        return any('star' in x for x in self.get_quantities('includeobj').values()[0][0])
    def get_stellar_catalog_name(self):
        assert(self.has_stellar_catalog()), 'Catalog {} does not contain stellar source catalog'
        mask = ['star' in x for x in self.get_quantities('includeobj').values()[0][0]]
        return self.get_quantities('includeobj').values()[0][0][mask][0] 
    def has_galaxy_catalog(self):
        return any('gal' in x for x in self.get_quantities('includeobj').values()[0][0])
    def get_galaxy_catalog_name(self):
        assert(self.has_stellar_catalog()), 'Catalog {} does not contain galaxy source catalog'
        mask = ['gal' in x for x in self.get_quantities('includeobj').values()[0][0]]
        return self.get_quantities('includeobj').values()[0][0][mask][0] 
    
    
class InstanceCatalogStar(BaseInstanceCatalog):
    """
    This object takes an instance catalog containing stellar sources
    """
    def _subclass_init(self,filename,**kwargs):
        assert(os.path.isfile(filename)), 'Catalog {} does not exist'.format(filename)
        self.base_ic = BaseInstanceCatalog(filename=filename)
        self._file = os.path.join(os.path.dirname(filename),self.base_ic.get_stellar_catalog_name())
        self._quantity_modifiers = {
            
        } 
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
        mask = 0b1111111111 # Lower 10 bits encode type
        self._quantity_modifiers = {
        'id' : (lambda x: x >> 10, 'galaxy_id'), 
        'sub_type': (lambda x: x & mask, 'galaxy_id')    
        } 
        self._col_names = ['galaxy_object',
                 'galaxy_id',
                 'galaxy_ra',
                 'galaxy_dec',
                 'galaxy_mag_norm',
                 'galaxy_sed_name',
                 'galaxy_redshift',
                 'galaxy_gamma_1',
                 'galaxy_gamma_2',
                 'galaxy_kappa',
                 'galaxy_delta_ra',
                 'galaxy_delta_dec',
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
    def _generate_native_quantity_list(self):
        fh = pd.read_table(self._file, header=None, sep=' ',names=self._col_names)
        return np.unique(fh.keys())
    
    def _iter_native_dataset(self,native_filters=None):
        fh = pd.read_table(self._file, header=None, sep=' ',names=self._col_names)
        def native_quantity_getter(native_quantity):
            return fh[native_quantity].values
        yield native_quantity_getter

class InstanceCatalog(BaseInstanceCatalog):
    def _subclass_init(self,filename,**kwargs):
        assert(os.path.isfile(filename)), 'Catalog {} does not exist'.format(filename)
        self._file = filename
        self.base_ic = BaseInstanceCatalog(filename=filename)
        self.has_stars = self.base_ic.has_stellar_catalog()
        self.has_galaxies = self.base_ic.has_galaxy_catalog()
        if self.has_galaxies:
            self.galaxy_ic = InstanceCatalogGalaxy(filename=filename)
            self._galaxy_file = self.galaxy_ic._file
        if self.has_stars:
            self.star_ic = InstanceCatalogStar(filename=filename)
            self._star_file = self.star_ic._file
        mask = 0b1111111111 # Lower 10 bits encode type
        self._quantity_modifiers = {
        'id' : (lambda x: x >> 10, 'galaxy_id'), 
        'sub_type': (lambda x: x & mask, 'galaxy_id')    
        } 
    def _generate_native_quantity_list(self):
        return np.concatenate([self.base_ic._generate_native_quantity_list(),  
                  self.galaxy_ic._generate_native_quantity_list(), 
                  self.star_ic._generate_native_quantity_list()
                 ]).ravel()
    def _iter_native_dataset(self,native_filters=None):
        def native_quantity_getter(native_quantity):
            if self.base_ic.has_quantity(native_quantity):
                return self.base_ic.get_quantities(native_quantity).values()[0]
            elif self.galaxy_ic.has_quantity(native_quantity):
                return self.galaxy_ic.get_quantities(native_quantity).values()[0]
            elif self.star_ic.has_quantity(native_quantity):
                return self.star_ic.get_quantities(native_quantity).values()[0]
        yield native_quantity_getter



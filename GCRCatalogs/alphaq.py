"""
Alpha Q galaxy catalog class.
"""
from __future__ import division
import os
import numpy as np
import h5py
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog
from .register import register_reader

__all__ = ['AlphaQGalaxyCatalog', 'AlphaQClusterCatalog']

class AlphaQGalaxyCatalog(BaseGenericCatalog):
    """
    Alpha Q galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, filename, lightcone=True, **kwargs):

        assert os.path.isfile(filename), 'Catalog file {} does not exist'.format(filename)
        self._file = filename
        majorVersion = 0
        minorVersion = 0
        with h5py.File(self._file, 'r') as fh:
            self.cosmology = FlatLambdaCDM(
                H0=fh['metaData/simulationParameters/H_0'].value,
                Om0=fh['metaData/simulationParameters/Omega_matter'].value,
                Ob0=fh['metaData/simulationParameters/Omega_b'].value
            )
            if "metaData/majorVersion" in fh:
                majorVersion = hf['metaData/majorVersion'].value
                minorVersion = hf['metaData/minorVersion'].value


        self.lightcone = lightcone
        
        self._quantity_modifiers = {
            'galaxy_id' :    'galaxyID',
            'ra':            (lambda x: x/3600.0, 'ra'),
            'ra_true':       (lambda x: x/3600.0, 'ra_true'),
            'dec':           (lambda x: x/3600.0, 'dec'),
            'dec_true':      (lambda x: x/3600.0, 'dec_true'),
            'redshift':      'redshift',
            'redshift_true': 'redshiftHubble',
            'disk_sersic_index':'morphology/diskSersicIndex',
            'bulge_sersic_index':'morphology/spheroidSersicIndex',
            'shear_1':       'shear1',
            'shear_2':       'shear2',
            'convergence':   'convergence',
            'magnification': 'magnification',
            'halo_id':       'hostIndex',
            'halo_mass':     'hostHaloMass',
            'is_central':    (lambda x : x.astype(np.bool), 'isCentral'),
            'stellar_mass':  'totalMassStellar',
            'size_disk_true':'morphology/diskHalfLightRadius',
            'size_bulge_true':'morphology/spheroidHalfLightRadius',
            'position_x':    'x',
            'position_y':    'y',
            'position_z':    'z',
            'velocity_x':    'vx',
            'velocity_y':    'vy',
            'velocity_z':    'vz'
        }
        if(majorVersion >= 2 and minorVersion >= 1):
            quantity_mod_v2_01 = {
                #now stored as degrees
                'ra':  'ra',
                'dec': 'dec',
                'ra_true': 'ra_true',
                'dec_true': 'dec_true',
                'ellipticity_1_true': 'ellipticity_1',
                'ellipticity_2_true': 'ellipticity_2'
            }
            self._quantity_modifiers.update(quanity_mod_v2_0)

        for band in 'ugriz':
            self._quantity_modifiers['mag_{}_lsst'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed'.format(band)
            self._quantity_modifiers['mag_{}_sdss'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band)
            self._quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest'.format(band)
            self._quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest'.format(band)

        self._quantity_modifiers['mag_Y_lsst'] = 'LSST_filters/magnitude:LSST_y:observed'
        self._quantity_modifiers['Mag_true_Y_lsst_z0'] = 'LSST_filters/magnitude:LSST_y:rest'

        with h5py.File(self._file, 'r') as fh:
            self.cosmology = FlatLambdaCDM(
                H0=fh['metaData/simulationParameters/H_0'].value,
                Om0=fh['metaData/simulationParameters/Omega_matter'].value,
                Ob0=fh['metaData/simulationParameters/Omega_b'].value
            )
    
    def _generate_native_quantity_list(self):
        with h5py.File(self._file, 'r') as fh:
            hgroup = fh['galaxyProperties']
            hobjects = []
            #get all the names of objects in this tree
            hgroup.visit(hobjects.append)
            #filter out the group objects and keep the dataste objects
            hdatasets = [hobject for hobject in hobjects if type(hgroup[hobject])==h5py.Dataset]
            native_quantities = set(hdatasets)
        return native_quantities


    def _iter_native_dataset(self, native_filters=None):
        assert not native_filters, '*native_filters* is not supported'
        with h5py.File(self._file, 'r') as fh:
            def native_quantity_getter(native_quantity):
                return fh['galaxyProperties/{}'.format(native_quantity)].value
            yield native_quantity_getter

    def _get_native_quantity_info_dict(self,quantity,default=None):
        with h5py.File(self._file,'r') as fh:
            if 'galaxyProperties/'+quantity not in fh:
                return default
            else:
                info_dict = dict()
                for key in fh['galaxyProperties/'+quantity].attrs.keys():
                    info_dict[key] = fh['galaxyProperties/'+quantity].attrs[key]
                return info_dict
    
    def _get_quantity_info_dict(self, quantity, default=None):
        return default
        #TODO needs some fixing
        print "in get quantity"
        native_name = None
        if quantity in self._quantity_modifiers:
            print "in quant modifers"
            q_mod = self._quantity_modifiers[quantity]
            if isinstance(q_mod,(tuple,list)):
                print "it's a list object, len:",len(length)

                if(len(length) > 2):
                    return default #This value is composed of a function on 
                    #native quantities. So we have no idea what the units are
                else:
                    #Note: This is just a renamed column.
                    return self._get_native_quantity_info_dict(q_mod[1],default)
            else:
                print "it's a string: ",q_mod
                return self._get_native_quantity_info_dict(q_mod,default)
        elif quantity in self._native_quantities:
            print "in get native quant"
            return self._get_native_quantity_info_dict(quantity,default)
        
                
        

# Registers the reader
register_reader(AlphaQGalaxyCatalog)


#=====================================================================================================


class AlphaQClusterCatalog(AlphaQGalaxyCatalog):
    """
    The galaxy cluster catalog. Inherits AlphaQGalaxyCatalog, overloading select methods.

    The AlphaQ cluster catalog is structured in the following way: under the root hdf group, there
    is a group per each halo with SO mass above 1e14 M_sun/h. Each of these groups contains the same
    datasets as the original AlphaQ galaxy catalog, but with only as many rows as member galaxies for
    the halo in question. Each group has attributes which contain halo-wide quantities, such as mass,
    position, etc.

    This class offers filtering on any halo quantity (group attribute), as seen in all three of the
    methods of this class (all the group attributes are iterated over in contexts concerning the
    pre-filtering). The valid filtering quantities are:
    {'host_halo_mass', 'sod_halo_cdelta', 'sod_halo_cdelta_error', 'sod_halo_c_acc_mass',
     'fof_halo_tag', 'halo_index', 'halo_step', 'halo_ra', 'halo_dec', 'halo_z',
     'halo_z_err', 'sod_halo_radius', 'sod_halo_mass', 'sod_halo_ke', 'sod_halo_vel_disp'}
    """


    def _subclass_init(self, filename, **kwargs):
        super(AlphaQClusterCatalog, self)._subclass_init(filename, **kwargs)
        with h5py.File(self._file, 'r') as fh:
            self._native_filter_quantities = set(fh[next(fh.keys())].attrs)


    def _iter_native_dataset(self, native_filters=None):
        with h5py.File(self._file, 'r') as fh:
            for key in fh:
                halo = fh[key]

                if native_filters and not all(f[0](*(halo.attrs[k] for k in f[1:])) for f in native_filters):
                    continue

                def native_quantity_getter(native_quantity):
                    raise NotImplementedError

                yield native_quantity_getter


# Registers the reader
register_reader(AlphaQClusterCatalog)

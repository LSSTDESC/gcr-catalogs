"""
AGN catalog class.
"""
from __future__ import division, print_function
import os
import h5py
import numpy as np
from GCR import BaseGenericCatalog

__all__ = ['AGNCatalog']

def _calc_flux(mag):
    return np.power(10, -0.4*mag)

def _calc_mag_sum(mag1, mag2):
    total_flux =  _calc_flux(mag1) +  _calc_flux(mag2)
    return -2.5*np.log10(total_flux)

class AGNCatalog(BaseGenericCatalog):
    """
    AGN catalog class.  Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, base_dir, filename, **kwargs): #pylint: disable=W0221

        if not os.path.isdir(base_dir):
            raise RuntimeError("Catalog directory %s does not exist." % (base_dir))

        self._path = os.path.join(base_dir, filename)
        self._handle = h5py.File(self._path, 'r')
        self._quantity_modifiers = self._generate_quantity_modifiers()
        self.lightcone = kwargs.get('lightcone', True)
        self.sky_area = kwargs.get('sky_area', None)

    def __del__(self):
        self._handle.close()

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
            'Av':                                           'Av',
            'blackHoleAccretionRate':                       'blackHoleAccretionRate',
            'blackHoleEddingtonRatio':                      'blackHoleEddingtonRatio',
            'blackHoleMass':                                'blackHoleMass',
            'dec':                                          'dec',
            'galaxy_id':                                    'galaxy_id',
            'halo_mass':                                    'halo_mass',
            'is_central':                                   'is_central',
            'Mag_true_i_agnonly_lsst_z0':                   'M_i(extincted)',
            'Mag_true_i_agnonly_no_agn_extinction_lsst_z0': 'M_i',
            'ra':                                           'ra',
            'redshift':                                     'redshift',
            'stellar_mass':                                 'stellar_mass',
            'duty_cycle_on':                                'duty_cycle_on',
        }

        # magnitudes
        for band in ['u', 'g', 'r', 'i', 'z', 'y']:
            quantity_modifiers['mag_{}_noagn_lsst'.format(band)] = 'mag_{}_lsst(galaxy)'.format(band) # galaxy with no AGN
            quantity_modifiers['mag_{}_agnonly_lsst'.format(band)] = 'mag_{}_lsst(agn)'.format(band)
            quantity_modifiers['mag_{}_agnonly_extincted_lsst'.format(band)] = 'mag_{}_lsst(agn_extincted)'.format(band)
            quantity_modifiers['mag_{}_lsst'.format(band)] = (_calc_mag_sum,
                                                              'mag_{}_lsst(galaxy)'.format(band),
                                                              'mag_{}_lsst(agn)'.format(band),
                                                             )
            quantity_modifiers['mag_{}_extincted_agn_lsst'.format(band)] = (_calc_mag_sum,
                                                                            'mag_{}_lsst(galaxy)'.format(band),
                                                                            'mag_{}_lsst(agn_extincted)'.format(band),
                                                                           )
        # Magnitudes
        for band in ['g', 'r', 'i']: # only gri galaxy rest-frame magnitudes are provided in the AGN catalog
            quantity_modifiers['Mag_true_{}_noagn_lsst_z0'.format(band)] = 'Mag_true_{}_lsst_z0'.format(band)

        for band in ['i']: # only the i-band AGN rest-frame magnitude is provided in the AGN catalog
            quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = (_calc_mag_sum,
                                                                      'Mag_true_{}_lsst_z0'.format(band),
                                                                      'M_{}'.format(band),
                                                                     )
            quantity_modifiers['Mag_true_{}_extincted_agn_lsst_z0'.format(band)] = (_calc_mag_sum,
                                                                                    'Mag_true_{}_lsst_z0'.format(band),
                                                                                    'M_{}(extincted)'.format(band),
                                                                                   )

        return quantity_modifiers


    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise RuntimeError("*native_filters* not supported")
        yield lambda x: self._handle[x][()]

    def _generate_native_quantity_list(self):
        return list(self._handle.keys())

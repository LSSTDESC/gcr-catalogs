"""
AGN composite catalog (matched to cosmoDC2) reader

This reader was designed by Yao-Yuan Mao and Eve Kovacs
based a catalog provided by Scott Daniel.
"""

from GCRCatalogs.composite import CompositeReader
import numpy as np

def _calc_flux(mag):
    return np.power(10, -0.4*mag)


def get_composite_mag(original_mag, agn_mag):
    if np.ma.isMaskedArray(agn_mag):
        # fill masked array and convert to ndarray
        agn_mag = agn_mag.filled(fill_value=np.inf)
    # add agn flux to original flux
    return -2.5*np.log10(_calc_flux(original_mag) + _calc_flux(agn_mag))


def get_composite_mag_with_dutycycle(original_mag, agn_mag, duty_cycle_flag):
    # mask those agn whose duty-cycle flag is off
    if np.ma.isMaskedArray(agn_mag)  and np.ma.isMaskedArray(duty_cycle_flag):
        agn_mag[~duty_cycle_flag] = np.ma.masked
    #return composite mag
    return get_composite_mag(original_mag, agn_mag)


class AGNCombinedCatalog(CompositeReader):

    def _subclass_init(self, **kwargs):

        """
        AGNComposite catalog reader, inherited from CompositeCatalog class 
        """
        self._catalog_names = [cat.identifier for cat in self._catalogs]
        self.duty_cycle_on = kwargs.get('duty_cycle_on', True)
        
        for band in 'ugriz':
            if self.duty_cycle_on:
                self._quantity_modifiers['mag_{}_lsst'.format(band)] = (
                    get_composite_mag_with_dutycycle,
                    (self._catalog_names[0], 'mag_{}_lsst'.format(band)),
                    (self._catalog_names[1], 'mag_{}_lsst(agn)'.format(band)),
                    (self._catalog_names[1], 'duty_cycle_on'),
                )
            else:
                self._quantity_modifiers['mag_{}_lsst'.format(band)] = (
                    get_composite_mag,
                    (self._catalog_names[0], 'mag_{}_lsst'.format(band)),
                    (self._catalog_names[1], 'mag_{}_lsst(agn)'.format(band)),
                )
            self._quantity_modifiers['mag_{}_noagn_lsst'.format(band)] = (
                self._catalog_names[0], 'mag_{}_lsst'.format(band)
            )

        suppress_overwrite = kwargs.get('suppress_overwrite', None) #schema variables from main catalog
        if suppress_overwrite:
            for q in suppress_overwrite:
                if self._quantity_modifiers.get(q) == (self._catalog_names[1], q):
                    self._quantity_modifiers[q] = (self._catalog_names[0], q)

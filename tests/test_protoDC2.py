from __future__ import unicode_literals, absolute_import, print_function
import numpy as np
from astropy.cosmology import FlatLambdaCDM
from GCR import GCRQuery
import GCRCatalogs


gc = GCRCatalogs.load_catalog('protoDC2')
print('cosmology: {}'.format(gc.cosmology))
print('version = {}'.format(gc.get_catalog_info('version')))

def test_lightcone():
    assert gc.lightcone, 'Must be lightcone'

def test_cosmology():
    assert isinstance(gc.cosmology, FlatLambdaCDM), 'Must be FlatLambdaCDM'
    
def test_info():
    for q in sorted(gc.list_all_native_quantities()):
        assert gc.get_quantity_info(q), '{} does not have quantity_info'.format(q)

def test_angles():
    units = ['radians', 'degrees', 'arcsecond']
    angular_quantities = [q for q in sorted(gc.list_all_native_quantities()) if gc.get_quantity_info(q, default={}).get('unit') in units]
    for q in angular_quantities:
        print('{}: min={:13.4g} max={:13.4g}'.format(q, np.min(gc[q]), np.max(gc[q])))

def test_skyarea():
    assert hasattr(gc,'sky_area'), 'Must have sky area'
    assert isinstance(gc.sky_area, float), 'Must be float'
    print('sky area = {}'.format(gc.sky_area)) 

from __future__ import unicode_literals, absolute_import, print_function
import numpy as np
import GCRCatalogs
from GCRCatalogs.cosmology import Cosmology

gc = GCRCatalogs.load_catalog('protoDC2')
print('cosmology: {}'.format(gc.cosmology))
print('version = {}'.format(gc.get_catalog_info('version')))

def test_lightcone():
    assert gc.lightcone, 'Must be lightcone'

def test_cosmology():
    assert isinstance(gc.cosmology, Cosmology), 'Must be GCRCatalogs.cosmology.Cosmology'

def test_info():
    for q in sorted(gc.list_all_native_quantities()):
        assert gc.get_quantity_info(q), '{} does not have quantity_info'.format(q)

def test_angles():
    units = ['radians', 'degrees', 'arcsecond']
    angular_quantities = [q for q in sorted(gc.list_all_native_quantities()) if gc.get_quantity_info(q, default={}).get('unit') in units]
    for q in angular_quantities:
        print('{}: min={:13.4g} max={:13.4g}'.format(q, np.min(gc[q]), np.max(gc[q])))

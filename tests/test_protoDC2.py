"""
test_protoDC2.py
"""
import pytest
from astropy.cosmology import FlatLambdaCDM
import GCRCatalogs

# pylint: disable=redefined-outer-name
@pytest.fixture(scope='module')
def protoDC2():
    gc = GCRCatalogs.load_catalog('protoDC2')
    print('cosmology: {}'.format(gc.cosmology))
    print('version = {}'.format(gc.get_catalog_info('version')))
    return gc

def test_lightcone(protoDC2):
    assert protoDC2.lightcone, 'Must be lightcone'

def test_cosmology(protoDC2):
    assert isinstance(protoDC2.cosmology, FlatLambdaCDM), 'Must be FlatLambdaCDM'

def test_info(protoDC2):
    for q in protoDC2.list_all_native_quantities():
        assert protoDC2.get_quantity_info(q), '{} does not have quantity_info'.format(q)

def test_skyarea(protoDC2):
    assert hasattr(protoDC2,'sky_area'), 'Must have sky area'
    assert isinstance(protoDC2.sky_area, float), 'Must be float'
    print('sky area = {}'.format(protoDC2.sky_area))

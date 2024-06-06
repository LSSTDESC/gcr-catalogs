"""
test_protoDC2.py
"""
import pytest
from astropy.cosmology import FlatLambdaCDM
import GCRCatalogs
GCRCatalogs.ConfigSource.set_config_source()

# pylint: disable=redefined-outer-name
@pytest.fixture(scope='module')
def protoDC2():
    return GCRCatalogs.load_catalog('protoDC2')

def test_version(protoDC2):
    print('version =', protoDC2.version)

def test_lightcone(protoDC2):
    assert protoDC2.lightcone, '`lightcone` must be True'

def test_cosmology(protoDC2):
    assert isinstance(protoDC2.cosmology, FlatLambdaCDM), '`cosmology` must be a FlatLambdaCDM subclass'
    print('cosmology =', protoDC2.cosmology)

def test_skyarea(protoDC2):
    assert isinstance(protoDC2.sky_area, float), '`sky_area` must be a float'
    print('sky area =', protoDC2.sky_area)

"""
test_register.py
"""
import pytest
import GCRCatalogs

_default_catalogs_min_set = {
    'protoDC2',
    'buzzard',
    'buzzard_test',
    'buzzard_high-res',
}

# pylint: disable=redefined-outer-name
@pytest.fixture(scope='module')
def default_catalogs():
    return GCRCatalogs.get_available_catalogs()

def test_default_catalog_set(default_catalogs):
    assert set(default_catalogs).issuperset(_default_catalogs_min_set)

def test_available_catalog_set(default_catalogs):
    assert set(GCRCatalogs.available_catalogs).issuperset(set(default_catalogs))

@pytest.mark.parametrize('catalog', list(GCRCatalogs.get_available_catalogs()))
def test_default_catalog_config(catalog, default_catalogs):
    c = GCRCatalogs.get_catalog_config(catalog)
    v = default_catalogs[catalog]
    assert set(c) == set(v)
    assert c['subclass_name'] == v['subclass_name']

@pytest.mark.parametrize('catalog', list(GCRCatalogs.available_catalogs))
def test_config_entries(catalog):
    c = GCRCatalogs.get_catalog_config(catalog)
    assert 'subclass_name' in c

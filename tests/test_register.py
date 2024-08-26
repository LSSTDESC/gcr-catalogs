"""
test_register.py
"""
import pytest
import GCRCatalogs
GCRCatalogs.ConfigSource.set_config_source()

# pylint: disable=redefined-outer-name
@pytest.fixture(scope='module')
def default_catalogs():
    return GCRCatalogs.get_available_catalogs()

def test_available_catalog_set(default_catalogs):
    all_catalogs = GCRCatalogs.get_available_catalogs(False, True)
    assert set(all_catalogs).issuperset(set(default_catalogs))

@pytest.mark.parametrize('catalog', GCRCatalogs.get_available_catalogs(names_only=True))
def test_default_catalog_config(catalog, default_catalogs):
    c = GCRCatalogs.get_catalog_config(catalog)
    v = default_catalogs[catalog]
    assert set(c) == set(v)
    assert c['subclass_name'] == v['subclass_name']

@pytest.mark.parametrize('catalog', GCRCatalogs.get_available_catalogs(False, names_only=True))
def test_has_catalog(catalog):
    assert GCRCatalogs.has_catalog(catalog)

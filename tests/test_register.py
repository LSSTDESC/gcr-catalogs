"""
test_register.py
"""
import GCRCatalogs

_default_catalogs = {
    'protoDC2',
    'buzzard',
    'buzzard_test',
    'buzzard_high-res',
}

def test_default_catalogs():
    assert set(GCRCatalogs.get_available_catalogs()).issuperset(_default_catalogs)

def test_available_catalogs():
    assert set(GCRCatalogs.available_catalogs).issuperset(set(GCRCatalogs.get_available_catalogs()))

def test_default_catalog_config():
    for k, v in  GCRCatalogs.get_available_catalogs().items():
        c = GCRCatalogs.get_catalog_config(k)
        assert set(c) == set(v)
        assert c['subclass_name'] == v['subclass_name']

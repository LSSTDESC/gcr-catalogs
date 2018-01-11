import GCRCatalogs

_default_catalogs = {
    'protoDC2',
    'buzzard',
    'buzzard_test',
    'buzzard_high-res',
    'dc1',
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

def test_readers():
    readers = set((GCRCatalogs.register.resolve_config_alias(v)['subclass_name'] for v in GCRCatalogs.available_catalogs.values()))
    for reader in readers:
        GCRCatalogs.register.import_subclass(reader, 'GCRCatalogs', GCRCatalogs.BaseGenericCatalog)

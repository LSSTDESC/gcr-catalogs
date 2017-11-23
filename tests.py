import GCRCatalogs

_available_catalogs = {
    'proto-dc2_v2.0',
    'buzzard_v1.6',
    'buzzard_high-res_v1.1',
}

def test_available_catalogs():
    assert set(GCRCatalogs.available_catalogs).issuperset(_available_catalogs)


def test_readers():
    readers = set((v['subclass_name'] for v in GCRCatalogs.available_catalogs.values()))
    for reader in readers:
        GCRCatalogs.register.import_subclass(reader, 'GCRCatalogs', GCRCatalogs.BaseGenericCatalog)

import GCRCatalogs

_available_readers = {
        'AlphaQGalaxyCatalog',
        'AlphaQClusterCatalog',
        'BuzzardGalaxyCatalog',
        'DC1GalaxyCatalog',
}

_available_catalogs = {
        'proto-dc2_v2.0',
        'buzzard_v1.6',
        'buzzard_high-res_v1.1',
}

def test_available_readers():
    assert set(GCRCatalogs.get_available_readers()).issuperset(_available_readers)

def test_available_catalogs():
    assert set(GCRCatalogs.get_available_catalogs()).issuperset(_available_catalogs)

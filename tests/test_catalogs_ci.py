"""
test_catalogs_ci.py
"""
import GCRCatalogs

TEST_CATALOG = 'cosmoDC2_v1.1.4_small'

def test_load_catalog_and_quantities_for_ci():

    all_catalogs = list(GCRCatalogs.get_available_catalogs(include_default_only=False))
    assert TEST_CATALOG in all_catalogs, 'Test catalog missing'

    cat = GCRCatalogs.load_catalog(TEST_CATALOG)
    qs = cat.list_all_quantities()[:1] + cat.list_all_native_quantities()[:1]
    assert qs, 'No quantities found in ' + TEST_CATALOG
    data = next(cat.get_quantities(qs, return_iterator=True))
    assert all(data.get(q) is not None for q in qs), 'some quantities cannot be loaded'

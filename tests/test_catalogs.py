"""
test_catalogs.py
"""
import pytest
import GCRCatalogs

all_catalogs = list(GCRCatalogs.get_available_catalogs(include_default_only=False))

@pytest.mark.parametrize("catalog", all_catalogs)
def test_load_catalog_and_quantities(catalog):
    cat = GCRCatalogs.load_catalog(catalog)
    q = cat.list_all_quantities()[:1] + cat.list_all_native_quantities()[:1]
    for data in cat.get_quantities(q, return_iterator=True):
        assert data is not None
        break

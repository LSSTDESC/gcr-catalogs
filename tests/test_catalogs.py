"""
test_catalogs.py
"""
import pytest
import GCRCatalogs
GCRCatalogs.ConfigSource.set_config_source()

all_catalogs = list(GCRCatalogs.get_available_catalogs(include_default_only=False))

@pytest.mark.parametrize('catalog', all_catalogs)
def test_load_catalog_and_quantities(catalog):
    cat = GCRCatalogs.load_catalog(catalog)
    qs = cat.list_all_quantities()[:1] + cat.list_all_native_quantities()[:1]
    assert qs, 'No quantities found in ' + catalog
    data = next(cat.get_quantities(qs, return_iterator=True))
    assert all(data.get(q) is not None for q in qs), 'some quantities cannot be loaded'

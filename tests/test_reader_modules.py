"""
test_reader_modules.py
"""
import pytest
import GCRCatalogs

all_readers = set((
    GCRCatalogs.register.resolve_config_alias(v)['subclass_name']
    for v in GCRCatalogs.available_catalogs.values()
))

@pytest.mark.parametrize('reader', all_readers)
def test_reader_module(reader):
    GCRCatalogs.register.import_subclass(reader, 'GCRCatalogs', GCRCatalogs.BaseGenericCatalog)

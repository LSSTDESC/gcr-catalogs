"""
test_reader_modules.py
"""
import pytest
import GCRCatalogs
GCRCatalogs.ConfigSource.set_config_source()
from GCRCatalogs.catalog_helpers import import_subclass


all_readers = GCRCatalogs.register.get_reader_list()
# import_subclass('composite.CompositeReader')

@pytest.mark.parametrize('reader', all_readers)
def test_reader_module(reader):
    # GCRCatalogs.register.import_subclass(reader, 'GCRCatalogs', GCRCatalogs.BaseGenericCatalog)
    import_subclass(reader, 'GCRCatalogs', GCRCatalogs.BaseGenericCatalog)

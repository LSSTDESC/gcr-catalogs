"""
test_reader_modules.py
"""
import pytest
import GCRCatalogs

all_readers = GCRCatalogs.register.get_reader_list()

@pytest.mark.parametrize('reader', all_readers)
def test_reader_module(reader):
    GCRCatalogs.register.import_subclass(reader, 'GCRCatalogs', GCRCatalogs.BaseGenericCatalog)

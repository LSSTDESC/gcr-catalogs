"""
test_reader_modules.py
"""
import pytest
import GCRCatalogs
import os


all_readers = GCRCatalogs.register.get_reader_list()

@pytest.mark.parametrize('reader', all_readers)
def test_reader_module(reader):
    if GCRCatalogs.register.get_root_dir() is None:
        # Adust so test can be run anywhere
        GCRCatalogs.register.set_root_dir(os.getenv('HOME'))
    GCRCatalogs.register.import_subclass(reader, 'GCRCatalogs', GCRCatalogs.BaseGenericCatalog)

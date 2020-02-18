"""
test_reader_modules.py
"""
import pytest
import GCRCatalogs
import os

if GCRCatalogs.register._ROOT_DIR is None:
    # Adust so test can be run anywhere
    GCRCatalogs.register.set_root_dir(os.getenv('HOME'))

all_readers = GCRCatalogs.register.get_reader_list()

@pytest.mark.parametrize('reader', all_readers)
def test_reader_module(reader):
    GCRCatalogs.register.import_subclass(reader, 'GCRCatalogs', GCRCatalogs.BaseGenericCatalog)

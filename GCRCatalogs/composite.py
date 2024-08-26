"""
composite reader
"""
import warnings

from GCR import CompositeSpecs, CompositeCatalog

# from .register import load_catalog, load_catalog_from_config_dict, has_catalog
from .register import load_catalog, has_catalog
from .base_config import load_catalog_from_config_dict


class CompositeReader(CompositeCatalog):
    def __init__(self, **kwargs):
        instances = []
        for catalog_dict in kwargs['catalogs']:
            catalog_name = catalog_dict.get('catalog_name') or catalog_dict.get('based_on')
            if has_catalog(catalog_name):
                catalog = load_catalog(catalog_name, catalog_dict)
            elif 'subclass_name' in catalog_dict:
                if not catalog_name:
                    catalog_name = catalog_dict['subclass_name']
                catalog = load_catalog_from_config_dict(catalog_dict)
            else:
                raise ValueError('catalog config must specify `catalog_name`, `based_on`, or `subclass_name`')
            instances.append(CompositeSpecs(catalog, catalog_name, **catalog_dict))

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', 'CompositeCatalog is still an experimental feature')
            super(CompositeReader, self).__init__(instances, **kwargs)

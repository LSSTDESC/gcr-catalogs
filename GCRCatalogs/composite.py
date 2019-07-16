"""
composite reader
"""
import warnings
from GCR import CompositeCatalog, MATCHING_FORMAT, MATCHING_ORDER
from .register import load_catalog, load_catalog_from_config_dict, has_catalog

class CompositeReader(CompositeCatalog):
    def __init__(self, **kwargs):
        instances = []
        identifiers = []
        methods = []
        for catalog_dict in kwargs['catalogs']:
            catalog_name = catalog_dict.get('catalog_name') or catalog_dict.get('based_on')
            if has_catalog(catalog_name):
                catalog = load_catalog(catalog_name, catalog_dict)
            elif 'subclass_name' in catalog_dict:
                if not catalog_name:
                    catalog_name = catalog_dict['subclass_name']
                catalog = load_catalog_from_config_dict(catalog_dict)
            else:
                raise ValueError('catalog config must specify `catalog_name` or `subclass_name`')
            instances.append(catalog)
            identifiers.append(catalog_name)
            method = catalog_dict.get('matching_method', 'MATCHING_FORMAT')
            if method == 'MATCHING_FORMAT':
                method = MATCHING_FORMAT
                self.__len__ = instances[0].__len__
            elif method == 'MATCHING_ORDER':
                method = MATCHING_ORDER
                self.__len__ = instances[0].__len__
            methods.append(method)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', 'CompositeCatalog is still an experimental feature')
            super(CompositeReader, self).__init__(instances, identifiers, methods, **kwargs)

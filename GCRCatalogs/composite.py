"""
composite reader
"""
import warnings
from GCR import CompositeCatalog, MATCHING_FORMAT, MATCHING_ORDER
from .register import load_catalog, load_catalog_from_config_dict, available_catalogs

class CompositeReader(CompositeCatalog):
    def __init__(self, **kwargs):
        instances = []
        identifiers = []
        methods = []
        for catalog_dict in kwargs['catalogs']:
            catalog_name = catalog_dict.get('catalog_name')
            if catalog_name in available_catalogs:
                catalog = load_catalog(catalog_name, catalog_dict)
            else:
                catalog = load_catalog_from_config_dict(catalog_dict)
            instances.append(catalog)
            identifiers.append(catalog_dict.get('catalog_name'))
            method = catalog_dict.get('matching_method', 'MATCHING_FORMAT')
            if method == 'MATCHING_FORMAT':
                method = MATCHING_FORMAT
            elif method == 'MATCHING_ORDER':
                method = MATCHING_ORDER
            methods.append(method)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', 'CompositeCatalog is still an experimental feature')
            super(CompositeReader, self).__init__(instances, identifiers, methods, **kwargs)

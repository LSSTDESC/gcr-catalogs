"""
composite reader
"""
from GCR import CompositeCatalog, MATCHING_FORMAT, MATCHING_ORDER
from .register import load_catalog, load_catalog_from_config_dict

class CompositeReader(CompositeCatalog):
    def __init__(self, **kwargs):
        instances = []
        identifiers = []
        methods = []
        for catalog_dict in kwargs['catalogs']:
            if 'subclass_name' in catalog_dict:
                catalog = load_catalog_from_config_dict(catalog_dict)
            else:
                catalog = load_catalog(catalog_dict['catalog_name'])
            instances.append(catalog)
            identifiers.append(catalog_dict.get('catalog_name'))
            method = catalog_dict.get('matching_method', 'MATCHING_FORMAT')
            if method == 'MATCHING_FORMAT':
                method = MATCHING_FORMAT
            elif method == 'MATCHING_ORDER':
                method = MATCHING_ORDER
            methods.append(method)
        super(CompositeReader, self).__init__(instances, identifiers, methods, **kwargs)

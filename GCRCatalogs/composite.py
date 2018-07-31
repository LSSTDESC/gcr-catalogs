"""
composite reader
"""
from GCR import CompositeCatalog, MATCHING_FORMAT, MATCHING_ORDER
from .register import load_catalog

class CompositeReader(CompositeCatalog):
    def __init__(self, **kwargs):
        instances = []
        identifiers = []
        methods = []
        for catalog_dict in kwargs['catalogs']:
            catalog = catalog_dict['name']
            instances.append(load_catalog(catalog))
            identifiers.append(catalog)
            method = catalog_dict.get('method', 'MATCHING_FORMAT')
            if method == 'MATCHING_FORMAT':
                method = MATCHING_FORMAT
            elif method == 'MATCHING_ORDER':
                method = MATCHING_ORDER
            methods.append(method)
        super(CompositeReader, self).__init__(instances, identifiers, methods, **kwargs)

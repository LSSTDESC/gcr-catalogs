import os
from GCR import BaseGenericCatalog
from .utils import load_yaml

_registered_readers = dict()
_registered_catalogs = dict()

__all__ = ['register_reader', 'register_catalog', 'get_available_catalogs', 'load_catalog']

def register_reader(subclass):
    """
    Registers a new galaxy catalog type with the loading utility.

    Parameters
    ----------
    subclass: subclass of BaseGenericCatalog
    """
    assert issubclass(subclass, BaseGenericCatalog), "Provided class is not a subclass of BaseGenericCatalog"
    _registered_readers[subclass.__name__] = subclass


def register_catalog(catalog_name, catalog_config):
    """
    Registers a new galaxy catalog with the config file.

    Parameters
    ----------
    catalog_name
    """
    _registered_catalogs[catalog_name] = catalog_config


for _ in os.listdir(os.path.join(os.path.dirname(__file__), 'catalog_configs')):
    register_catalog(os.path.splitext(_)[0], load_yaml(os.path.join(os.path.dirname(__file__), 'catalog_configs', _)))


def get_available_catalogs():
    return _registered_catalogs


def get_available_readers():
    return _registered_readers


def load_catalog(catalog_name, config_overwrite=None):
    """
    Load a galaxy catalog as specified in a yaml config file.

    Parameters
    ----------
    catalog_name : str
        name of the catalog
    config_overwrite : dict, optional
        a dictionary of config options to overwrite

    Return
    ------
    galaxy_catalog : subclass of BaseGalaxyCatalog
    """
    config = _registered_catalogs[catalog_name]
    if config_overwrite:
        config.update(config_overwrite)
    return _registered_readers[config['subclass_name']](**config)

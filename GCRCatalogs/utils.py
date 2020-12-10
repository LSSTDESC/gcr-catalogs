"""
utility module
"""
import hashlib
import os

__all__ = ['md5', 'is_string_like', 'get_config_dir']

def md5(fname, chunk_size=65536):
    """
    generate MD5 sum for *fname*
    """
    hash_md5 = hashlib.md5()
    with open(fname, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def is_string_like(obj):
    """
    test if `obj` is string like
    """
    try:
        obj + ''
    except (TypeError, ValueError):
        return False
    return True


def first(iterable, default=None):
    """
    returns the first element of `iterable`
    """
    return next(iter(iterable), default)

def get_config_dir(create=False):
    if os.getenv("XDG_CONFIG_HOME"):                   # Unix
        user_config_dir = os.getenv("XDG_CONFIG_HOME")	
    elif os.getenv("LOCALAPPDATA"):                     # Win
        user_config_dir = os.getenv("LOCALAPPDATA")
    else:
        user_config_dir = os.path.join(os.path.expanduser("~"), ".config")

    desc_config_dir = os.path.join(user_config_dir, "lsstdesc")

    if create:
        os.makedirs(desc_config_dir, exist_ok=True)

    return desc_config_dir
      

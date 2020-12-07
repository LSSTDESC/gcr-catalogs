"""
utility module
"""
import hashlib

__all__ = ['md5', 'is_string_like', 'first', 'decode']


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


def decode(bytestring):
    """
    decode a bytestring is possible
    """
    try:
        return bytestring.decode()
    except AttributeError:
        return str(bytestring)

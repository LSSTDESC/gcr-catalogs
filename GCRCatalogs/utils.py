"""
utility module
"""
import hashlib

def md5(fname, chunk_size=65536):
    """
    generate MD5 sum for *fname*
    """
    hash_md5 = hashlib.md5()
    with open(fname, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

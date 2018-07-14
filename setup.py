#!/usr/bin/env python
"""
Catalog repo for LSST DESC
Copyright (c) 2017 LSST DESC
http://opensource.org/licenses/MIT
"""

import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'GCRCatalogs', 'version.py')) as f:
    exec(f.read()) # pylint: disable=W0122

setup(
    name='GCRCatalogs',
    version=__version__, # pylint: disable=E0602
    description='Catalog repo for LSST DESC',
    url='https://github.com/LSSTDESC/gcr-catalogs',
    author='Yao-Yuan Mao',
    author_email='yymao.astro@gmail.com',
    maintainer='Yao-Yuan Mao',
    maintainer_email='yymao.astro@gmail.com',
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='GCR',
    packages=['GCRCatalogs'],
    install_requires=['future', 'requests', 'pyyaml', 'numpy', 'astropy', 'GCR>=0.7.1'],
    extras_require = {
        'protodc2': ['h5py'],
        'instance': ['pandas'],
        'reference': ['pandas'],
        'dc1': ['sqlalchemy', 'pymssql'],
        'dc2_coadd': ['tables', 'pandas'],
        'focal_plane': ['scikit-image', 'pandas'],
        'full': ['h5py', 'sqlalchemy', 'pymssql', 'pandas', 'tables', 'scikit-image'],
    },
    package_data={'GCRCatalogs': ['catalog_configs/*.yaml']},
)

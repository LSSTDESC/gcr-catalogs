#!/usr/bin/env python
"""
Catalog repo for LSST DESC
Copyright (c) 2017 LSST DESC
http://opensource.org/licenses/MIT
"""

import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), 'GCRCatalogs', 'version.py')) as f:
    exec(f.read())  # pylint: disable=W0122

setup(
    name='lsstdesc-gcr-catalogs',
    version=__version__,  # pylint: disable=E0602 # noqa: F821
    description='Catalog repo for LSST DESC',
    url='https://github.com/LSSTDESC/gcr-catalogs',
    author='Yao-Yuan Mao',
    author_email='yymao.astro@gmail.com',
    maintainer='Yao-Yuan Mao',
    maintainer_email='yymao.astro@gmail.com',
    license='MIT',
    license_files = ('LICENSE',),
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='GCR',
    packages=find_packages(),
    install_requires=['requests', 'pyyaml', 'numpy', 'astropy', 'GCR>=0.9.2'],
    extras_require={
        'full': ['h5py', 'healpy', 'pandas', 'pyarrow', 'tables'],
    },
    package_data={'GCRCatalogs': ['catalog_configs/*.yaml', 'site_config/*.yaml', 'SCHEMA.md']},
)

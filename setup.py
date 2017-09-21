#!/usr/bin/env python
"""
Catalog repo for LSST DESC
Copyright (c) 2017 LSST DESC
http://opensource.org/licenses/MIT
"""

from setuptools import setup

setup(
    name='GCRCatalogs',
    version='0.1.2',
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
    install_requires=['numpy','h5py','astropy','GCR'],
    package_data = {'GCRCatalogs': ['catalog_configs/*.yaml']},
)

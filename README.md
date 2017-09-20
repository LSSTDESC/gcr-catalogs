# GCR Catalogs

This repo hosts the catalogs used by [DESCQA2](https://github.com/LSSTDESC/descqa). 

All the catalogs can be accessed through an unified inferface, the [GCR](https://github.com/yymao/generic-catalog-reader).
A full description of the `GCR` API can be found [here](https://github.com/yymao/generic-catalog-reader/blob/master/GCR.py).

Currently there are two catalogs available (more to come):

1. "Proto-DC2" (AlphaQ) catalog by Eve Kovacs, Danila Korytov, Katrin Heitmann et al. (**NOT READY YET**)
2. Buzzard v1.5 by Joe DeRose, Risa Wechsler et al.

Each of the catalogs is specified by a YAML config file, which can be found [here](https://github.com/LSSTDESC/gcr-catalogs/tree/master/GCRCatalogs/catalog_configs).


Some examples of using `GCRCatalogs` can be found [here](https://github.com/LSSTDESC/gcr-catalogs/tree/master/examples). (Thanks Joe for providing the CLF test!)

To use these catalogs, first clone this repository on NERSC (yes, you need a NERSC account):

    git clone git@github.com:LSSTDESC/gcr-catalogs.git

And then, [start a NERSC notebook server](https://jupyter.nersc.gov) and browse to `gcr-catalogs/examples` to start the example notebooks (using python 2 kernal). You can copy these notebooks and then add your tests.


This package is also pip installable

    pip install git+git://github.com/LSSTDESC/gcr-catalogs.git

It is already installed in the DESCQA envoirnment on NERSC. You can activate this envoirnment:

    source /global/common/cori/contrib/lsst/apps/anaconda/4.4.0-py2/bin/activate
    source activate DESCQA


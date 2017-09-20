# GCR Catalogs

Currently there are two catalogs available:

1. "Proto-DC2" (AlphaQ) catalog by Eve Kovacs, Danila Korytov, Katrin Heitmann et al. (**NOT READY YET**)
2. Buzzard v1.5 by Joe DeRose, Risa Wechsler et al.

We will add the specifications of these catalogs into the yaml config files that can be found [here](https://github.com/LSSTDESC/gcr-catalogs/tree/master/GCRCatalogs/catalog_configs).

Examples of using the GCR API can be found [here](https://github.com/LSSTDESC/gcr-catalogs/tree/master/examples). (Thanks Joe for providing the CLF test!)

To use these catalogs with the GCR, first clone this repository on NERSC (yes, you need a NERSC account):

    git clone git@github.com:LSSTDESC/gcr-catalogs.git

And then, [start a NERSC notebook server](https://jupyter.nersc.gov) and browse to `generic-catalog-reader/examples` to start the example notebooks. You can copy these notebooks and then add your tests.

One can also pip install the package (this does not include the yaml and example files)

    pip install git+git://github.com/LSSTDESC/gcr-catalogs.git

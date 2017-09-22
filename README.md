# GCR Catalogs

This repo hosts the mock galaxy catalogs used by [DESCQA2](https://github.com/LSSTDESC/descqa).

On a NERSC machine, all these catalogs can be directly accessed through the "Generic Catalog Reader" (GCR) inferface.
More information about GCR can be found [here](https://github.com/yymao/generic-catalog-reader).

Currently there are three catalogs available (more to come):

1. `proto-dc2-v1.0` (**NOT READY YET**): Proto-DC2 (AlphaQ) catalog by Eve Kovacs, Danila Korytov, Andrew Benson, Katrin Heitmann et al. 
2. `buzzard_v1.5`: Buzzard catalog v1.5 by Joe DeRose, Risa Wechsler et al.
3. `dc1`: DC1 catalog

Each of the catalogs is specified by a YAML config file, which can be found [here](https://github.com/LSSTDESC/gcr-catalogs/tree/master/GCRCatalogs/catalog_configs). The galaxy quantities in these catalogs conform to [this schema](https://docs.google.com/document/d/1rUsImkBkjjw82Xa_-3a8VMV6K9aYJ8mXioaRhz0JoqI/edit).


## Setup

`GCRCatalogs` is already installed in the DESCQA Python envoirnment at NERSC. To use it:

### with Jypeter notebooks:

First, [start a NERSC notebook server](https://jupyter.nersc.gov) and open a notebook with Python 2 kernel. Make sure you add the DESCQA Python enviornment to `sys.path`:

```python
import sys
sys.path.insert(0, '/global/common/cori/contrib/lsst/apps/anaconda/py2-envs/DESCQA/lib/python2.7/site-packages')
```

### in a terminal:

Activate DESCQA Python environment by running the following on NERSC (needs to be in `bash` or `zsh`):

    source /global/common/cori/contrib/lsst/apps/anaconda/4.4.0-py2/bin/activate
    source activate DESCQA


### Getting latest version 

You can install the latest version by running:

    pip install git+git://github.com/LSSTDESC/gcr-catalogs.git


## Usage

Some examples of using `GCRCatalogs` can be found [here](https://github.com/LSSTDESC/gcr-catalogs/tree/master/examples). (Thanks to Joe DeRose for providing the CLF test example!)

Here's a minimal example:

```python
import GCRCatalogs
gc = GCRCatalogs.load_catalog('proto-dc2-v1.0')
gc.get_quantities(['redshift_true'])
print gc.list_all_quantities()
```

### interfacing PhoSim through CatSim:

See an example [here](https://github.com/LSSTDESC/gcr-catalogs/blob/master/examples/phosim_descqa.py)

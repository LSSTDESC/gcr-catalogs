# GCR Catalogs

This repo hosts the mock galaxy catalogs availble to the LSST DESC. These catalogs are also used by [DESCQA](https://github.com/LSSTDESC/descqa).

On a NERSC machine, all these catalogs can be directly accessed through the "Generic Catalog Reader" (GCR) inferface.
More information about GCR can be found [here](https://github.com/yymao/generic-catalog-reader).

Currently these sets of catalogs are available (**Note that these catalogs are not perfect and will continue to be updated**):

1. protoDC2: 
   by Eve Kovacs, Danila Korytov, Andrew Benson, Katrin Heitmann et al. 
   - `protoDC2` (full catalog)
   - `protoDC2_test` (same as `protoDC2` but this one skips time-consuming md5 check.)
   
2. Buzzard series: 
   by Joe DeRose, Risa Wechsler, Eli Rykoff et al.
   - `buzzard` (full catalog, DES Y3 area)
   - `buzzard_test` (same as `buzzard` but a small subset for testing purpose)
   - `buzzard_high-res` (higher resolution, smaller sky area)
   - `buzzard_v1.6_1`, `buzzard_v1.6_2`, `buzzard_v1.6_3`, `buzzard_v1.6_5`, `buzzard_v1.6_21` (different realizations of `buzzard`)
      
3. DC1 catalog: 
   - `dc1`

Each of the catalogs is specified by a YAML config file, which can be found [here](https://github.com/LSSTDESC/gcr-catalogs/tree/master/GCRCatalogs/catalog_configs). The galaxy quantities in these catalogs conform to [the schema](GCRCatalogs/SCHEMA.md).


## Use GCRCatalogs on NERSC

_Note_: These instructions about Python environment may change in the future. If you encounter issues, please check if there's any updates on these instructions.

`GCRCatalogs` is already installed in the DESCQA Python envoirnment at NERSC. To use it:

### In Jypeter notebooks:

First, [start a NERSC notebook server](https://jupyter-dev.nersc.gov) and open a notebook with a Python kernel. In the first cell, insert the Python enviornment to `sys.path`:

For Python 3 (recommended):
```python
import sys
sys.path.insert(0, '/global/common/software/lsst/common/miniconda/py3-4.2.12/lib/python3.6/site-packages')
```

For Python 2:
```python
import sys
sys.path.insert(0, '/global/common/cori/contrib/lsst/apps/anaconda/py2-envs/DESCQA/lib/python2.7/site-packages')
```

### In a terminal:

Activate DESCQA Python environment by running the following on NERSC (needs to be in `bash` or `zsh`):

For Python 3 (recommended):
```bash
source /global/common/software/lsst/cori-haswell-gcc/stack/setup_w_2017_46_py3_gcc6.sh
```

For Python 2:
```bash
source /global/common/cori/contrib/lsst/apps/anaconda/4.4.0-py2/bin/activate
source activate DESCQA
```

### In a Python script: 

To be able to import `GCRCatalogs`, the first line of the script should be:

For Python 3 (recommended):
```bash
#!/global/common/software/lsst/common/miniconda/py3-4.2.12/bin/python
```

For Python 2:
```bash
#!/global/common/cori/contrib/lsst/apps/anaconda/py2-envs/DESCQA/bin/python 
```

### Use the lateset version of GCRCatalogs

If you need to use a newer version of GCRCatalogs then the one installed on NERSC, you can clone this repo (on a NERSC machine), 
and add the path to `sys.path`. You should add this line *right after* you insert the DESC Python environment. 
```python
sys.path.insert(0, '/path/to/gcr-catalogs')
```

## Usage and examples

- See [this notebook](https://github.com/LSSTDESC/gcr-catalogs/blob/master/examples/GCRCatalogs%20Demo.ipynb) for a detail tutorial on how to use GCR Catalogs.

- See [this notebook](https://github.com/LSSTDESC/gcr-catalogs/blob/master/examples/CLF%20Test.ipynb) for an actual application (the Conditional  Luminosity Function test) using GCR Catalogs. (Thanks to Joe DeRose for providing the CLF test example!)

- See [GCR documentation](https://yymao.github.io/generic-catalog-reader/) for the complete GCR API.


# GCR Catalogs

[![Paper DOI](https://img.shields.io/badge/Paper%20DOI-10.3847%2F1538--4365%2Faaa6c3-brightgreen.svg)](https://doi.org/10.3847/1538-4365/aaa6c3)
[![arXiv:1709.09665](https://img.shields.io/badge/astro--ph.IM-arXiv%3A1709.09665-B31B1B.svg)](https://arxiv.org/abs/1709.09665)

This repo hosts the mock galaxy catalogs availble to the LSST DESC and are used by [DESCQA](https://github.com/LSSTDESC/descqa). 
The GCRCatalogs module uses the "Generic Catalog Reader" (GCR) to provide a unified interface to access these catalogs. 
More information about GCR can be found in the [GCR repo](https://github.com/yymao/generic-catalog-reader).
Description of the concept of this reader interface can be found in the [DESCQA paper](https://doi.org/10.3847/1538-4365/aaa6c3).

Currently these sets of catalogs are available (**Note that these catalogs are not perfect and will continue to be updated**):

1. protoDC2: 
   by Andrew Benson, Andrew Hearin, Katrin Heitmann, Danila Korytov, Eve Kovacs et al.
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

Each of the catalogs is specified by a YAML config file, which can be found [here](GCRCatalogs/catalog_configs). The galaxy quantities in these catalogs conform to [the schema](GCRCatalogs/SCHEMA.md).


## Use GCRCatalogs on NERSC

_Note_: These instructions about Python environment may change in the future. If you encounter issues, please check if there's any updates on these instructions.

`GCRCatalogs` is already installed in the DESCQA Python envoirnment at NERSC. To use it:

### In Jypeter notebooks:

First, [start a NERSC notebook server](https://jupyter-dev.nersc.gov) and open a notebook with a Python kernel. In the first cell, insert the Python enviornment to `sys.path`:

For Python 3 (recommended):
```python
import sys
sys.path.insert(0, '/global/common/software/lsst/common/miniconda/current/lib/python3.6/site-packages')
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
source /global/common/software/lsst/common/miniconda/setup_current_python.sh
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
#!/global/common/software/lsst/common/miniconda/current/bin/python
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

If you are running DESCQA and want to use your cloned GCRCatalogs, you can add the path to `-p` option:
```bash
./run_master.sh -t <tests> -c <catalogs> -p /path/to/gcr-catalogs
```

## Usage and examples

- See [this notebook](examples/GCRCatalogs%20Demo.ipynb) for a detail tutorial on how to use GCR Catalogs.

- See [this notebook](examples/CLF%20Test.ipynb) for an actual application (the Conditional  Luminosity Function test) using GCR Catalogs. (Thanks to Joe DeRose for providing the CLF test example!)

- See [GCR documentation](https://yymao.github.io/generic-catalog-reader/) for the complete GCR API.


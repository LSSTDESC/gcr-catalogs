# GCR Catalogs

[![doi:10.3847/1538-4365/aaa6c3](https://img.shields.io/badge/Paper%20DOI-10.3847%2F1538--4365%2Faaa6c3-brightgreen.svg)](https://doi.org/10.3847/1538-4365/aaa6c3)
[![arXiv:1709.09665](https://img.shields.io/badge/astro--ph.IM-arXiv%3A1709.09665-B31B1B.svg)](https://arxiv.org/abs/1709.09665)

`GCRCatalogs` is a Python package that serves as a repository of various
galaxy catalogs and sky catalogs for the LSST Dark Energy Science Collaboration (DESC).
It provides a unified user interface to access all catalogs by using
the [Generic Catalog Reader (GCR)](https://github.com/yymao/generic-catalog-reader) base class.

This package is also used by the [DESCQA](https://github.com/LSSTDESC/descqa)
validation framework, and the concept and description of this reader interface
can be found in the [DESCQA paper](https://doi.org/10.3847/1538-4365/aaa6c3)
and also the [GCR repo](https://github.com/yymao/generic-catalog-reader).


## Available Catalogs

You can always run the following code to see all available catalogs:
```python
import GCRCatalogs
sorted(GCRCatalogs.get_available_catalogs(False))
```
(*Note*: remove `False` in the above line to only see recommended catalogs.)

Each catalog is specified by a YAML config file,
which can be found [here](GCRCatalogs/catalog_configs).

You can also find an overview of the data products of DESC Data Challenge 2
at [this Confluence page](https://confluence.slac.stanford.edu/x/oJgHDg)
(*DESC member only*).

1. "protoDC2" Extragalactic Catalogs: \
   *by Andrew Benson, Andrew Hearin, Katrin Heitmann, Danila Korytov, Eve Kovacs et al.*
   - `protoDC2` (full catalog)
   - `protoDC2_test` (same as `protoDC2` but this one skips time-consuming md5 check.)
   - `proto-dc2_vX.X_test.yaml` (some other versions of the protoDC2 catalog. You can run
     ```python
     sorted((name for name in GCRCatalogs.get_available_catalogs(False) if name.startswith('proto')))
     ```
     to see all available versions.

2. "Buzzard" Extragalactic Catalogs: \
   *by Joe DeRose, Risa Wechsler, Eli Rykoff et al.*
   - `buzzard` (full catalog, DES Y3 area)
   - `buzzard_test` (same as `buzzard` but a small subset for testing purpose / faster access)
   - `buzzard_high-res` (higher resolution, smaller sky area)
   - `buzzard_v1.6_1`, `buzzard_v1.6_2`, `buzzard_v1.6_3`, `buzzard_v1.6_5`, `buzzard_v1.6_21` (different realizations of `buzzard`)

3. DC2 "Coadd Catalogs": \
   *by LSST DESC, compiled by Michael Wood-Vasey*
   - `dc2_coadd_run1.1p`: coadd catalog for Run 1.1p
   - `dc2_coadd_run1.1p_tract4850`: same as `dc2_coadd_run1.1p` but has only one tract (4850) for testing purpose / faster access

4. DC2 "Reference Catalogs": \
   *by LSST DESC, compiled by Scott Daniel*
   - `dc2_reference_run1.1p`: reference catalog for Run 1.1p
   - `dc2_reference_run1.2p`: reference catalog for Run 1.2p

5. DC2 "Instance Catalogs": \
   *by LSST DESC, compiled by Scott Daniel*
   - `dc2_instance_example1`: an example instance catalog
   - `dc2_instance_example2`: another example instance catalog

6. DC1 Galaxy Catalog:
   - `dc1`: Galaxy catalog used for DC1 (also known as "the catalog on fatboy")

7. HSC Coadd Catalog for PDR1 XMM field: \
   *by the Hyper Suprime-Cam (HSC) Collaboration*
   - `hsc-pdr1-xmm`


## Use GCRCatalogs at NERSC

Here's the instruction of using `GCRCatalogs` at NERSC.
All catalogs that are available in `GCRCatalogs` are all physically located at NERSC.
Note that you need to be in the `lsst` user group to access them.
You can find instructions about getting NERSC account and joining `lsst` group
at [this Confluence page](https://confluence.slac.stanford.edu/x/mgRTD)
(*DESC members only*).

### With Jypeter notebooks:

It is recommended that you first install DESC-specific kernels for your
NERSC jupyter-dev environment (*you only need to do this once*).
To do so, log in to cori.nersc.gov and run:
```bash
source /global/common/software/lsst/common/miniconda/kernels/setup.sh
```
Detailed instructions can also be found at [this Confluence page](https://confluence.slac.stanford.edu/x/1_ubDQ)
(*DESC members only*).

Then, you can [start a NERSC notebook server](https://jupyter-dev.nersc.gov)
and open a notebook with the `desc-python` or `desc-stack` kernel.
`GCRCatalogs` and necessary dependencies are already installed in these two kernels.
You can check if it works simply by running:

```python
import GCRCatalogs
```

If you don't have these DESC-specific kernels installed, you can modify
`sys.path` at run time (*not recommended*).
At the very first cell of your notebook, run:

```python
import sys
sys.path.insert(0, '/global/common/software/lsst/common/miniconda/current/lib/python3.6/site-packages')
```

### In a terminal or in a Python script:

You can activate DESC Python environment by running the following line on NERSC
(needs to be in `bash` or `zsh`):

```bash
source /global/common/software/lsst/common/miniconda/setup_current_python.sh
```

If you want to use `GCRCatalogs` in a Python script, you can either activate DESC
Python environment before you run the script, or make the first line of the script to be:

```bash
#!/global/common/software/lsst/common/miniconda/current/bin/python
```

### Use the latest version of GCRCatalogs

If you need to use a newer version of `GCRCatalogs` then the one installed in the DESC Python environment,
here's what you need to do:

1. Clone this repo (on a NERSC machine):
   ```bash
   git clone git@github.com:LSSTDESC/gcr-catalogs.git
   ```
2. Add the path to `sys.path` in your notebook.
   ```python
   import sys
   sys.path.insert(0, '/path/to/cloned/gcr-catalogs')
   ```
   (Note that if you use `sys.path` for the DESC Python environment, you should add the line above *right after* you insert the DESC Python environment.)

If you are running DESCQA and want to use your cloned `GCRCatalogs`, you can add the path to `-p` option:
```bash
./run_master.sh -t <tests> -c <catalogs> -p /path/to/cloned/gcr-catalogs
```
See [more instrcutions for DESCQA here](https://github.com/LSSTDESC/descqa/blob/master/CONTRIBUTING.md#master-script-options).

`GCRCatalogs` is also pip-installable, in case you need to install,
say the master branch of `GCRCatalogs` in your own Python environment
(*no, in most cases you don't need this*):
```bash
pip install https://github.com/LSSTDESC/gcr-catalogs/archive/master.zip
```

## Usage and Examples

Here's the very basic usage of `GCRCatalogs`.
Scroll down to see the example notebooks and more advanced usages.

```python
import GCRCatalogs

# see all available catalogs
print(sorted(GCRCatalogs.get_available_catalogs(False)))

# load a calalog
catalog = GCRCatalogs.load_catalog('protoDC2')

# see all available quantities
print(sorted(catalog.list_all_quantities()))

# load quantities
data = catalog.get_quantities(['ra', 'dec'])
```

- You can find quantity definitions in [`GCRCatalogs/SCHEMA.md`](https://github.com/LSSTDESC/gcr-catalogs/blob/master/GCRCatalogs/SCHEMA.md).

- See [this notebook](examples/GCRCatalogs%20Demo.ipynb) for a detailed tutorial on how to use `GCRCatalogs`.

- See [this notebook](examples/CLF%20Test.ipynb) for an actual application (the Conditional Luminosity Function test) using GCR Catalogs. (Thanks to Joe DeRose for providing the CLF test example!)

- You can find more notebooks that use `GCRCatalogs` in [`LSSTDESC/DC2_Repo`](https://github.com/LSSTDESC/DC2_Repo/tree/master/Notebooks).

- See also the [GCR documentation](https://yymao.github.io/generic-catalog-reader/) for the complete GCR API.

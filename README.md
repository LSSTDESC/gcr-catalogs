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

You can always run the following code to see the up-to-date list of all available catalogs:
```python
import GCRCatalogs
sorted(GCRCatalogs.get_available_catalogs(False))
```
(*Note*: remove `False` in the above line to only see recommended catalogs.)

Each catalog is specified by a YAML config file,
which can be found [here](GCRCatalogs/catalog_configs).

You can also find an overview and more detailed description of all the data
products of DESC Data Challenge 2 at the
["DC2 Data Product Overview"](https://confluence.slac.stanford.edu/x/oJgHDg)
Confluence page (*DESC member only*).

-  **"cosmoDC2" Extragalactic Catalogs** \
   *by Andrew Benson, Andrew Hearin, Katrin Heitmann, Danila Korytov, Eve Kovacs, Patricia Larsen, Eli Rykoff et al.*
   - `cosmoDC2_v1.0`: full cosmoDC2 catalog (v1.0)
   - `cosmoDC2_v1.0_image`: same as `cosmoDC2_v1.0` but with only the sky area that is needed for image simulation (Run 2.0)
   - `cosmoDC2_v1.0_small`: 26 contiguous healpixels of `cosmoDC2_v1.0` for testing purpose
   - `cosmoDC2_v1.1.4_image`: same as `cosmoDC2_v1.0_image` but with cosmoDC2 v1.1.4 for Run 2.1
   - `cosmoDC2_v1.1.4_small`: 17 contiguous healpixels of `cosmoDC2_v1.1.4_image` for testing purpose
   - `cosmoDC2_v1.1.4_redmapper_v0.2.1py`: Redmapper catalog (v0.2.1) for `cosmoDC2_v1.1.4_image`.

-  **"protoDC2" Extragalactic Catalogs** \
   *by Andrew Benson, Andrew Hearin, Katrin Heitmann, Danila Korytov, Eve Kovacs, Patricia Larsen et al.*
   - `protoDC2`: full catalog
   - `protoDC2_test`: same as `protoDC2` but this one skips time-consuming md5 check
   - `proto-dc2_vX.X_test.yaml`: some other versions of the protoDC2 catalog. You can run
     ```python
     sorted((name for name in GCRCatalogs.get_available_catalogs(False) if name.startswith('proto-dc2_')))
     ```
     to see all available versions.

-  **"Buzzard" Extragalactic Catalogs** \
   *by Joe DeRose, Risa Wechsler, Eli Rykoff et al.*
   - `buzzard`: full catalog, DES Y3 area
   - `buzzard_test`: same as `buzzard` but a small subset for testing purpose / faster access
   - `buzzard_high-res`: higher resolution, smaller sky area
   - `buzzard_v1.9.2_x`: different realizations of the version of the `buzzard` catalog documented in [arXiv:1901.02401](https://arxiv.org/abs/1901.02401).
   - `buzzard_v1.6_x`: different realizations of an older version of `buzzard`.
     You can run
     ```python
     sorted((name for name in GCRCatalogs.get_available_catalogs(False) if name.startswith('buzzard_v1.6')))
     ```
     to see all available versions.


-  **DC2 "Object Catalogs"** \
   *by LSST DESC, compiled by Michael Wood-Vasey*
   - `dc2_object_run2.1i_dr1a`: static object catalog for Run 2.1i DR1a (with only DPDD columns and native columns needed for the DPDD columns; use `dc2_object_run2.1i_dr1a_all_columns` if you need additional columns)
   - `dc2_object_run1.2i`: static object catalog for Run 1.2i (with only DPDD columns and native columns needed for the DPDD columns)
   - `dc2_object_run1.2i_with_photoz`: same as `dc2_object_run1.2i` but with photo-z's (columns that start with `photoz_`). Photo-z provided by Sam Schmidt.
   - `dc2_object_run1.2i_all_columns`: static object catalog for Run 1.2i (with DPDD and all native columns, slower to access)
   - `dc2_object_run1.2i_tract4850`: same as `dc2_object_run1.2i_all_columns` but only has one tract (4850)for testing purpose / faster access
   - `dc2_object_run1.2i_tract5063`: same as `dc2_object_run1.2i_all_columns` but only has one tract (5063)for testing purpose / faster access
   - `dc2_object_run1.2i_tract5063_with_metacal`: same as `dc2_object_run1.2i_tract5063` but with metacal (columns that start with `mcal_`). Metacal catalog provided by Johann Cohen-Tanugi and Erin Sheldon.
   - `dc2_object_run1.2p`: static object catalog for Run 1.2p (with only DPDD columns and native columns needed for the DPDD columns)
   - `dc2_object_run1.2p_all_columns`: static object catalog for Run 1.2p (with DPDD and all native columns, slower to access)
   - `dc2_object_run1.2p_tract4850`: same as `dc2_object_run1.2p_all_columns` but only has one tract (4850)for testing purpose / faster access
   - `dc2_object_run1.2p_v3_with_photoz`: same as `dc2_object_run1.2p_v3` but with photo-z's (columns that start with `photoz_`). Photo-z provided by Sam Schmidt.
   - `dc2_object_run1.1p`: static object catalog for Run 1.1p (with DPDD and all native columns)
   - `dc2_object_run1.1p_tract4850`: same as `dc2_object_run1.1p` but has only one tract (4850) for testing purpose / faster access

-  **DC2 "Source Catalogs"** \
   *by LSST DESC, compiled by Michael Wood-Vasey*
   - `dc2_source_run1.2i`: Source Table catalog for Run 1.2i (with only DPDD columns and native columns needed for the DPDD columns)

-  **DC2 "Forced Source Catalogs"** \
   *by LSST DESC, compiled by Michael Wood-Vasey*
   - `dc2_forced_source_run1.2p`: Forced Source Table catalog for Run 1.2p (with only DPDD columns and native columns needed for the DPDD columns).  This is the forced-position photometry based on the positions in the Object Table.

-  **DC2 "DIA Source Test Catalogs"** \
   *by LSST DESC, compiled by Michael Wood-Vasey*
   - `dc2_dia_source_run1.2p_test`: DIASource Table catalog for a test DIA processing of Tract+Paptch 4849+6,6 for Run 1.2p (with only DPDD columns and native columns needed for the DPDD columns).

-  **DC2 "Truth Catalogs"** \
   *by LSST DESC, compiled by Scott Daniel*
   - `dc2_truth_run1.2_static`: truth catalog for Run 1.2 (static objects only, corresponds to `proto-dc2_v3.0`)
   - `dc2_truth_run1.2_variable_lightcurve`: light curves of variable objects in the truth catalog for Run 1.2
   - `dc2_truth_run1.2_variable_summary`: summary table of variable objects in the truth catalog for Run 1.2
   - `dc2_truth_run1.1_static`: truth catalog for Run 1.1 (static objects only, corresponds to `proto-dc2_v2.1.2`)

-  **DC2 "Reference Catalogs"** \
   *by LSST DESC, compiled by Scott Daniel*
   - `dc2_reference_run1.2`: reference catalog for Run 1.2 (corresponds to `proto-dc2_v3.0`)
   - `dc2_reference_run1.1`: reference catalog for Run 1.1 (corresponds to `proto-dc2_v2.1.2`)

-  **DC2 "Instance Catalogs"** \
   *by LSST DESC, compiled by Scott Daniel*
   - `dc2_instance_example1`: an example instance catalog
   - `dc2_instance_example2`: another example instance catalog

-  **HSC Coadd Catalog for PDR1 XMM field** \
   *by the Hyper Suprime-Cam (HSC) Collaboration*
   - `hsc-pdr1-xmm`

-  **DC2 e-images** \
   *by LSST DESC*
   - `dc2_eimages_run1.2i_visit-181898`: one visit of e-images for Run 1.2i
   - `dc2_eimages_run1.2p_visit-181898`: one visit of e-images for Run 1.2p


## Use GCRCatalogs at NERSC

Here's the instruction of using `GCRCatalogs` at NERSC.
All catalogs that are available in `GCRCatalogs` are all physically located at NERSC.
Note that you need to be in the `lsst` user group to access them.
You can find instructions about getting NERSC account and joining `lsst` group
at [this Confluence page](https://confluence.slac.stanford.edu/x/mgRTD)
(*DESC members only*).

### With Jupyter notebooks:

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
Python environment before you run the script, or edit the hashbang line of the script to be:

```bash
#!/global/common/software/lsst/common/miniconda/current/envs/stack/bin/python
```

### Use the latest version of GCRCatalogs

If you need to use a newer version of `GCRCatalogs` than the one installed in the DESC Python environment,
here's what you need to do:

1. Clone this repo (on a NERSC machine):
   ```bash
   git clone git@github.com:LSSTDESC/gcr-catalogs.git
   ```
   (Note that if you want to use a PR, you need to clone the corresponding branch.)

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

- See [this notebook](examples/CompositeReader%20example.ipynb) for a example of using the composite catalog feature.

- See [this notebook](examples/CLF%20Test.ipynb) for an actual application (the Conditional Luminosity Function test) using GCR Catalogs. (Thanks to Joe DeRose for providing the CLF test example!)

- You can find more tutorial notebooks that use `GCRCatalogs` in [`LSSTDESC/DC2-analysis`](https://github.com/LSSTDESC/DC2-analysis/tree/master/tutorials).

- See also the [GCR documentation](https://yymao.github.io/generic-catalog-reader/) for the complete GCR API.

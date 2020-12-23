# GCR Catalogs

[![Conda Version](https://img.shields.io/conda/vn/conda-forge/lsstdesc-gcr-catalogs.svg)](https://anaconda.org/conda-forge/lsstdesc-gcr-catalogs)
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

Below is a list of most-used catalogs. To find a complete, most up-to-date list of all available catalogs,
run the following code:

```python
import GCRCatalogs

# List all catalogs that are recommended for general comsumption
GCRCatalogs.get_available_catalogs(names_only=True)

# List all catalogs, including those may not be intended for general comsumption
GCRCatalogs.get_available_catalogs(include_default_only=False, names_only=True)

# List all catalogs whose names contain the word "object"
GCRCatalogs.get_available_catalogs(include_default_only=False, names_only=True, name_contains="object")

# List all catalogs whose names start with the word "buzzard"
GCRCatalogs.get_available_catalogs(include_default_only=False, names_only=True, name_startswith="buzzard")
```

(*Note*: remove `False` in the above line to only see recommended catalogs.)

Each catalog is specified by a YAML config file,
which can be found [here](GCRCatalogs/catalog_configs).

You can also find an overview and more detailed description of all the data
products of DESC Data Challenge 2 at the
["DC2 Data Product Overview"](https://confluence.slac.stanford.edu/x/oJgHDg)
Confluence page (*DESC member only*).

### Extragalactic Catalogs and Add-ons

#### cosmoDC2

*by Andrew Benson, Andrew Hearin, Katrin Heitmann, Danila Korytov, Eve Kovacs, Patricia Larsen et al.*

- `cosmoDC2_v1.1.4_image`: latest cosmoDC2 catalog (used for Run 2.1+)
- `cosmoDC2_v1.1.4_small`: 17 contiguous healpixels of `cosmoDC2_v1.1.4_image` for testing purpose
- `cosmoDC2_v1.1.4_redmapper_v0.5.7`: Redmapper catalog (v0.5.7) for `cosmoDC2_v1.1.4_image` (provided by Eli Rykoff).
- `cosmoDC2_v1.1.4_image_with_photozs_v1` and `cosmoDC2_v1.1.4_small_with_photozs_v1`: containing photo-z for cosmoDC2 v1.1.4 (provided by Sam Schmidt)
- `cosmoDC2_v1.1.4_image_with_photoz_calib` and `cosmoDC2_v1.1.4_small_with_photoz_calib`: containing columns that identify DESI-like QSOs, LRGs, ELGs, or a magnitude limited sample in cosmoDC2 v1.1.4 (provided by Chris Morrison)

#### protoDC2

*by Andrew Benson, Andrew Hearin, Katrin Heitmann, Danila Korytov, Eve Kovacs, Patricia Larsen et al.*

- `protoDC2`: full catalog
- `protoDC2_test`: same as `protoDC2` but this one skips time-consuming md5 check
- `proto-dc2_vX.X_test.yaml`: some other versions of the protoDC2 catalog

#### Buzzard

*by Joe DeRose, Risa Wechsler, Eli Rykoff et al.*

- `buzzard`: full catalog, DES Y3 area
- `buzzard_test`: same as `buzzard` but a small subset for testing purpose / faster access
- `buzzard_high-res`: higher resolution, smaller sky area
- `buzzard_v2.0.0_x`: different realizations of the version of the `buzzard` catalog documented in [arXiv:1901.02401](https://arxiv.org/abs/1901.02401).

### DC2 Runs Data Products and Add-ons

*by LSST DESC, compiled by the DC2 Team*

#### Run 2.2 Object Catalogs

##### DR6 WFD (up to Year 5)

- `dc2_object_run2.2i_dr6`: static object catalog for Run 2.2i DR6 (WFD and DDF visits)
  (Note: a small sky region in the upper right corner of the footprint was excluded in the current version (v1))
- `dc2_object_run2.2i_dr6_with_addons`: same as `dc2_object_run2.2i_dr6` but with all available add-on catalogs
  (Note: currently available add-ons include metacal and truth-match. Photo-z add-on not yet available for DR6; use `dc2_object_run2.2i_dr6a_with_photoz` for a preview.)

##### DR2 (up to Year 1)

- `dc2_object_run2.2i_dr2_wfd`: static object catalog for Run2.2i DR2 WFD
- `dc2_object_run2.2i_dr2_wfd_with_addons`: same as `dc2_object_run2.2i_dr2_wfd` but with all available add-on catalogs
  (Note: currently only truth-match add-on is available; metacal, photo-z not yet available for DR2 WFD.)

##### DR3  (up to Year 2)

Note: DR3 processing is not fully completed; a few tracts are missing. Here `dr3a` is a preview of DR3.

- `dc2_object_run2.2i_dr3a`: static object catalog for Run 2.2i DR3 (preview)
- `dc2_object_run2.2i_dr3a_with_metacal`: `dc2_object_run2.2i_dr3a` + metacal (preview; missing more tracts)
- `dc2_object_run2.2i_dr3a_with_photoz`: `dc2_object_run2.2i_dr3a` + photo-z (preview)

#### Run 2.2 Truth Catalogs

- `dc2_truth_run2.2i_summary_tract_partition`: combined truth summary table (galaxies, stars, SNe); partitioned in tracts.
- `dc2_truth_run2.2i_galaxy_truth_summary`: galaxy truth summary table, partitioned in healpixels as cosmoDC2.
- `dc2_truth_run2.2i_sn_truth_summary`: SN truth summary table.
- `dc2_truth_run2.2i_sn_variability_truth`: SN variable truth information.
- `dc2_truth_run2.2i_star_lc_stats`: star light curve statistics.
- `dc2_truth_run2.2i_star_truth_summary`: star truth summary table.
- `dc2_truth_run2.2i_star_variability_truth`: star variable truth information.

#### Run 1.2 Object Catalogs

- `dc2_object_run1.2i`: static object catalog for Run 1.2i (with only DPDD columns and native columns needed for the DPDD columns)
- `dc2_object_run1.2i_with_photoz`: same as `dc2_object_run1.2i` but with photo-z's (columns that start with `photoz_`). Photo-z provided by Sam Schmidt.
- `dc2_object_run1.2i_all_columns`: static object catalog for Run 1.2i (with DPDD and all native columns, slower to access)
- `dc2_object_run1.2i_tract4850`, `dc2_object_run1.2i_tract5063`: same as `dc2_object_run1.2i_all_columns` but only has one tract for testing purpose / faster access
- `dc2_object_run1.2p`: static object catalog for Run 1.2p (with only DPDD columns and native columns needed for the DPDD columns)
- `dc2_object_run1.2p_all_columns`: static object catalog for Run 1.2p (with DPDD and all native columns, slower to access)
- `dc2_object_run1.2p_tract4850`: same as `dc2_object_run1.2p_all_columns` but only has one tract (4850)for testing purpose / faster access

#### Run 1.2 Truth Catalogs

- `dc2_truth_run1.2_static`: truth catalog for Run 1.2 (static objects only, corresponds to `proto-dc2_v3.0`)
- `dc2_truth_run1.2_variable_lightcurve`: light curves of variable objects in the truth catalog for Run 1.2
- `dc2_truth_run1.2_variable_summary`: summary table of variable objects in the truth catalog for Run 1.2

#### Run 1.2 DIA Source Catalogs

- `dc2_dia_source_run1.2p_test`: DIASource Table catalog for a test DIA processing of Tract+Paptch 4849+6,6 for Run 1.2p (with only DPDD columns and native columns needed for the DPDD columns).

#### Run 1.2 Forced Source Catalogs

- `dc2_forced_source_run1.2p`: Forced Source Table catalog for Run 1.2p (with only DPDD columns and native columns needed for the DPDD columns).  This is the forced-position photometry based on the positions in the Object Table.

#### Run 1.2 Source Catalogs

- `dc2_source_run1.2i`: Source Table catalog for Run 1.2i (with only DPDD columns and native columns needed for the DPDD columns)

#### Run 1.2 e-images

- `dc2_eimages_run1.2i_visit-181898`: one visit of e-images for Run 1.2i
- `dc2_eimages_run1.2p_visit-181898`: one visit of e-images for Run 1.2p

## Use GCRCatalogs at NERSC

Here's the instruction of using `GCRCatalogs` at NERSC.
All catalogs that are available in `GCRCatalogs` are all physically located at NERSC.
Note that you need to be in the `lsst` user group to access them.
You can find instructions about getting NERSC account and joining `lsst` group
at [this Confluence page](https://confluence.slac.stanford.edu/x/mgRTD)
(*DESC members only*).

### With Jupyter notebooks

It is recommended that you first install DESC-specific kernels for your
NERSC jupyter environment (*you only need to do this once*).
To do so, log in to cori.nersc.gov and run:
```bash
source /global/common/software/lsst/common/miniconda/kernels/setup.sh
```
Detailed instructions can also be found at [this Confluence page](https://confluence.slac.stanford.edu/x/1_ubDQ)
(*DESC members only*).

Then, you can [start a NERSC notebook server](https://jupyter.nersc.gov)
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

### In a terminal or in a Python script

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
print(GCRCatalogs.get_available_catalogs(names_only=True))

# load a catalog
catalog = GCRCatalogs.load_catalog('protoDC2')

# load a catalog with runtime custom options
# (one needs to check catalog configs to know the keywords)
catalog = GCRCatalogs.load_catalog('cosmoDC2_v1.1.4_image', config_overwrite={'healpix_pixels': [8786, 8787, 8788]})
catalog = GCRCatalogs.load_catalog('dc2_object_run2.2i_dr6', config_overwrite={'tracts': [3638, 3639, 3640])

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

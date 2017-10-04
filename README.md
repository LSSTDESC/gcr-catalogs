# GCR Catalogs

This repo hosts the mock galaxy catalogs used by [DESCQA2](https://github.com/LSSTDESC/descqa).

On a NERSC machine, all these catalogs can be directly accessed through the "Generic Catalog Reader" (GCR) inferface.
More information about GCR can be found [here](https://github.com/yymao/generic-catalog-reader).

Currently these catalogs are available (more to come):

1. Proto-DC2 (AlphaQ) (**NOT READY YET**): `proto-dc2-v1.0` (full catalog) and `proto-dc2-clusters-v1.0` (clusters only) by Eve Kovacs, Danila Korytov, Andrew Benson, Katrin Heitmann et al. 
2. Buzzard series: `buzzard_v1.6` (and different realizations: `buzzard_v1.6_1`, `buzzard_v1.6_2`, `buzzard_v1.6_3`, `buzzard_v1.6_5`, `buzzard_v1.6_21`, `buzzard_v1.6_21`),  `buzzard_v1.5`, `buzzard_high-res_v1.1` by Joe DeRose, Risa Wechsler, Eli Rykoff et al. (Note: high-res reader has not been fully implemented yet. For now only native quantities work for high-res.)
3. DC1 catalog: `dc1`

Each of the catalogs is specified by a YAML config file, which can be found [here](https://github.com/LSSTDESC/gcr-catalogs/tree/master/GCRCatalogs/catalog_configs). The galaxy quantities in these catalogs conform to [this schema](https://docs.google.com/document/d/1rUsImkBkjjw82Xa_-3a8VMV6K9aYJ8mXioaRhz0JoqI/edit).


## Use DESCQA Python envoirnment

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


### with a python script: 

To be able to import `GCRCatalogs`, the first line of the script should be:

    #!/global/common/cori/contrib/lsst/apps/anaconda/py2-envs/DESCQA/bin/python 


## Getting latest version of GCRCatalogs

You can install the latest version by running (but note that you need to change the python paths accordingly) 

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



## Contribute to GCRCatalogs:

1. On GitHub [Fork](https://guides.github.com/activities/forking/) the GCRCatalogs GitHub repo.
2. On NERSC

       cd /your/own/directory
       git clone git@github.com:YourGitHubUsername/gcr-catalogs.git

3. Make changes
4. Test by adding your clone to the path when running Python: 
   ```python
   import sys
   sys.path.insert(0, '/your/own/directory/gcr-catalogs')
   ```
5. Commit and create pull requests

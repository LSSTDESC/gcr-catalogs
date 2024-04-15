# Contributing to GCRCatalogs

## Preparing catalog files

Consider the following when you prepare the catalog files that you plan to add to `GCRCatalogs`. 

- File format: While GCRCatalogs can support any file format,
  we strongly recoommend that the files are stored in the Apache Parquet format.
  Both astropy and pandas support reading and writing Parquet files.
- File partition: For large data sets, the files should be partitioned to enable parallel access.
  Most commonly we partition the data by sky areas, but the choice of course would depend on the specific data content.  
- Data schema: Make sure the schema (including column names, types, and units) are in the same schema
  that the users should be using (that is, no further transformation of column names, types, and units would be needed). 

Once you have your data files ready, the data files should be copied to a specific location on NERSC
that all DESC members can access. 
You can do that by opening an issue at https://github.com/LSSTDESC/desc-help/issues. 
After your data files are copied, note the location as you will need it when specifying the catalog config (see below).

## Preparing a catalog reader

If you are writing a new reader, please see this [guide](https://github.com/yymao/generic-catalog-reader#usage)
for an overview and an example of a minimal reader.
The guide will explain that your reader must be a subclass of the `BaseGenericCatalog` parent class
and that you will need to supply a minimum of 3 methods to specify how to read in the underlying file.

The best practice is to ensure the schema (including column names, types, and units) of your data files
is identical to what you expect the users will be using. 
However, if really needed, you can also supply a translation dictionary between the native quantities in your
catalog and the quantities that are presented to the user via the `GCRCatalogs` interface.

You may want to look at existing readers in this repository as additional examples.

## Preparing a catalog config

Each catalog is represented by one yaml configuration file, placed in the `catalog_configs`
subdirectory for `GCRCatalogs`.

The filename of the yaml config file is the catalog name. Catalog names are treated in a case-insensitive fashion.
Config files that start with an underscore `_` will be ignored.

Each yaml config file should specify the reader class to use and all input arguments to be supplied to the reader class.
For example, if the reader class asks for `catalog_root_dir` as an input argument to specify the location of the
catalog files, you need to include `catalog_root_dir` as a keyword in the corresponding yaml config file,
and set it to the correct location.

All keywords in the yaml config file will be passed to the reader class.

Below is a list of required, recommended, or reserved keywords that may appear in a yaml config file.

### Required keywords

```yaml
subclass_name: <reader_module_name>.<ReaderClassName>
```

`subclass_name` should always be set to indicate the reader, _except_ when the following keywords are present:

- `alias`, `is_pseudo_entry`: `subclass_name` will be ignored
- `based_on`:  `subclass_name` is not required but will be used if supplied.

See the "Reserved Keywords" section below for more information on these keywords.

### Location keywords

Tyically, the location of the file (or the directory where the files are stored) is specified by one of the following keywords:
`base_dir`, `catalog_root_dir`, `filename` (there are a few other possiblities for historic reasons). 
You should use the keyword that is consistent with what is implemented in the reader. 

When specifying the path for the location keyword, the path should always start with `^/`, where `^` represents the 
top level of the shared directory. You can find what `^` will be translated to in 
[`site_rootdir.yaml`](https://github.com/LSSTDESC/gcr-catalogs/blob/master/GCRCatalogs/site_config/site_rootdir.yaml). 

### Recommended keywords

```yaml
creators: "Creator Name 1", "Creator Name 2", "Creator Name 3"
description: "A short, human-readable description of this specific catalog."
```

These keywords are for documentation purpose. They should be self-explanatory.

### Reserved keywords

```yaml
alias: another_catalog_name
based_on: another_catalog_name

include_in_default_catalog_list: true
addon_for: another_catalog_name
deprecated: "A short deprecation message."
is_pseudo_entry: true
public_release: v1, v2
```

The first two keywords allow you to reference another catalog:

- When `alias` is set, this yaml file will act as an alias to `another_catalog_name`, and all other keywords in this config will be ignored.
- When `based_on` is set, this yaml file will inherit the config content of `another_catalog_name`. All other keywords present in this config will _overwrite_ the inherited content.

The rest are mainly for documentation/informational purpose:

- `include_in_default_catalog_list` should _only_ be set to indicate the catalog is recommended for general comsuption. Catalogs with this keyword will show up in the recommended catalog list.
- `addon_for` should _only_ be set to indicate that the catalog is intended to be used _only_ as an addon catalog for `another_catalog_name`, and is not for standalone use. Note that setting this keyword does not prohibit users from loading this catalog.
- `deprecated` should _only_ be set to indicate that the catalog has been deprecated and should no longer be used. Deprecation message can include alternative catalogs that the users may use. Note that setting this keyword does not prohibit users from loading this catalog.
- `is_pseudo_entry` should _only_ be set to indicate that the config is a pseudo entry (i.e., not intended to be loaded via GCR; no reader required). Pseudo entries will by default be ignored by the register.
- `public_release` should _only_ be set to indicate that the config is a public release entry. It can be set to a string or a list of strings.

## GitHub workflow

1. Request to join the
   [LSSTDESC/gcr-catalogs-developers](https://github.com/orgs/LSSTDESC/teams/gcr-catalogs-developers/members) team
   if you are not already on it.
   Being on the team allows you to create branches.
   However, you can still contribute to this repo by [creating a fork](https://guides.github.com/activities/forking/).

2. Clone LSSTDESC/gcr-catalogs (or your fork). You can skip this step if you've done it.

3. Sync with the upstream master branch (**always do this step!**)

   ```bash
   cd /your/own/directory/gcr-catalogs

   # If you are working with LSSTDESC/gcr-catalogs
   git checkout master
   git pull

   # If you are working with your fork
   git remote add upstream https://github.com/LSSTDESC/gcr-catalogs.git
   git pull upstream master
   git push origin master
   ```

4. Create a new branch for this edit:

   ```bash
   git checkout -b u/user/short-description master
   ```

5. Make changes as needed.

6. Test by adding your clone to the path when running Python/Jupyter:

   ```python
   import sys
   sys.path.insert(0, '/your/own/directory/gcr-catalogs')
   ```

   You should also run `pytest --no-catalog` for a minimal set of tests.
   Note that if `--no-catalog` option is omitted, a full test run will start, which will take a few hours.

7. Commit and push to your forked repo

   ```bash
   git add <files changed>
   git commit -m <short but meaningful message>
   git push origin u/user/short-description
   ```

8. Go to GitHub and "create a pull request".

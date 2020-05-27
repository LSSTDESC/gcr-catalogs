# Contributing to GCRCatalogs

## Preparing a catalog reader

If you are writing a new reader, please see this [guide](https://github.com/yymao/generic-catalog-reader#usage)
for an overview and an example of a minimal reader.
The guide will explain that your reader must be a subclass of the `BaseGenericCatalog` parent class
and that you will need to supply a minimum of 3 methods to specify how to read in the underlying file.
You can also supply a translation dictionary between the native quantities in your
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

```yaml
# Required keywords
subclass_name: <reader_module_name>.<ReaderClassName>  # Indicate which reader to use.

# Recommended keywords
creators: ["Creator Name 1", "Creator Name 2", "Creator Name 3"]
description: "A short, human-readable description of this specific catalog."

# Reserved keyword
alias: another_catalog_name  # When set, this yaml file will act as an alias to another_catalog_name.
                             # All other keywords in this config will be ignored.
based_on: another_catalog_name  # When set, this yaml file will inherit the config content of another_catalog_name.
                                # All other keywords in this config will overwrite the inherited content.
include_in_default_catalog_list: true  # When set, this catalog will show up in the "recommended" catalog list.
                                       # Only catalogs that are intended for general comsuption should set this keyword.
addon_for: another_catalog_name  # Set this keyword to indicate that this catalog is intended to be used ONLY as
                                 # an addon catalog for another_catalog_name, and is not for standalone use.
                                 # Note that setting this keyword does not prohibit users from load this catalog.
deprecated: "A short deprecation message."  # Set this keyword if this catalog has been deprecated and should
                                            # no longer be used.
                                            # Setting this keyword does not prohibit users from load this catalog.
is_pseudo_entry: true  # Set if this config is an pseudo entry and should be ignored by the register.
```

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

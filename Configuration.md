# GCR Catalogs Configuration

GCRCatalogs has several configuration parameters.  For most users
default settings will be appropriate, but some may need more control.
Those parameters and how to modify them are described below.

## Site

Defaults for certain other parameters are dependent on where you're running.
Currently recognized sites in the GCRCatalogs sense are "nersc", "in2p3"
and "nersc_public". If you are running at NERSC, GCRCatalogs will detect that
and use the value 'nersc'.

### How and When to Set Site

You may set site explicitly by giving the
environment variable `DESC_GCR_SITE` one of the allowed values.
This is likely necessary if you are either running at in2p3 or are
running at NERSC but want to access only the publicly released catalogs.
If none of the standard site values are appropriate, you'll need to set
values independently for the configuration parameters described in remaining
sections.

## Root Directory

Production catalog datasets are stored in a hierarchy under a dedicated
protected directory at the site.  Within the catalog metadata the path
to the data is given relative to the root directory.  Hence to access the
data one must know the location of the root directory in the local file
system. By default that value is determined from the site, however there
are a couple ways to set a value explicitly for the root directory if
the per-site default is not what you need:

- It can be set from Python code (`GCRCatalogs.set_root_dir`)
- It can be set from a previously-written user config file.
  See the docstring for the class `RootDirManager` for details

## Catalog Config Source

GCRCatalogs accesses production catalog data by keying off the catalog name
to discover the metadata needed to read the associated dataset. That metadata
has traditionally been stored in catalog config files in a directory of
the `gcr-catalogs` package.  The same information is now also stored
in the DESC Data Registry database. GCRCatalogs needs to know whether to
use the files or the Data Registry as the source of this metadata. By
default GCRCatalogs will use the site to determine a value, currently
"dataregistry" when the site is "nersc" and "files" otherwise. One
may override this value by

- setting the environment variable `GCR_CONFIG_SOURCE` to the desired
  value before using GCRCatalogs
- from within Python invoking `GCRCatalogs.ConfigSource.set_config_source()`
  (in order to use files) or
  `GCRCatalogs.ConfigSource.set_config_source(dr=True)`
  to use the Data Registry
or "files"

"""
This script uses CatSim to produce a PhoSim InstanceCatalog
based on data provided by the GCR interface to the
proto-dc2 simulation
"""

import numpy as np
import os

############################################################
# connect to OpSim simulation to get a realistic observation

# point this to whatever OpSim simulated cadence you have
# available
opsim_db = os.path.join('/global', 'cscratch1', 'sd', 'danielsf',
                        'OpSimData',
                        'minion_1016_sqlite_new_dithers.db')

from lsst.sims.catUtils.utils import ObservationMetaDataGenerator

obs_gen = ObservationMetaDataGenerator(opsim_db)

# The boundLength kwarg controls the radius of the field of
# view in degrees.  If not defined, we default to 1.75,
# which is the nominal value for LSST
obs_list = obs_gen.getObservationMetaData(fieldRA=(-2.0,2.0),
                                          fieldDec=(-2.0, 2.0),
                                          boundLength=0.1)

if len(obs_list) == 0:
    raise RuntimeError("No valid observations found")

obs = obs_list[0]


############################################
# establish connection to the DESCQA catalog

from GCRCatalogs import bulgeDESCQAObject, diskDESCQAObject

cat_file = 'proto-dc2_v2.0'
db_bulge = bulgeDESCQAObject(cat_file)
db_disk = diskDESCQAObject(cat_file)

############################
# actually write the catalog

from GCRCatalogs import PhoSimDESCQA
from lsst.sims.catUtils.exampleCatalogDefinitions import DefaultPhoSimHeaderMap

cat_name = 'phosim_cat.txt'

# first, query the catalog for bulges
cat = PhoSimDESCQA(db_bulge, obs_metadata=obs, cannot_be_null=['hasBulge'])
cat.phoSimHeaderMap = DefaultPhoSimHeaderMap
cat.write_catalog(cat_name, chunk_size=100000)

# then, query the catalog for disks, writing to the same output file
# by specifying write_mode='a' and write_header=False
cat = PhoSimDESCQA(db_disk, obs_metadata=obs, cannot_be_null=['hasDisk'])
cat.write_catalog(cat_name, chunk_size=100000,
                  write_mode='a', write_header=False)

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

from GCRCatalogs import DESCQAObject
from lsst.sims.utils import radiansFromArcsec

def deg_to_radians(x):
    return np.radians(x).astype(np.float)

def arcsec_to_radians(x):
    return radiansFromArcsec(x).astype(np.float)

class bulgeDESCQAObject(DESCQAObject):
    epoch = 2000.0

    # PhoSim uniqueIds are generated by taking
    # source catalog uniqueIds, multiplying by
    # 1024, and adding objectTypeId.  This
    # components of the same galaxy to have
    # different uniqueIds, even though they
    # share a uniqueId in the source catalog
    objectTypeId = 77

    # this identifies the uniqueId column
    # in the source catalog
    idColKey = 'halo_id'

    # map the source catalog columns to CatSim
    # columns; each tuple is :
    #
    # (catsim_column_name,
    #  source_column_name,
    #  optional transformation to get from one to the other)
    columns = [('raJ2000', 'ra_true', deg_to_radians),
               ('decJ2000', 'dec_true', deg_to_radians),
               ('shear1', 'shear_1'),
               ('shear2', 'shear_2'),
               ('kappa', 'convergence'),
               ('redshift', 'redshift_true'),
               ('majorAxis', 'morphology/spheroidRadiusArcsec', arcsec_to_radians)]

    # default values that are applied if no other source
    # for a column can be found
    dbDefaultValues = {'sindex': 4.0}

class diskDESCQAObject(DESCQAObject):
    epoch = 2000.0
    objectTypeId = 87
    idColKey = 'halo_id'
    columns = [('raJ2000', 'ra_true', deg_to_radians),
               ('decJ2000', 'dec_true', deg_to_radians),
               ('shear1', 'shear_1'),
               ('shear2', 'shear_2'),
               ('kappa', 'convergence'),
               ('redshift', 'redshift_true'),
               ('majorAxis', 'morphology/diskRadiusArcsec', arcsec_to_radians)]

    dbDefaultValues = {'sindex': 1.0}


cat_file = 'proto-dc2_v2.0'
db_bulge = bulgeDESCQAObject(cat_file)
db_disk = diskDESCQAObject(cat_file)

#########################################################################
# define a class to write the PhoSim catalog; defining necessary defaults

from lsst.sims.catUtils.exampleCatalogDefinitions import PhoSimCatalogSersic2D
from lsst.sims.catalogs.decorators import cached, compound
from lsst.sims.catUtils.mixins import EBVmixin

class PhoSimDESCQA(PhoSimCatalogSersic2D, EBVmixin):

    # default values used if the database does not provide information
    default_columns = [('sedFilename', 'Inst.50E07.0005Z.spec.gz', str, 100),
                       ('raOffset', 0.0, float), ('decOffset', 0.0, float),
                       ('internalExtinctionModel', 'CCM', str, 3),
                       ('internalAv', 0.1, float),
                       ('internalRv', 3.1, float),
                       ('galacticExtinctionModel', 'CCM', str, 3),
                       ('galacticRv', 3.1, float)]

    # below are defined getter methods used to define CatSim value-added columns
    @cached
    def get_hasDisk(self):
        return np.where(self.column_by_name('morphology/diskRadiusArcsec')==0.0, None, 1.0)

    @cached
    def get_hasBulge(self):
        return np.where(self.column_by_name('morphology/spheroidRadiusArcsec')==0.0, None, 1.0)

    @cached
    def get_minorAxis(self):
        return 0.5*self.column_by_name('majorAxis')

    @cached
    def get_positionAngle(self):
        if not hasattr(self, '_pa_rng'):
            self._pa_rng = np.random.RandomState(88)
        ran = self._pa_rng.random_sample(len(self.column_by_name('raJ2000')))
        return ran*2.0*np.pi

    @cached
    def get_phoSimMagNorm(self):
        return self.column_by_name('mag_g_any')


############################
# actually write the catalog

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




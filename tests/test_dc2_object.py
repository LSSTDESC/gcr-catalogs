"""
Tests for DC2 Object Reader
"""
import os
import pytest
import numpy as np
from numpy.testing import assert_array_equal
import GCRCatalogs
GCRCatalogs.ConfigSource.set_config_source()

# pylint: disable=redefined-outer-name
@pytest.fixture(scope='module')
def load_dc2_catalog():
    """Convenience function to provide catalog"""
    this_dir = os.path.dirname(__file__)
    reader = 'dc2_object_run1.1p_tract4850'
    config = {'base_dir': os.path.join(this_dir, 'dc2_object_data'),
              'filename_pattern': 'test_object_tract_4850.hdf5'}
    return GCRCatalogs.load_catalog(reader, config)


def test_get_missing_column(load_dc2_catalog):
    """Verify that a missing column gets correct defaults.

    Uses just a local minimal HDF5 file and schema.yaml
    """
    gc = load_dc2_catalog

    empty_float_column_should_be_nan = gc['g_base_PsfFlux_flux']
    empty_int_column_should_be_neg1 = gc['g_parent']
    empty_bool_column_should_be_False = gc['g_base_SdssShape_flag']

    assert_array_equal(empty_float_column_should_be_nan,
                       np.repeat(np.nan, len(gc)))
    assert_array_equal(empty_int_column_should_be_neg1,
                       np.repeat(-1, len(gc)))
    assert_array_equal(empty_bool_column_should_be_False,
                       np.repeat(False, len(gc)))


def test_get_tract_patch(load_dc2_catalog):
    """Verify that we get tract, patch columns correctly.

    These are not originally stored as columns in the HDF5 files.
    They are added by the reader.
    So we want to test here that that actually works.
    """
    gc = load_dc2_catalog
    tract = 4850
    patch = '3,1'

    tract_col = gc['tract']
    patch_col = gc['patch']

    assert_array_equal(tract_col, np.repeat(tract, len(gc)))
    assert_array_equal(patch_col, np.repeat(patch, len(gc)))

import numpy as np
from numpy.testing import assert_array_equal
import pytest

import GCRCatalogs


@pytest.fixture(scope='module')
def load_dc2_catalog():
    reader = 'dc2_object_run1.1p_tract4850.yaml'
    config = {'base_dir': 'dc2_object_data',
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

"""
DC2 DM Catalog Reader

Read DC2 catalogs based off LSST Data Management (DM) Science Pipelines output
as extracted and reformatted as Parquet files.
Readers that provide access to DC2 DM data should inherit from this class.
"""

import math
import os
import re
import warnings

import numpy as np
import yaml
from GCR import BaseGenericCatalog
from .parquet import ParquetFileWrapper

from .utils import first, is_string_like

__all__ = ['DC2DMCatalog', 'DC2DMTractCatalog', 'DC2DMVisitCatalog']


#pylint: disable=C0103
def convert_flux_to_mag(flux, fluxmag0):
    """Convert calibrated flux to AB mag.
    """
    flux_nJ = convert_flux_to_nanoJansky(flux, fluxmag0)
    mag_AB = convert_nanoJansky_to_mag(flux_nJ)
    return mag_AB


#pylint: disable=C0103
def convert_nanoJansky_to_mag(flux):
    """Convert calibrated nanoJansky flux to AB mag.
    """
    #pylint: disable=C0103
    AB_mag_zp_wrt_Jansky = 8.90  # Definition of AB
    # 9 is from nano=10**(-9)
    #pylint: disable=C0103
    AB_mag_zp_wrt_nanoJansky = 2.5 * 9 + AB_mag_zp_wrt_Jansky

    return -2.5 * np.log10(flux) + AB_mag_zp_wrt_nanoJansky


#pylint: disable=C0103
def convert_flux_err_to_mag_err(flux, flux_err):
    """Convert flux and flux err to mag err.

    Assumes flux_err is symmetric.
    Uses instantaneous derivative.
    So a negative flux measurement (with a positive flux_err) will produce a finite, but negative mag_err.
    """
    return (2.5 / math.log(10)) * (flux_err / flux)


#pylint: disable=C0103
def convert_flux_to_nanoJansky(flux, fluxmag0):
    """Convert the listed DM coadd-reported flux values to nanoJansky.

    Based on the given fluxmag0 value, which is AB mag = 0.
    Eventually we will get nJy from the final calibrated DRP processing.
    """
    #pylint: disable=C0103
    AB_mag_zp_wrt_Jansky = 8.90  # Definition of AB
    # 9 is from nano=10**(-9)
    #pylint: disable=C0103
    AB_mag_zp_wrt_nanoJansky = 2.5 * 9 + AB_mag_zp_wrt_Jansky

    return 10**((AB_mag_zp_wrt_nanoJansky)/2.5) * flux / fluxmag0


def create_basic_flag_mask(*flags):
    """Generate a mask for a set of flags

    For each item the mask will be true if and only if all flags are false

    Args:
        *flags (ndarray): Variable number of arrays with booleans or equivalent

    Returns:
        The combined mask array
    """

    out = np.ones(len(flags[0]), bool)
    for flag in flags:
        out &= (~flag)

    return out


class DC2DMCatalog(BaseGenericCatalog):
    r"""DC2 Catalog reader

    Parameters
    ----------
    base_dir          (str): Directory of data files being served, required
    filename_pattern  (str): The optional regex pattern of served data files
    is_dpdd          (bool): File are already in DPDD-format.  No translation.

    Attributes
    ----------
    base_dir          (str): The directory of data files being served
    """
    # pylint: disable=too-many-instance-attributes

    FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    FILE_PATTERN = r'.+\.parquet$'
    META_PATH = None
    _default_pixel_scale = None

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self._filename_re = re.compile(kwargs.get('filename_pattern', self.FILE_PATTERN))

        if not os.path.isdir(self.base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self.base_dir))

        self._datasets = self._generate_datasets()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self.base_dir))

        self._columns = first(self._datasets).columns
        bands = kwargs.get("bands") or self._detect_available_bands()

        if kwargs.get('is_dpdd'):
            self._quantity_modifiers = {col: None for col in self._columns}
        else:
            quantity_modifiers_kwargs = dict()

            dm_schema_version = kwargs.get("dm_schema_version") or self._detect_dm_schema_version()
            quantity_modifiers_kwargs["dm_schema_version"] = dm_schema_version

            if bands:
                quantity_modifiers_kwargs["bands"] = list(bands)

            pixel_scale = kwargs.get("pixel_scale") or self._default_pixel_scale
            if pixel_scale:
                quantity_modifiers_kwargs["pixel_scale"] = float(pixel_scale)

            self._quantity_modifiers = self._generate_modifiers(**quantity_modifiers_kwargs)

        # meta_path in catalog config take precedence, otherwise use the class default value
        meta_path = kwargs.get("meta_path", self.META_PATH)
        if meta_path:
            meta_path = os.path.join(self.FILE_DIR, meta_path)  # for relative meta_path
            self._quantity_info_dict = self._generate_info_dict(meta_path, bands)
        else:
            self._quantity_info_dict = dict()

        self._len = None

    def _detect_dm_schema_version(self):
        if any(col.endswith('_fluxSigma') for col in self._columns):
            return 1
        if any(col.endswith('_fluxErr') for col in self._columns):
            return 2
        if any(col == 'base_Blendedness_abs_instFlux' for col in self._columns):
            return 3
        return 4

    def _detect_available_bands(self):
        """
        To be implemented by subclass. Should return a list of available filter names or None.
        """
        return

    @staticmethod
    def _generate_modifiers(**kwargs):  # pylint: disable=unused-argument
        """Creates a dictionary relating native and homogenized column names

        Returns:
            A dictionary of the form {<homogenized name>: <native name>, ...}
        """
        return dict()

    @staticmethod
    def _generate_info_dict(meta_path, bands=None):
        """Creates a 2d dictionary with information for each homogenized quantity

        Args:
            meta_path (path): Path of yaml config file with object meta data
            bands (list or None): A list of band names.
              They are used to replace the "<band>" place holders in
              quantity names and their descriptions.

        Returns:
            Dictionary of the form
                {<homonogized value (str)>: {<meta value (str)>: <meta data>}, ...}
        """

        with open(meta_path, 'r') as f:
            base_dict = yaml.safe_load(f)

        info_dict = dict()
        for q, info in base_dict.items():
            if not isinstance(info, dict):  # for backward compatibility
                info = dict(zip(("description", "unit", "in_GCRbase", "in_DPDD"), info))

            if bands and "<band>" in q:
                for band in bands:
                    info_dict[q.replace("<band>", band)] = {
                        k: v.replace("<band>", band) if is_string_like(v) else v for k, v in info.items()
                    }
            else:
                info_dict[q] = info

        return info_dict

    def _get_quantity_info_dict(self, quantity, default=None):
        """Return a dictionary with descriptive information for a quantity

        Returned information includes a quantity description, quantity units,
        whether the quantity is defined in the DPDD,
        and if the quantity is available in GCRbase.

        Args:
            quantity   (str): The quantity to return information for
            default (object): Value to return if no information is available (default None)

        Returns:
            A dictionary with information about the provided quantity
        """

        return self._quantity_info_dict.get(quantity, default)

    @staticmethod
    def _extract_dataset_info(filename): # pylint: disable=unused-argument
        """
        Should return a dict that contains infomation of each dataset
        that is parsed from the filename
        Should return None if no infomation need to be stored
        Should return False if this dataset needs to be skipped
        """

    @staticmethod
    def _sort_datasets(datasets):
        return datasets

    def _generate_datasets(self):
        """Return viable data sets from all files in self.base_dir

        Returns:
            A list of ObjectTableWrapper(<file path>, <key>) objects
            for all files and keys
        """
        datasets = list()
        for fname in os.listdir(self.base_dir):
            if not self._filename_re.match(fname):
                continue
            info = self._extract_dataset_info(fname)
            if info is False:
                continue
            file_path = os.path.join(self.base_dir, fname)
            datasets.append(ParquetFileWrapper(file_path, info))

        return self._sort_datasets(datasets)

    def _generate_native_quantity_list(self):
        """Return a set of native quantity names as strings"""
        return self._columns

    @staticmethod
    def _obtain_native_data_dict(native_quantities_needed, native_quantity_getter):
        """
        Overloading this so that we can query the database backend
        for multiple columns at once
        """
        return native_quantity_getter.read_columns(list(native_quantities_needed),
                                                   as_dict=True)

    def _iter_native_dataset(self, native_filters=None):
        for dataset in self._datasets:
            if (native_filters is not None and
                    not native_filters.check_scalar(dataset.info)):
                continue
            yield dataset

    def __len__(self):
        if self._len is None:
            # pylint: disable=attribute-defined-outside-init
            self._len = sum(len(dataset) for dataset in self._datasets)
        return self._len

    def close_all_file_handles(self):
        """Clear all cached file handles"""
        for dataset in self._datasets:
            dataset.close()


class DC2DMTractCatalog(DC2DMCatalog):
    _native_filter_quantities = {'tract'}
    FILE_PATTERN = r'.+_tract_?\d+\.parquet$'

    def _subclass_init(self, **kwargs):
        self._tracts = None
        if kwargs.get('tract') is not None and kwargs.get('tracts') is not None:
            raise ValueError('Conflict options (tract and tracts) defined')
        if kwargs.get('tract') is not None:
            self._tracts = [int(kwargs['tract'])]
        if kwargs.get('tracts') is not None:
            self._tracts = [int(t) for t in kwargs['tracts']]
        super()._subclass_init(**kwargs)

    def _extract_dataset_info(self, filename):
        match = re.search(r'tract_?(\d+)', filename)
        if match is None:
            warnings.warn('Filename {} does not contain tract info or not in correct format. Skipped')
            return False
        tract = int(match.groups()[0])
        if self._tracts and tract not in self._tracts:
            return False
        return {'tract': tract}

    def _sort_datasets(self, datasets):
        current_tracts = set(dataset.info['tract'] for dataset in datasets)
        if self._tracts and not all(t in current_tracts for t in self._tracts):
            warnings.warn('Not all tracts that were requested are loaded. Use `available_tracts` to see what tracts have been loaded.')
        return sorted(datasets, key=lambda d: d.info['tract'])

    @property
    def available_tracts(self):
        """Returns a sorted list of available tracts
        Returns:
            A sorted list of available tracts as integers
        """
        return [dataset.info['tract'] for dataset in self._datasets]


class DC2DMVisitCatalog(DC2DMCatalog):
    _native_filter_quantities = {'visit'}
    FILE_PATTERN = r'.+_visit_?\d+\.parquet$'

    def _subclass_init(self, **kwargs):
        self._visits = None
        if kwargs.get('visit') is not None and kwargs.get('visits') is not None:
            raise ValueError('Conflict options (visit and visits) defined')
        if kwargs.get('visit') is not None:
            self._visits = [int(kwargs['visit'])]
        if kwargs.get('visits') is not None:
            self._visits = [int(t) for t in kwargs['visits']]
        super()._subclass_init(**kwargs)

    def _extract_dataset_info(self, filename):
        match = re.search(r'visit_?(\d+)', filename)
        if match is None:
            warnings.warn('Filename {} does not contain visit info or not in correct format. Skipped')
            return False
        visit = int(match.groups()[0])
        if self._visits and visit not in self._visits:
            return False
        return {'visit': visit}

    def _sort_datasets(self, datasets):
        current_visits = set(dataset.info['visit'] for dataset in datasets)
        if self._visits and not all(v in current_visits for v in self._visits):
            warnings.warn('Not all visits that were requested are loaded. Use `available_tracts` to see what visits have been loaded.')
        return sorted(datasets, key=lambda d: d.info['visit'])

    @property
    def available_visits(self):
        """Returns a sorted list of available visits
        Returns:
            A sorted list of available visits as integers
        """
        return [dataset.info['visit'] for dataset in self._datasets]

"""
DC2 matched table reader

This reader was written by Eve Kovacs.
The reader ingests the matching table provided by Javier Sanchez
(fits file format). The tables are produced by matching objects in the DC2
object catalogs with objects in the cosmoDC2 catalog. Code can be found in
https://github.com/LSSTDESC/CatalogMatcher/blob/master/CatalogMatcher/match.py#L44
The complete script is available in
https://gist.github.com/fjaviersanchez/787bb5cd6b598226174e1cd9661465ca
"""

import os
import re
from functools import partial

import numpy.ma as ma
from astropy.io import fits

from GCR import BaseGenericCatalog

__all__ = ['DC2MatchedTable']

def _get_galaxy_mask(is_star, is_matched):
    return ~is_star & is_matched

def _get_star_mask(is_star, is_matched):
    return is_star & is_matched

def _get_galaxy_array(q, is_star, is_matched):
    mask = _get_galaxy_mask(is_star, is_matched)
    return ma.MaskedArray(q, mask=mask)

def _get_star_array(q, is_star, is_matched):
    mask = _get_star_mask(is_star, is_matched)
    return ma.MaskedArray(q, mask=mask)

class DC2MatchedTable(BaseGenericCatalog):

    def _subclass_init(self, **kwargs):

        """
        DC2MatchedTable reader, inherited from BaseGenericCatalog class
        """
        table_dir = kwargs.get('table_dir', None)
        table_filename_template = kwargs.get('table_filename_template', None)
        if not table_dir or not table_filename_template:
            print('Filename template and/or directory for matching table required')
            return
        self._data_release = kwargs.get('data_release', None)
        self._version = kwargs.get('version', '')
        if not self._data_release or not self._version:
            print('Data_release and/or version for matching table required')
            return

        filename_template = table_filename_template.format(self._version, self._data_release)
        self._use_tracts = bool(kwargs.get('tracts', None))
        self._files = self._get_file_list(table_dir, filename_template, tracts=self._use_tracts)
        if len(self._files) == 0:
            print("No files found matching template filename {}".format(filename_template))
            return
        self._truth_version = kwargs.get('truth_version', '')

        self._object_id = kwargs.get('object_id', 'objectId')
        self._truth_id = kwargs.get('truth_id', 'truthId')
        self._match_flag = kwargs.get('match_flag', 'is_matched')
        self._is_star = kwargs.get('is_star', 'is_star')

        # check matched table quantities
        self._column_names = self._check_files(self._files, object_id=self._object_id,
                                               truth_id=self._truth_id, match_flag=self._match_flag,
                                               is_star=self._is_star)
        self._native_quantities = self._generate_native_quantity_list()
        self._quantity_modifiers = self._generate_quantity_modifiers()

    def _generate_quantity_modifiers(self):
        # modify native quantities
        quantity_modifiers = {
            'galaxy_match_mask': (_get_galaxy_mask, self._is_star, self._match_flag),
            'star_match_mask':   (_get_star_mask, self._is_star, self._match_flag),
            'redshift_true_galaxy': (_get_galaxy_array, 'redshift_true', self._is_star, self._match_flag),
        }
        modified_quantity_list = [c for c in self._column_names if self._is_star not in c and self._match_flag not in c and 'redshift' not in c]
        for q in modified_quantity_list:
            quantity_modifiers[q + '_galaxy'] = (_get_galaxy_array, q, self._is_star, self._match_flag)
            quantity_modifiers[q + '_star'] = (_get_star_array, q, self._is_star, self._match_flag)

        return quantity_modifiers

    @staticmethod
    def _get_file_list(table_dir, filename_template, tracts=None):
        files = dict()
        fname_pattern = filename_template.format(r'(\d+)')

        nmatch = 0
        for f in sorted(os.listdir(table_dir)):
            m = re.match(fname_pattern, f)
            if m is None:
                continue

            if tracts:
                tract_this = int(m.groups()[0])
                if tract_this in tracts:
                    files[tract_this] = os.path.join(table_dir, f)
            else:
                files[str(nmatch)] = os.path.join(table_dir, f)
                nmatch += 1

        return files

    @staticmethod
    def _check_files(file_list, object_id='objectID', truth_id='truthID',
                     match_flag='match_flag', is_star='is_star'):
        colnames = []
        for f in file_list.values():
            with fits.open(f) as hdul:
                cols = list(hdul)[1].columns.names
                if object_id not in cols or match_flag not in cols or is_star not in cols or truth_id not in cols:
                    raise ValueError('Matching table {} does not have minimal expected columns'.format(f))
                if len(colnames) > 0 and cols.sort() != colnames.sort():
                    raise ValueError('Matching table {} has inconsistent data columns'.format(f))
                colnames = cols
        return colnames

    def _generate_native_quantity_list(self):
        return self._column_names

    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None and not self._use_tracts:
            raise ValueError("*native_filters* is not supported")

        for file_id, file_path in self._files.items():
            if (
                self._use_tracts and native_filters is not None and
                not native_filters.check_scalar({"tract": file_id})
            ):
                continue
            with fits.open(file_path) as hdul:
                handle = list(hdul)[1]
                yield partial(self._native_quantity_getter, handle=handle)

    @staticmethod
    def _native_quantity_getter(native_quantity, handle):
        return handle.data[native_quantity]

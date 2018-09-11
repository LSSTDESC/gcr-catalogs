"""
Add-on catalogs for CosmoDC2
These catalogs will assume the same native file structure as the master catalog
"""
import os
import h5py
from itertools import product
from GCR import BaseGenericCatalog
from .cosmodc2 import BaseDC2GalaxyCatalog

__all__ = ['CosmoDC2AddonCatalog']


class CosmoDC2AddonCatalog(BaseGenericCatalog):
    """
    Generic addon to the cosmoDC2 catalog based on HDF5 datasets saved assuming
    the same structure as the main catalog.
    """
    def _subclass_init(self, catalog_root_dir, catalog_filename_template, **kwargs):

        if not os.path.isdir(catalog_root_dir):
            raise ValueError('Catalog directory {} does not exist'.format(catalog_root_dir))

        self._addon_group = kwargs['addon_group']
        self._healpix_files = BaseDC2GalaxyCatalog._get_healpix_file_list(
            catalog_root_dir,
            catalog_filename_template,
            **kwargs
        )
        self._native_quantities = self._process_metadata(**kwargs)

    def _generate_native_quantity_list(self):
        return self._native_quantities

    def _process_metadata(self, ensure_quantity_consistent=False):
        native_quantities = None
        for (_, hpx_this), file_path in self._healpix_files.items():

            file_name = os.path.basename(file_path)
            with h5py.File(file_path, 'r') as fh:
                # get native quantities
                hgroup = fh[self._addon_group]
                hobjects = []
                #get all the names of objects in this tree
                hgroup.visit(hobjects.append)
                #filter out the group objects and keep the dataste objects
                hdatasets = [hobject for hobject in hobjects if type(hgroup[hobject]) == h5py.Dataset]
                addon_native_quantities = set(hdatasets)

                if native_quantities is None:
                    native_quantities = addon_native_quantities
                elif (ensure_quantity_consistent and
                      native_quantities != addon_native_quantities):
                    raise ValueError('native quantities are not consistent among different files')
                else:
                    break
        return native_quantities

    def _iter_native_dataset(self, native_filters=None):
        for (zlo_this, hpx_this), file_path in self._healpix_files.items():
            d = {'healpix_pixel': hpx_this, 'redshift_block_lower': zlo_this}
            if native_filters is not None and not native_filters.check_scalar(d):
                continue
            with h5py.File(file_path, 'r') as fh:
                def native_quantity_getter(native_quantity):
                    return fh['{}/{}'.format(self._addon_group, native_quantity)].value # pylint: disable=E1101
                yield native_quantity_getter

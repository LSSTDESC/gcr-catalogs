"""
DC1GalaxyCatalog by Andrew Hearin
"""
import os

from sqlalchemy import engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import numpy as np
from astropy.cosmology import FlatLambdaCDM

from GCR import BaseGenericCatalog


__all__ = ['DC1GalaxyCatalog']


class DC1GalaxyCatalog(BaseGenericCatalog):
    """
    DC1 galaxy catalog class.
    """
    
    native_filter_string_only = True

    def _subclass_init(self, **kwargs):

        db_url = engine.url.URL('mssql+pymssql', **self._read_database_info_from_file(kwargs['db_info_fname']))
        session_factory = sessionmaker(autoflush=True, bind=create_engine(db_url))
        self._Session = scoped_session(session_factory)

        self._quantity_modifiers = {
            'ra_true': 'ra',
            'dec_true': 'dec',
            'redshift_true': 'redshift',
            'galaxy_id': 'galid',
            'galaxy_id_disk': 'sedid_disk',
            'galaxy_id_bulge': 'sedid_bulge',
            'Mag_true_r_lsst_z0': 'absmag_r_total',
            'sersic_disk': 'disk_n',
            'sersic_bulge': 'bulge_n',
            'stellar_mass': 'mass_stellar',
            'size_disk_true': 'a_d',
            'size_minor_disk_true': 'b_d',
            'size_bulge_true': 'a_b',
            'size_minor_bulge_true': 'b_b',
        }

        self.cosmology = FlatLambdaCDM(Om0=0.25, Ob0=0.045, H0=73.)
        self.lightcone = True
        self.sky_area = float(kwargs.get('sky_area', np.nan))


    @staticmethod
    def _read_database_info_from_file(db_info_fname):
        msg = ("The file {0} does not exist.\n"
            "This file is used to access connectivity information to the DC1 database.")
        assert os.path.isfile(db_info_fname), msg

        try:
            with open(db_info_fname) as f:
                lines = f.readlines()
        except (IOError, OSError):
            info = tuple()
        else:
            info = tuple((l.strip() for l in lines[:5]))

        fields = ('host', 'port', 'database', 'username', 'password')

        if len(info) != len(fields) or not all(info):
            msg = 'File "{}" should be {} lines of ascii with the following information: {}'.format(db_info_fname, len(fields), ', '.join(fields))
            raise ValueError(msg)

        return dict(zip(fields, info))


    def _generate_native_quantity_list(self):
        session = self._Session()
        query = 'SELECT column_name FROM information_schema.columns WHERE table_name=\'galaxy\' ORDER BY ordinal_position;'
        return (r[0] for r in session.execute(query))


    def _iter_native_dataset(self, native_filters=None):
        session = self._Session()
        if native_filters:
            condition = 'WHERE ' + ' AND '.join(native_filters)
        else:
            condition = ''
        def native_quantity_getter(native_quantity):
            query = 'SELECT {} from galaxy {}'.format(native_quantity, condition)
            return np.array([r[0] for r in session.execute(query)])
        yield native_quantity_getter

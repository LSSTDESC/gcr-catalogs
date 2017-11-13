"""
DC1GalaxyCatalog by Andrew Hearin
"""
import os

from sqlalchemy import engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import numpy as np
from astropy.cosmology import FlatLambdaCDM

from GCR import BaseGenericCatalog
from .register import register_reader


__all__ = ['DC1GalaxyCatalog']


class DC1GalaxyCatalog(BaseGenericCatalog):
    """
    DC1 galaxy catalog class.
    """

    def _subclass_init(self, db_info_fname, **kwargs):

        db_url = engine.url.URL('mssql+pymssql', **self._read_database_info_from_file(db_info_fname))
        session_factory = sessionmaker(autoflush=True, bind=create_engine(db_url))
        self._Session = scoped_session(session_factory)

        self._quantity_modifiers = {
            'ra_true': 'ra',
            'dec_true': 'dec' ,
            'redshift_true': 'redshift',
            'galaxy_id': 'galid',
            'galaxy_id_disk': 'sedid_disk',
            'galaxy_id_bulge': 'sedid_bulge',
            'Mag_r_lsst_z0': 'absmag_r_total',
            'disk_sersic_index': 'disk_n',
            'bulge_sersic_index': 'bulge_n',
            'stellar_mass': 'mass_stellar',
            'disk_re_a_true': 'a_d',
            'disk_re_b_true': 'b_d',
            'bulge_re_a_true': 'a_b',
            'bulge_re_b_true': 'b_b',
        }

        self.cosmology = FlatLambdaCDM(Om0=0.25, Ob0=0.045, H0=73.)
        self.lightcone = True


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
            msg = "The file {0} should be {1} lines of ascii with the following information:\n{}\n".format(db_info_fname, len(fields), '\n'.join(fields))
            raise ValueError(msg)

        return dict(zip(fields, info))


    def _generate_native_quantity_list(self):
        session = self._Session()
        query = 'SELECT column_name FROM information_schema.columns WHERE table_name=\'galaxy\' ORDER BY ordinal_position;'
        return (r[0] for r in session.execute(query).fetchall())


    def _iter_native_dataset(self, native_filters=None):
        session = self._Session()
        def native_quantity_getter(native_quantity):
            query = 'SELECT {0} from galaxy'.format(native_quantity)
            return np.array([r[0] for r in session.execute(query).fetchall()])
        yield native_quantity_getter


register_reader(DC1GalaxyCatalog)

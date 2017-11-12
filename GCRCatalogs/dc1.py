"""
DC1GalaxyCatalog by Andrew Hearin
"""
import os
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.engine import url
from sqlalchemy import create_engine
import pymssql
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
        self.dbURL = url.URL('mssql+pymssql', \
                **self._read_database_info_from_file(db_info_fname))

        self.engine = create_engine(self.dbURL)

        self._quantity_modifiers = {
            'ra_true': 'ra',
            'dec_true': 'dec' ,
            'redshift_true': 'redshift',
            'galaxy_id': 'galid',
            'galaxy_id_disk': 'sedid_disk',
            'galaxy_id_bulge': 'sedid_bulge',
            'Mag_r_lsst_z0': 'absmag_r_total',
            'disk_Sersic_index': 'disk_n',
            'bulge_Sersic_index': 'bulge_n',
            'stellar_mass': 'mass_stellar',
            'disk_re_a_true': 'a_d',
            'disk_re_b_true': 'b_d',
            'bulge_re_a_true': 'a_b',
            'bulge_re_b_true': 'b_b'
            }

        self.cosmology = FlatLambdaCDM(Om0=0.25, Ob0=0.045, H0=73.)
        self.lightcone = True


    def _read_database_info_from_file(self, db_info_fname):
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
        """
        """
        session = scoped_session(sessionmaker(autoflush=True, bind=self.engine))
        query = "SELECT column_name FROM information_schema.columns WHERE table_name='galaxy' ORDER BY ordinal_position;"
        return [r[0] for r in session.execute(query).fetchall()]


    def _iter_native_dataset(self, native_filters=None):
        """
        """
        yield scoped_session(sessionmaker(autoflush=True, bind=self.engine))


    @staticmethod
    def _fetch_native_quantity(dataset, native_quantity, topN=None):
        """ runs query and returns numpy array
        """
        #  Write the query string
        if topN is None:
            query = 'SELECT {0} from galaxy'.format(native_quantity)
        else:
            try:
                topN = int(topN)
            except (ValueError, TypeError):
                raise ValueError("`topN` argument must be an integer")
            query = 'SELECT TOP {0} {1} from galaxy'.format(topN, native_quantity)

        #  Fetch the data as a list of strings
        results_list = [r[0] for r in dataset.execute(query).fetchall()]

        #  Convert to ndarray and return
        return np.array(results_list)


register_reader(DC1GalaxyCatalog)

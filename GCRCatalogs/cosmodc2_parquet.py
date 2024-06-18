"""
For parquet version of cosmoDC2 and skysim5000

The reader class CosmoDC2ParquetCatalog is the same as DC2TruthParquetCatalog
but with some metadata processing.
"""
from .cosmology import FlatLambdaCDM
from .dc2_truth_parquet import DC2TruthParquetCatalog

__all__ = ["CosmoDC2ParquetCatalog"]


class CosmoDC2ParquetCatalog(DC2TruthParquetCatalog):
    def _subclass_init(self, **kwargs):
        super()._subclass_init(**kwargs)

        self.lightcone = kwargs.get('lightcone', True)
        self.version = kwargs.get('version', '0.0.0')
        self.halo_mass_def = kwargs.get('halo_mass_def', 'FoF, b=0.168')

        self.cosmology = None
        if 'cosmology' in kwargs:
            self.cosmology = FlatLambdaCDM(**kwargs['cosmology'])

        self.sky_area = None
        if 'sky_area' in kwargs:
            self.sky_area = float(kwargs["sky_area"])

    @property
    def available_healpix_pixels(self):
        return sorted((d.info["healpix_pixel"] for d in self._datasets))

"""
define Cosmology class for GCRCatalogs
"""
import math
from collections import namedtuple

try:
    from astropy.cosmology import w0waCDM
    import astropy.units as u
except ImportError:
    _HAS_ASTROPY = False
else:
    _HAS_ASTROPY = True

try:
    import pyccl as ccl
except ImportError:
    _HAS_CCL = False
else:
    _HAS_CCL = True


__all__ = ['Cosmology']


# This is copied from pyccl.Parameters' call signature
# https://github.com/LSSTDESC/CCL/blob/master/pyccl/core.py#L63
_default_kwargs = dict(Omega_c=None, Omega_b=None, h=None, A_s=None, n_s=None,
                       Omega_k=0., N_nu_rel=3.046, N_nu_mass=0., m_nu=0.,w0=-1., wa=0.,
                       bcm_log10Mc=math.log10(1.2e14), bcm_etab=0.5, bcm_ks=55., sigma8=None,
                       z_mg=None, df_mg=None)


_Cosmology = namedtuple('Cosmology', list(_default_kwargs.keys()))
_Cosmology.__new__.__defaults__ = tuple(_default_kwargs.values())


class Cosmology(_Cosmology):
    """
    An object that stores cosmology parameters.
    It uses the pyccl.Parameters' call signature.
    See https://github.com/LSSTDESC/CCL/blob/master/pyccl/core.py#L63

    It has two member methods: `to_ccl` and `to_astropy`

    Parameters
    ----------
    Omega_c (float): Cold dark matter density fraction.
    Omega_b (float): Baryonic matter density fraction.
    h (float): Hubble constant divided by 100 km/s/Mpc; unitless.
    A_s (float): Power spectrum normalization. Optional if sigma8 is
                    specified.
    n_s (float): Primordial scalar perturbation spectral index.
    Omega_k (float, optional): Curvature density fraction. Defaults to 0.
    N_nu_rel (float, optional): Number of massless neutrinos present. Defaults to 3.046
    N_nu_mass (float, optional): Number of massive neutrinos present. Defaults to 0.
    m_nu (float, optional): total mass in eV of the massive neutrinos present (current must be equal mass). Defaults to 0.
    w0 (float, optional): First order term of dark energy equation of
                            state. Defaults to -1.
    wa (float, optional): Second order term of dark energy equation of
                            state. Defaults to 0.
    log10Mc (float, optional): One of the parameters of the BCM model.
    etab (float, optional): One of the parameters of the BCM model.
    ks (float, optional): One of the parameters of the BCM model.
    sigma8 (float): Variance of matter density perturbations at 8 Mpc/h
                    scale. Optional if A_s is specified.
    df_mg (:obj: array_like): Perturbations to the GR growth rate as a
                                function of redshift, Delta f. Used to
                                implement simple modified growth
                                scenarios.
    z_mg (:obj: array_like): Array of redshifts corresponding to df_mg.
    """
    __slots__ = ()

    def to_ccl(self):
        """
        Return pyccl.Cosmology instance.
        """
        if not _HAS_CCL:
            raise RuntimeError('CCL (pyccl) is not installed/avaiable.')
        return ccl.Cosmology(ccl.Parameters(**self._asdict()))

    def to_astropy(self):
        """
        Return a astropy.cosmology.FLRW instance.
        """
        if not _HAS_ASTROPY:
            raise RuntimeError('astropyis not installed/avaiable.')

        return w0waCDM(H0=self.h * 100.0, Om0=self.Omega_m, Ode0=self.Omega_de,
                       w0=self.w0, wa=self.wa, Tcmb0=self.T_CMB,
                       Neff=self.N_nu_eff, m_nu=self.m_nu*u.eV, Ob0=self.Omega_b)

    @property
    def Omega_m(self):
        return self.Omega_c + self.Omega_b

    @property
    def Omega_de(self):
        return 1.0 - self.Omega_c - self.Omega_b - self.Omega_k

    @property
    def T_CMB(self):
        return 2.725 #NOTE: currently hard coded in CCL. May change in the future.

    @property
    def N_nu_eff(self):
        return self.N_nu_rel + self.N_nu_mass

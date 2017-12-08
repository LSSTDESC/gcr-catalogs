from GCRCatalogs.cosmology import Cosmology

def test_cosmology():
    Omega_c = 0.28
    Omega_b = 0.045
    c = Cosmology(Omega_c=Omega_c, Omega_b=Omega_b, h=0.7)
    assert c.Omega_m == Omega_c + Omega_b
    assert c.Omega_de == 1.0 - Omega_c - Omega_b


def test_astropy_cosmology():
    Omega_c = 0.28
    Omega_b = 0.045
    c = Cosmology(Omega_c=Omega_c, Omega_b=Omega_b, h=0.7)
    c = c.to_astropy()
    assert c.H0.value == 70.0
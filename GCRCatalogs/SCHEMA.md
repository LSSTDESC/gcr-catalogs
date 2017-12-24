# Schema of GCR Catalogs as used in LSST DESC

## Metadata

Attribute name | Type | Definition
--- | --- | ---
`version` | `str` | catalog version
`cosmology` | `astropy.cosmology` | cosmology of the mock catalog
`halo_mass_def` | `str` | halo mass definition, e.g., `vir`, `200m`, `200c`
`lightcone` | `bool` | whether or not the catalog is a light cone catalog

## Galaxy properties

- Label names are generally in `lowercase_separated_by_underscores` format, except in a few cases an upper case letter is needed (e.g., `Mag_true_Y_lsst_z0`).
- Label names generally start with the name of the physical quantity, and are followed by specifications (i.e., use `size_disk_true` not `true_disk_size`). Some exceptions are `galaxy_id`, `halo_id`, `halo_mass`.
- A quantity with `_true` usually means before the lensing effect is taken into account.
- Not all quantities listed below are available in all catalogs. Use `list_all_quantities()` to find available quantities.
- In addition to the quantities listed below, there are also *native quantities*, which are quantities whose label names and/or units have not been homogenized and may change in the future. Nevertheless, one can still access native quantities via GCRCatalogs. Use `list_all_native_quantities()` to find available native quantities.

Quantity Label | Unit | Definition
--- | --- | ---
`galaxy_id` | - | Unique integer identifier
`ra` | degree | Right ascension, lensed
`ra_true` | degree | Right ascension, not lensed
`dec` | degree | Declination, lensed
`dec_true` | degree | Declination, not lensed
`redshift_true` | - | Cosmological redshift
`redshift` | - | Cosmological redshift with line-of-sight motion
`Mag_true_<band>_<filter>_z<z>` | - | Absolute magnitude, not lensed, in `<band>` with  `<filter>` and k-corrected to `<z>`, e.g., `Mag_true_Y_lsst_z0`, `Mag_true_g_des_z01`
`mag_<band>_<filter>_lsst` | - | Apparent magnitude, lensed, in `<band>` with  `<filter>`, e.g., `mag_Y_lsst`, `mag_g_des`
`magerr_<band>_<filter>_lsst` | - | Error in apparent magnitude in `<band>` with  `<filter>`, e.g., `magerr_Y_lsst`, `magerr_g_des`
`sersic` | - | Sersic index of galaxy light profile
`sersic_disk` | - | Sersic index of disk light profile
`sersic_bulge` | - | Sersic index of bulge light profile
`A_v` | - | Extinction in V-band
`R_v` | - | Ratio of total to selective extinction in B and V bands
`size` | arcsec | Galaxy half-light radius (of major axis), lensed
`size_true` | arcsec | Galaxy half-light radius (of major axis), not lensed
`size_disk_true` | arcsec | Disk half-light radius (of major axis), not lensed
`size_bulge_true` | arcsec | Bulge half-light radius (of major axis), not lensed
`ellipticity_1` | - | Ellipticity component 1, lensed
`ellipticity_2` | - | Ellipticity component 2, lensed
`ellipticity_1_true` | - | Ellipticity component 1, for galaxy, not lensed
`ellipticity_2_true` | - | Ellipticity component 2, for galaxy, not lensed
`ellipticity_1_disk_true` | - | Ellipticity component 1, for disk, not lensed
`ellipticity_2_disk_true` | - | Ellipticity component 2, for disk, not lensed
`ellipticity_1_bulge_true` | - | Ellipticity component 1, for bulge, not lensed
`ellipticity_2_bulge_true` | - | Ellipticity component 2, for bulge, not lensed
`shear_1` | - | Shear (gamma) component 1 *(sign convention to be supplied)*
`shear_2` | - | Shear (gamma) component 2 *(sign convention to be supplied)*
`convergence` | - | Convergence (kappa)
`magnification` | - | Magnification
`halo_id` | - | Unique ID of the main halo that contains the galaxy
`halo_mass` | M<sub>sun</sub> | Halo mass of the main halo that contains the galaxy
`stellar_mass` | M<sub>sun</sub> | Total stellar mass of the galaxy
`is_central` | *(bool)* | If the galaxy is the central galaxy of the main halo
`position_x` | Mpc | 3D position (x coordinate)
`position_y` | Mpc | 3D position (y coordinate)
`position_z` | Mpc | 3D position (z coordinate)
`velocity_x` | km/s | 3D velocity (x component)
`velocity_y` | km/s | 3D velocity (y component)
`velocity_z` | km/s | 3D velocity (z component)

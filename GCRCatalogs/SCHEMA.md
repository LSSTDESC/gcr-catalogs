# Schema of GCR Catalogs as used in LSST DESC

## Extragalactic Catalogs

### Metadata for Extragalactic Catalogs

Attribute name | Type | Definition
--- | --- | ---
`version` | `str` | catalog version
`cosmology` | `astropy.cosmology` | cosmology of the mock catalog
`halo_mass_def` | `str` | halo mass definition, e.g., `vir`, `200m`, `200c`
`lightcone` | `bool` | whether or not the catalog is a light cone catalog

### Schema for Extragalactic Catalogs

Columns names in extragalactic catalogs generally follow these rules:

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
`Mag_true_<band>_<filter>_z<z>` | - | Absolute magnitude, not lensed, in `<band>` with  `<filter>` and k-corrected to `<z>`, e.g., `Mag_true_Y_lsst_z0`, `Mag_true_g_des_z01`. In the case when postfix is `_z0`, it means rest-frame absolute magnitude.
`mag_true_<band>_<filter>` | - | Apparent magnitude, not lensed, in `<band>` with  `<filter>`, e.g., `mag_true_Y_lsst`, `mag_true_g_des`
`mag_<band>_<filter>` | - | Apparent magnitude, lensed, in `<band>` with  `<filter>`, e.g., `mag_Y_lsst`, `mag_g_des`
`magerr_<band>_<filter>` | - | Error in apparent magnitude in `<band>` with  `<filter>`, e.g., `magerr_Y_lsst`, `magerr_g_des`
`mag_<band>` | - | alias for `mag_<band>_lsst`
`mag_true_<band>` | - | alias for `mag_true_<band>_lsst`
`magerr_<band>` | - | alias for `magerr_<band>_lsst`
`sersic` | - | Sersic index of galaxy light profile
`sersic_disk` | - | Sersic index of disk light profile
`sersic_bulge` | - | Sersic index of bulge light profile
`A_v` | - | Extinction in V-band, for galaxy light profile
`A_v_disk` | - | Extinction in V-band, for disk light profile
`A_v_bulge` | - | Extinction in V-band, for bulge light profile
`R_v` | - | Ratio of total to selective extinction in B and V bands, for galaxy light profile
`R_v_disk` | - | Ratio of total to selective extinction in B and V bands, for disk light profile
`R_v_bulge` | - | Ratio of total to selective extinction in B and V bands, for bulge light profile
`size` | arcsec | Galaxy half-light radius (of major axis), lensed
`size_minor` | arcsec | Galaxy half-light radius (of minor axis), lensed
`size_true` | arcsec | Galaxy half-light radius (of major axis), not lensed
`size_minor_true` | arcsec | Galaxy half-light radius (of minor axis), not lensed
`size_disk_true` | arcsec | Disk half-light radius (of major axis), not lensed
`size_minor_disk_true` | arcsec | Disk half-light radius (of minor axis), not lensed
`size_bulge_true` | arcsec | Bulge half-light radius (of major axis), not lensed
`size_minor_bulge_true` | arcsec | Bulge half-light radius (of minor axis), not lensed
`position_angle` | deg | Position angle (arctan(E2/E1)), for galaxy, lensed
`position_angle_true` | deg | Position angle (arctan(E2/E1)), for galaxy, not lensed
`ellipticity` | - | Ellipticity (= sqrt(E1^2+E2^2) = (1-q)/(1+q)), for galaxy, lensed, where `q = size_minor/size`
`ellipticity_1` | - | Ellipticity component 1, for galaxy, lensed
`ellipticity_2` | - | Ellipticity component 2, for galaxy, lensed
`ellipticity_true` | - | Ellipticity (= sqrt(E1^2+E2^2) = (1-q)/(1+q)), for galaxy, not lensed, where `q = size_minor_true/size_true`
`ellipticity_1_true` | - | Ellipticity component 1, for galaxy, not lensed
`ellipticity_2_true` | - | Ellipticity component 2, for galaxy, not lensed
`ellipticity_disk_true` | - | Ellipticity (= sqrt(E1^2+E2^2) = (1-q)/(1+q)), for disk, not lensed, where `q = size_minor_disk_true/size_disk_true`
`ellipticity_1_disk_true` | - | Ellipticity component 1, for disk, not lensed
`ellipticity_2_disk_true` | - | Ellipticity component 2, for disk, not lensed
`ellipticity_bulge_true` | - | Ellipticity (= sqrt(E1^2+E2^2) = (1-q)/(1+q)), for bulge, not lensed, where `q = size_minor_bulge_true/size_bulge_true`
`ellipticity_1_bulge_true` | - | Ellipticity component 1, for bulge, not lensed
`ellipticity_2_bulge_true` | - | Ellipticity component 2, for bulge, not lensed
`shear_1` | - | Shear (gamma) component 1 in treecorr/GalSim convention
`shear_2` | - | Shear (gamma) component 2 in treecorr/GalSim convention
`shear_2_treecorr` | - | Shear (gamma) component 2 in treecorr/GalSim convention (`= shear_2`)
`shear_2_phosim` | - | Shear (gamma) component 2 in PhoSim convention (`= -shear_2`)
`convergence` | - | Convergence (kappa)
`magnification` | - | Magnification
`halo_id` | - | Unique ID of the main halo that contains the galaxy
`halo_mass` | M<sub>sun</sub> | Halo mass of the main halo that contains the galaxy
`stellar_mass` | M<sub>sun</sub> | Total stellar mass of the galaxy
`stellar_mass_disk` | M<sub>sun</sub> | Stellar mass of the disk component
`stellar_mass_bulge` | M<sub>sun</sub> | Stellar mass of the bulge component
`bulge_to_total_ratio_<band>` | - | bulge-to-total luminosity ratio in `<band>` (e.g., `bulge_to_total_ratio_i`)
`is_central` | *(bool)* | If the galaxy is the central galaxy of the main halo
`position_x` | Mpc | 3D position (x coordinate)
`position_y` | Mpc | 3D position (y coordinate)
`position_z` | Mpc | 3D position (z coordinate)
`velocity_x` | km/s | 3D velocity (x component)
`velocity_y` | km/s | 3D velocity (y component)
`velocity_z` | km/s | 3D velocity (z component)
`sed_<start>_<width>` | 4.4659e13 W/Hz | intergrated, rest-frame, AB luminosity of for a narrow tophat filter from `<start>` to `<start>` + `<width>` in Angstroms
`sed_<start>_<width>_disk` | 4.4659e13 W/Hz | same as `sed_<start>_<width>` but for disk
`sed_<start>_<width>_bulge` | 4.4659e13 W/Hz | same as `sed_<start>_<width>` but for bulge
`sed_<start>_<width>_no_host_extinction` | 4.4659e13 W/Hz | same as `sed_<start>_<width>` but without dust extiction in the host galaxy
`sed_<start>_<width>_disk_no_host_extinction` | 4.4659e13 W/Hz | same as `sed_<start>_<width>_no_host_extinction` but for disk
`sed_<start>_<width>_bulge_no_host_extinction` | 4.4659e13 W/Hz | same as `sed_<start>_<width>_no_host_extinction` but for bulge

## DC2 DPDD-like Catalogs

The schema for DC2 DPDD-like Catalogs (such as Object, Source, and Force Source Catalogs, as defined in [LDM-153](https://ls.st/LDM-153)),
generally follow these rules:

- For quantities that are defined in [LSST DPDD](https://lse-163.lsst.io/dpdd.pdf), we follow DPDD's naming scheme.
- For quantities that are defined in the above "Schema for Extragalactic Catalogs", we follow Extragalactic Catalogs' naming scheme ('GCRbase' below).
- For quantities that are defined in both, we provide aliases so both naming schemes would work.
- For quantities that are defined in neither and are newly defined for the coadd catalogs, we generally follow Extragalactic Catalogs' naming style.

In the tables below we list the name of the quantity, its units and definition and whether the name is defined in the GCRbase or DPDD. Note that

- Items marked with 'xx' are not exactly defined in the DPDD, but their name is taken from a related column in a different table.  E.g.
  * there is no `x`, `y` in the DPDD Object table, but these are called `x`, '`y` in the DPDD Source table.  We don't have `xyCov` so we separately list `xErr` and `yErr`.
  * `radec` is a pair in the DPDD, but we separate out into `ra`, `dec` here.
  * The DPDD says `psCov`, but we only have the diagonal terms, so we call it `psErr`.
- Quantities named with `x` or `y` are in the local coordinate system of the tract+patch.

### Schema for DC2 Object Catalogs

Object Catalog contains information about static astronomical objects measured on a stacked (coadd) image.

Quantity Label | Unit | Definition | GCRbase | DPDD
--- | --- | --- | --- | ---
`ra` | degree | Right Ascension | x | xx |
`ra_err` | degree | Right Ascension | x | xx |
`dec` | degree | Declination | x | xx |
`dec_err` | degree | Declination | x | xx |
`x` | pixels | 2D centroid location (x coordinate). |   | xx |
`y` | pixels | 2D centroid location (y coordinate). |   | xx |
`xErr` | pixels | Error value for `centroidX`. |   | xx |
`yErr` | pixels | Error value for `centroidY`. |   | xx |
`xy_flag` | - | Flag for issues with `x` and `y`. |   | xx |
`psFlux_<band>` | nJy | Point source model flux in `<band>.` |   | x |
`psFluxErr_<band>` | nJy | Error value for `psFlux_<band>`. |   | x |
`psFlux_flag_<band>` | - | Flag for issues with `psFlux_<band>`. |   | x |
`Ixx_<band>` | asec2 | Adaptive second moment of the source intensity in `<band>`. |   | x |
`Iyy_<band>` | asec2 | Adaptive second moment of the source intensity in `<band>`. |   | x |
`Ixy_<band>` | asec2 | Adaptive second moment of the source intensity in `<band>`. |   | x |
`IxxPSF_<band>` | asec2 | Adaptive second moment of the PSF  in `<band>`. |   | x |
`IyyPSF_<band>` | asec2 | Adaptive second moment of the PSF  in `<band>`. |   | x |
`IxyPSF_<band>` | asec2 | Adaptive second moment of the PSF  in `<band>`. |   | x |
`I_flag_<band>` | - | Flag for issues with `Ixx_<band>`, `Ixx_<band>`, and `Ixx_<band>.` |   | x |
`cModelFlux_<band>` | nJy | composite model (CModel) flux in `<band>` | x |  |
`cModelFluxErr_<band>` | nJy | Error value for cModel flux in `<band>` | x |  |
`cModelFlux_flag_<band>` | - | Flag for issues with `cModelFlux_flag_<band>` | x |  |
`mag_<band>_cModel` | mag | composite model (cModel) magnitude in `<band>`, fitted by cModel. | x |   |
`magerr_<band>_cModel` | mag | Error value for `mag_<band>_cModel.` | x |   |
`snr_<band>_cModel` | - | Signal to noise ratio for magnitude in `<band>`, fitted by cModel. |   |   |
`psf_fwhm_<band>` | asec | PSF FWHM calculated from 'base_SdssShape' |   |   |
`good` | - | True if the source has no flagged pixels. |   |   |
`clean` | - |  True if the source has no flagged pixels and is not skipped by the deblender (`good && ~deblend_skipped`). |   |   |
`I_flag` | - | Flag for issues with `Ixx`, `Iyy`, and `Ixy`. |   | xx |
`blendedness` | - | measure of how flux is affected by neighbors: (1 - flux.child/flux.parent) (see 4.9.11 of [1705.06766](https://arxiv.org/abs/1705.06766)) |   |   |
`extendedness` | - | 0:star, 1:extended.  DM Stack `base_ClassificationExtendedness_value` |   |   |

### Schema for DC2 Source and Forced Source Catalogs

Source Catalog contains information about high signal-to-noise detections on single frame images,

Forced Source Catalog contains photometry measurements about low signal-to-noise detections done on individual
exposures in each place where an object was detected on a stacked image.

Quantity Label | Unit | Definition | GCRbase | DPDD
--- | --- | --- | --- | ---
`ra` | degree | Right Ascension | x | xx |
`ra_err` | degree | Right Ascension | x | xx |
`dec` | degree | Declination | x | xx |
`dec_err` | degree | Declination | x | xx |
`x` | pixels | 2D centroid location (x coordinate). |   | xx |
`y` | pixels | 2D centroid location (y coordinate). |   | xx |
`xErr` | pixels | Error value for `centroidX`. |   | xx |
`yErr` | pixels | Error value for `centroidY`. |   | xx |
`xy_flag` | - | Flag for issues with `x` and `y`. |   | xx |
`psFlux` | nJy | Point source model flux. |   | x |
`psFluxErr` | nJy | Error value for `psFlux`. |   | x |
`psFlux_flag` | - | Flag for issues with `psFlux`. |   | x |
`Ixx` | asec2 | Adaptive second moment of the source intensity. |   | x |
`Iyy` | asec2 | Adaptive second moment of the source intensity. |   | x |
`Ixy` | asec2 | Adaptive second moment of the source intensity. |   | x |
`IxxPSF` | asec2 | Adaptive second moment of the PSF. |   | x |
`IyyPSF` | asec2 | Adaptive second moment of the PSF. |   | x |
`IxyPSF` | asec2 | Adaptive second moment of the PSF. |   | x |
`I_flag` | - | Flag for issues with `Ixx`, `Ixx`, and `Ixx.` |   | x |
`blendedness` | - | measure of how flux is affected by neighbors: (1 - flux.child/flux.parent) (see 4.9.11 of [1705.06766](https://arxiv.org/abs/1705.06766)) |   |   |
`extendedness` | - | 0:star, 1:extended.  DM Stack `base_ClassificationExtendedness_value` |   |   |

## DC2 Run 1.x truth catalogs

DC2 truth catalogs correspond to catalogs such that `dc2_truth_run1.1_static` or `dc2_truth_run1.2_static`. Definition of quantities can be accessed using `get_quantity_info`:

```python
cat = GCRCatalogs.load_catalog('dc2_truth_run1.2_static')
cat.get_quantity_info('healpix_2048')
# {'description': 'healpixel containing the object (nside=2048; nested)'}
```

Note that the availability and definition of native quantities in the DC2 truth catalogs are more likely to change than the ones defined in the DPDD-like object catalogs for example.

*************************************
Creation of test data for unittesting
*************************************

Create example netCDF file
==========================

This file is used to derive raster fileformat test data, but is not used
directly in the unittests.  Using ANTS 2.1 module::

  $ python
  >>> import ants
  >>> import ants.tests
  >>> cube = ants.tests.stock.geodetic((6, 3))
  >>> ants.io.save.netcdf(cube, 'example_data.nc')

Create GDAL raster test file
============================

Creates one file for two sets of tests.  So we initially create a file for the
first set of tests, then copy it to the expected location for the second set
of tests.

The ANTS environments do not include the libgdal dependencies needed for
working with netCDF or GeoTIFF data.  So we need a standalone environment::

  $ conda create --name gdal gdal libgdal
  $ conda activate gdal
  $ gdal_translate example_data.nc global_geodetic.tif
  $ cp global_geodetic.tif ./load_files/gdal_file

F03 ancil file with pseudo levels and equivalent PP file
========================================================

Using ANTS 2.1 module.  Does not rely on example netCDF file above::

  $ python
  >>> import ants
  >>> import ants.tests
  >>> import iris
  >>> pseudo_coord = iris.coords.AuxCoord(range(1, 10), long_name='pseudo_level')
  >>> cube = ants.tests.stock.geodetic((9, 3, 3))
  >>> cube.attributes['STASH'] = 'm01s00i001'
  >>> cube.attributes['grid_staggering'] = 6
  >>> cube.add_aux_coord(pseudo_coord, 0)
  >>> ants.io.save.ancil(cube, 'load_files/ancil_file_with_pseudo_levels')
  >>> iris.save(cube, 'load_files/contains_pseudo_levels.pp')

Earlier F03 ancil files
=======================

These are all derived from the current version F03 ancil file above.  The
version number for the `middle_um_version_ancil` file is IMDI, and is defined
in F03 for UM versions between 3.1 and 5.1, inclusive.  The value of `15` for
pre-3.1 UM versions is taken from the existing unit test.  For reference, the
current version F03 ancils use a dataset version of `20`.

Using the ANTS 2.1 module again::

  $ python
  >>> import mule
  >>> ff = mule.UMFile.from_file("load_files/ancil_file_with_pseudo_levels")
  >>> ff.fixed_length_header.data_set_format_version = -32768
  >>> ff.to_file("load_files/middle_um_version_ancil")
  >>> ff.fixed_length_header.data_set_format_version = 15
  >>> ff.to_file("load_files/pre_um_3_1_ancil")


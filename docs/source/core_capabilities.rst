.. meta::
   :description lang=en: ANTS Command Line Tools
   :keywords: ANTS, utils
   :property=og:locale: en_GB

=======================
ANTS Command Line Tools
=======================

To assist with carrying out common steps in ancillary file generation, a number
of "general purpose" command line tools are provided. These are
briefly outlined here and detailed in full later in the documentation.

ancil_2anc.py
-------------

:doc:`ancil_2anc` loads one or more iris cubes from the provided filepath(s)
and saves them to the output filepath in NetCDF and/or ancillary file format.


ancil_create_shapefile.py
-------------------------

:doc:`ancil_create_shapefile` creates and saves a shapefile from a list of
pairs of longitude, latitude points that define a single polygon.


ancil_fill_n_merge.py
---------------------

The :doc:`ancil_fill_n_merge` application both merges different datasets
together and fills missing values.

ancil_general_regrid.py
-----------------------

The :doc:`ancil_general_regrid` application regrids a source file onto a
specified target grid.

.. toctree::
   :maxdepth: 2

   ancil_2anc.rst
   ancil_create_shapefile.rst
   ancil_fill_n_merge.rst
   ancil_general_regrid.rst

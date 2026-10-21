.. meta::
   :description lang=en: Tutorial on loading and saving data with ANTS
   :keywords: load, save, netcdf, ancil, metadata, license, licensing, attribution, references, tutorial
   :property=og:locale: en_GB

.. include:: common.txt

.. Created with assitance of MetOffice Enterprise Copilot

Loading and saving data with ANTS
==================================

Every ANTS based application starts by loading source data and a target grid,
and ends by saving the resulting field(s) to disk. ANTS is built on top of
|Iris|, and while you can use :py:func:`iris.load` and :py:func:`iris.save`
directly, the :mod:`ants.io.load` and :mod:`ants.io.save` modules add
capability that ancillary generation specifically needs. You should prefer the
ANTS routines over the base Iris ones unless you have good reason not to.

Why use the ANTS load and save routines?
-----------------------------------------

:mod:`ants.io.load` uses Iris to read the fileformats Iris supports (and
some ANTS specific ones, see :mod:`ants.fileformats`), then additionally:

1. derives the global/regional status of the input data and sets the
   corresponding metadata on the cube,
2. guesses bounds for latitude and longitude coordinates where a source has
   none, and
3. removes any ``forecast_reference_time`` and ``forecast_period``
   coordinates, which are not usually wanted in ancillary fields.
4. preserves metadata by loading sidecar metdata files alongside the data
   files.

:mod:`ants.io.save` similarly extends :py:func:`iris.save` with support for
the F03 UM ancillary fileformat and a UKCA specific flavour of NetCDF, neither
of which Iris can write natively, and has the option to write metadata files
alongside the saved files in the case of saving an F03 UM ancillary fileformat.

Loading data
------------

Use :func:`ants.io.load.load` to load one or more cubes from a filepath (or
list of filepaths):

.. code-block:: python

    import ants

    source_cubes = ants.io.load.load("/path/to/source_file.nc")

This returns a :class:`~iris.cube.CubeList`, even where the file contains a
single field. If you know your source contains exactly one field you may
prefer :func:`ants.io.load.load_cube`, which returns a single
:class:`~iris.cube.Cube` and raises an exception if more than one match is
found.

Loading a target grid
----------------------

Most ANTS applications need a target grid to process or regrid data onto.
:func:`ants.io.load.load_grid` loads a grid definition, without a data
payload, from one or more files, merging horizontal and vertical components
where necessary:

.. code-block:: python

    target_grid = ants.io.load.load_grid("/path/to/target_grid_namelist")

This supports both CAP compliant Fortran namelist grid definition files (use
this where you do not need a land sea mask as part of your processing) and
any fileformat that Iris can read (use this where you need the land sea mask
of the target field).

Where a target's land sea mask is needed directly, for example to make output
consistent with land or sea only data, use
:func:`ants.io.load.load_landsea_mask` instead. This function accepts either
a land binary mask field or a land fraction field:

.. code-block:: python

    # land_threshold is only used when the source is a land fraction field;
    # fractions greater than this value are treated as land.
    target_lsm = ants.io.load.load_landsea_mask(
        "/path/to/target_lsm.nc", land_threshold=0.5
    )

Loading metadata
----------------
Metadata in this tutorial refers to information about the data in a file, that does not
directly affect that data. For example, licensing information or attributions.

Metadata in this tutorial refers to information about the data in a file, that does not
directly affect that data. For example, licensing information or attributions.

Some ancillary file formats cannot include metadata. Metadata can be very important to
keep alongside the data as often data will have some form of requirement or restriction
on it. Because of this, ANTS can handle in external metadata files, provided they match
the naming convention of `filename.extension.accepted-metadata`. The current accepted
metadata attributes are "license", "attribution", "restrictions", "institution",
"acknowledgement", and "references".

This functionality can be turned off through the use of the argument
``--ignore-metadata-read` on the command line or when calling the ANTS load:

.. code-block:: python

    cube = ants.io.load.load("/path/to/source_file" ,ignore_metadata_read=True)


.. note::
    Any attributes or files referencing licensing should use the 'license' spelling for
    consistency.

ANTS can load in external metadata files or 'sidecar' files, if they are kept in the
same directory as the data files, and have the same name (including the extension).
Metadata can be loaded alongside all files, including NetCDF files, however ANTS will
not allow you to load a file with a metadata attribute and a sidecar file with the same
attribute. This is to prevent unintentional loss or overwriting of metadata information.

.. note::
    When using wildcards for loading with sidecar files, add the file extension to the
    end to prevent issues with ANTS attempting to load the sidecar files. E.g.
    `data*.pp` rather than `data*`.


Saving data
-----------

Saving to NetCDF is done via :func:`ants.io.save.netcdf`:

.. code-block:: python

    import ants.io.save as save

    save.netcdf(source_cubes, "/path/to/output.nc")

To save to an F03 UM ancillary file, use :func:`ants.io.save.ancil` instead.
Every cube saved this way **must have a STASH code attribute** set, since this
is used to identify the field in the ancillary file:

.. code-block:: python

    import iris.fileformats.pp

    for cube in source_cubes:
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i030")

    save.ancil(source_cubes, "/path/to/output_ancil")

If your data is destined for UKCA, use :func:`ants.io.save.ukca_netcdf`
instead, which applies UKCA specific conventions (compression, bounds,
data type coercion and attribute renaming) on top of a standard NetCDF save:

.. code-block:: python

    save.ukca_netcdf(source_cubes, "/path/to/output_ukca.nc")

Saving metadata
---------------
Metadata will only be saved to a sidecar file, if the ancil saver is used. This is
because NetCDF files will include the attributes within the file.

This functionality can be turned off through the use of the argument
``--ignore-metadata-write`` on the command line or when calling the ANTS save:

.. code-block:: python

    import ants.io.save as save

    save.ancil(source_cubes, "/path/to/output_ancil", ignore_metadata_write=True)

The sidecar files produced by ANTS follow the same naming coventions at those loaded in
`filename.attribute.accepted-metadata`. Only accepted metadata will be written out.


Key Points
----------

 * Prefer :mod:`ants.io.load` and :mod:`ants.io.save` over calling Iris
   directly - they add corrections and capability that ancillary generation
   depends on.
 * :func:`ants.io.save.ancil` requires every cube to have a ``STASH``
   attribute; NetCDF and UKCA NetCDF saves do not.
 * Use :func:`ants.io.load.load_grid` for a namelist based target grid, and
   :func:`ants.io.load.load_landsea_mask` where the target's land sea mask is
   needed directly.

See Also
--------

 * :doc:`tutorial_regridding` for using a loaded target grid to regrid data.
 * :doc:`ancil_2anc` for a command line tool that wraps a load/save round
   trip to convert between fileformats.
 * :doc:`appendixA_time_handling` for the time metadata expectations placed
   on data being saved as an ancillary.

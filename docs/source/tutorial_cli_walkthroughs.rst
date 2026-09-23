.. meta::
   :description lang=en: Worked examples for the ANTS command line tools
   :keywords: ancil_2anc, ancil_create_shapefile, ancil_fill_n_merge, ancil_general_regrid, ancil_vertical_regrid, tutorial
   :property=og:locale: en_GB

.. include:: common.txt

.. Created with assitance of MetOffice Enterprise Copilot

Worked examples: the ANTS command line tools
================================================

:doc:`core_capabilities` introduces the five general purpose command line
tools that ship with ANTS, and their individual pages (:doc:`ancil_2anc`,
:doc:`ancil_create_shapefile`, :doc:`ancil_fill_n_merge`,
:doc:`ancil_general_regrid`, :doc:`ancil_vertical_regrid`) document their full
set of arguments. This tutorial instead walks through a realistic invocation
of each tool as run in a cylc workflow, so you can see how they fit together
in practice.

All five tools share a common command line interface, provided by
:class:`ants.command_parse.AntsArgParser`:

.. code-block::

    <tool>.py <SOURCE1> [<SOURCE2> ...] --output <OUTPUT> [--ants-config <CONFIG>]

and are typically launched via the ``ants-launch`` wrapper, as shown below.

ancil_2anc: converting between fileformats
--------------------------------------------

:doc:`ancil_2anc` loads one or more cubes and writes them out as NetCDF and/or
an F03 ancillary file, inferring as much metadata as it can from the source.
It is a straight fileformat translation - see :doc:`tutorial_load_save` for
the underlying load/save mechanics.

.. code-block:: bash

    ants-launch ancil_2anc.py land_cover_fraction.nc \
        --output land_cover_fraction_ancil \
        --grid-staggering 6 \
        --ants-config rose-app-run.conf

The ``--grid-staggering`` argument (3 for New Dynamics, 6 for ENDGame) is
often required, since it usually cannot be inferred from a NetCDF source.

ancil_create_shapefile: producing a validity polygon
------------------------------------------------------

:doc:`ancil_create_shapefile` turns a JSON file containing a list of
``[longitude, latitude]`` pairs into a shapefile polygon, which can then be
used as the ``validity_polygon`` input to ``ancil_fill_n_merge`` (see
:doc:`tutorial_merge_fill`).

A minimal input JSON, defining a simple box:

.. code-block:: json

    [[-10.0, 40.0], [-10.0, 60.0], [10.0, 60.0], [10.0, 40.0]]

.. code-block:: bash

    ants-launch ancil_create_shapefile.py validity_region.json validity_region.shp

ancil_fill_n_merge: merging and filling
------------------------------------------

:doc:`ancil_fill_n_merge` merges a primary and (optional) alternate source and
fills any remaining missing points - see :doc:`tutorial_merge_fill` for the
concepts. ``--search-method kdtree`` is recommended for consistency across UM
and LFRic pipelines:

.. code-block:: bash

    ants-launch ancil_fill_n_merge.py primary_source.nc alternate_source.nc \
        --output merged_filled \
        --target-lsm target_lsm.nc \
        --polygon validity_region.shp \
        --search-method kdtree \
        --ants-config rose-app-run.conf

If only ``primary_source.nc`` is provided (no alternate), only the fill stage
runs.

ancil_general_regrid: regridding to a target grid
----------------------------------------------------

:doc:`ancil_general_regrid` regrids a source onto a target grid or target land
sea mask - see :doc:`tutorial_regridding` for the underlying mechanics:

.. code-block:: bash

    ants-launch ancil_general_regrid.py source_field.nc \
        --output regridded_field \
        --target-grid target_grid_namelist \
        --ants-config rose-app-run.conf

To regrid directly onto a target land sea mask instead of a plain grid, use
``--target-lsm`` in place of ``--target-grid``; the result will be made
consistent with that mask using the same fill algorithms discussed in
:doc:`tutorial_merge_fill`.

Like ``ancil_vertical_regrid``, discussed later, this application has no
built-in default regridding scheme - ``rose-app-run.conf`` above must include a
``[ants_regridding_horizontal]`` section (and a ``[ants_regridding_vertical]``
section too, if the target also varies vertically), for example:

.. code-block::

    [ants_regridding_horizontal]
    scheme = Linear

See :class:`ants.config.GlobalConfiguration` for the full list of valid
``scheme`` values. Omitting this section raises an error rather than
silently falling back to a default (the same is true of the
``[ants_regridding_vertical]`` scheme required by ``ancil_vertical_regrid``
- neither tool has a built-in default).

.. note:: `ancil_vertical_regrid` is available for vertical only regrid operations
   or cases where you want to ensure a vertical regrid is carried out before any
   other processing.


ancil_vertical_regrid: regridding onto a new vertical level set
------------------------------------------------------------------

:doc:`ancil_vertical_regrid` is the vertical-only counterpart to
``ancil_general_regrid``. Rather than moving data onto a new horizontal grid,
it interpolates onto a new set of vertical levels (for example a target
vertical namelist), and requires that the source and target already share
the same horizontal (latitude/longitude) coordinates:

.. code-block:: bash

    ants-launch ancil_vertical_regrid.py aerosol_3d.nc \
        --output aerosol_3d_L70 \
        --target-grid vertlevs_L70_50t_20s_80km \
        --ants-config rose-app-run.conf

This application has no default vertical scheme - the ``--ants-config`` file
passed above (``rose-app-run.conf``) must include a
``[ants_regridding_vertical]`` section naming one, for example:

.. code-block::

    [ants_regridding_vertical]
    scheme = Linear

See :class:`ants.config.GlobalConfiguration` for the full list of valid
``scheme`` values. Omitting this section raises an error rather than
silently falling back to a default (the same is true of the
``[ants_regridding_horizontal]`` scheme required by ``ancil_general_regrid``
- neither tool has a built-in default).

.. note::
   ``ancil_vertical_regrid`` checks its target before regridding: if the
   target is a UGrid mesh, it raises an error directing you to the
   regrid-to-mesh application in UG-ANTS instead; if the target's
   latitude/longitude coordinates do not match the source's, it raises an
   error rather than silently regridding horizontally too. Use
   :doc:`ancil_general_regrid` (see :doc:`tutorial_regridding`) when a
   horizontal regrid is also needed.

Decomposition configuration
------------------------------

All five tools accept ``--ants-config`` to point at an ANTS configuration
file. This is most commonly used to enable :doc:`decomposition` for large
datasets, for example:

.. code-block::

    [ants_decomposition]
    x_split = 2
    y_split = 2

    [ants_logging]
    enabled = True

Key Points
----------

 * All five command line tools share the same ``<sources> --output <output>
   [--ants-config <config>]`` interface via
   :class:`ants.command_parse.AntsArgParser`.
 * ``ancil_2anc`` is for fileformat translation, ``ancil_create_shapefile``
   produces validity polygons, ``ancil_fill_n_merge`` combines and fills
   data, ``ancil_general_regrid`` moves data onto a target horizontal grid,
   and ``ancil_vertical_regrid`` moves data onto a target set of vertical
   levels.
 * Prefer ``--search-method kdtree`` on ``ancil_fill_n_merge`` and
   ``ancil_general_regrid`` for consistency across UM and LFRic pipelines
   (see :doc:`tutorial_merge_fill`).
 * If you want to do a vertical regrid for UGrid target domains use the
   UG-ANTS tooling instead.
 * See the ``rose-stem/app/`` directory in the ANTS repository for complete,
   runnable configurations of each of these tools.

See Also
--------

 * :doc:`tutorial_load_save`
 * :doc:`tutorial_regridding`
 * :doc:`tutorial_merge_fill`
 * :doc:`core_capabilities`
 * :doc:`ancil_vertical_regrid`

.. meta::
   :description lang=en: Tutorial on regridding data with ANTS
   :keywords: regrid, esmf, rectilinear, tutorial
   :property=og:locale: en_GB

.. include:: common.txt

Regridding an ancillary field to a target grid
================================================

Producing an ancillary usually means taking source data on one grid and
regridding it onto a target model grid. ANTS provides regridding capability
that goes beyond what |Iris| offers directly, in particular schemes that are
useful when moving between very different grid types (for example a
lat-lon source and a rotated pole or cubesphere target). See
:mod:`ants.regrid` for the full picture; |Iris| itself is the right place to
look for capability that ANTS does not add to
(see :py:mod:`iris.analysis`).

Horizontal and vertical regridding
-----------------------------------

ANTS provides three groups of regridding scheme:

 * :mod:`ants.regrid.rectilinear` - horizontal regridding/interpolation
   schemes for rectilinear grids, for example
   :class:`~ants.regrid.rectilinear.Linear`,
   :class:`~ants.regrid.rectilinear.AreaWeighted` and a
   ``TwoStage`` scheme that performs an intermediate linear regrid before an
   area weighted regrid, which is useful when the source and target
   coordinate reference systems differ substantially.
 * :mod:`ants.regrid.interpolation` - vertical, points-based interpolation
   schemes.
 * :mod:`ants.regrid.esmf` - regridding schemes that use the ESMF framework,
   useful for more complex source/target grid combinations (for example
   unstructured or cubesphere grids).

Rather than choosing a horizontal or vertical scheme directly in your
application code, use :class:`ants.regrid.GeneralRegridScheme`. This lets the
regridding method be swapped later via configuration, without changing your
application:

.. code-block:: python

    import ants

    scheme = ants.regrid.GeneralRegridScheme(horizontal_scheme="TwoStage")

Worked example
--------------

The following mirrors the approach taken by the ``ancil_general_regrid``
application (see :doc:`tutorial_cli_walkthroughs`). We build a small source
cube and a target grid, both using ``ants.tests.stock``, and regrid the
source onto the target:

.. code-block:: python

    import numpy as np
    import ants
    import ants.tests.stock as stock

    # source data on a coarse grid; data must already be shaped to match
    # the cube's shape, so reshape the flat array of values first
    source = stock.geodetic((4, 4), data=np.arange(16).reshape(4, 4))

    # target grid to regrid onto
    target = stock.geodetic((8, 8))

    scheme = ants.regrid.GeneralRegridScheme(horizontal_scheme="TwoStage")
    result = source.regrid(target, scheme)

``result`` is a cube on the target grid. In an application dealing with
larger, real datasets you would typically pass ``result`` through
:func:`ants.decomposition.decompose` rather than calling ``regrid`` directly,
so that the regrid can be split into pieces that fit into memory - see
:doc:`decomposition` for details.

Regridding onto a land sea mask
--------------------------------

Where the target has a land sea mask, you will usually want the regridded
result to be consistent with it, so that land points do not end up with sea
sourced values and vice versa. Use
:func:`ants.analysis.make_consistent_with_lsm` after regridding to fill any
points that need correcting:

.. code-block:: python

    target_lsm = ants.io.load.load_landsea_mask("/path/to/target_lsm.nc")

    ants.analysis.make_consistent_with_lsm(
        result, target_lsm, invert_mask=True, method="kdtree"
    )

See :doc:`tutorial_merge_fill` for more on the fill algorithms
``make_consistent_with_lsm`` uses under the hood, including which one is
recommended.

Zonal mean behaviour
---------------------

If the source and target both have global extent in the ``x`` axis, or the
source has only a single column in ``x``, the target is treated specially so
that the result is a proper zonal mean, regardless of how many longitude
points the target actually has.

Key Points
----------

 * Use :class:`ants.regrid.GeneralRegridScheme` rather than a specific
   rectilinear/esmf/interpolation scheme directly, so the regrid method
   remains configurable.
 * ``TwoStage`` is useful when source and target use substantially different
   coordinate reference systems; a plain ``AreaWeighted`` or ``Linear``
   regrid may be sufficient (and cheaper) otherwise.
 * After regridding onto a masked target, use
   :func:`ants.analysis.make_consistent_with_lsm` to resolve any land/sea
   inconsistencies.
 * For large datasets, combine regridding with
   :func:`ants.decomposition.decompose` (see :doc:`decomposition`).

See Also
--------

 * :doc:`tutorial_load_save` for loading the source data and target grid.
 * :doc:`tutorial_merge_fill` for filling any remaining missing data after
   a regrid.
 * :doc:`ancil_general_regrid` for the command line tool that wraps this
   workflow.

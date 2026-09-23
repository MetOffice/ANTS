.. meta::
   :description lang=en: Tutorial on merging datasets and filling missing data with ANTS
   :keywords: merge, fill, kdtree, spiral search, tutorial
   :property=og:locale: en_GB

.. include:: common.txt

.. Created with assitance of MetOffice Enterprise Copilot

Merging datasets and filling missing data
==========================================

Two related, but distinct, problems come up repeatedly when producing
ancillary fields:

1. **Merging** - combining a primary source with an alternate source, either
   to build a larger coverage than either source has on its own, or to embed
   a high quality local source within a dataset that has wider coverage.
2. **Filling** - replacing missing data (masked or NaN values) with valid
   data taken from elsewhere in the field, so that every point that should
   have a value does have one.

Note that "merge" here is used differently to |Iris|, which uses the term for
combining cubes along a new dimension - see the `Iris Documentation`_ for that
meaning. See :mod:`ants.analysis` for the full set of routines covered here.

Merging two sources
--------------------

:func:`ants.analysis.merge` takes values from a primary source and an
alternate source, optionally guided by a validity polygon that marks the
region where the primary source should be trusted:

.. code-block:: python

    import numpy as np
    import ants
    import ants.tests.stock as stock

    # data must already be shaped to match the cube's shape, so reshape
    # the flat arrays of values first
    primary = stock.geodetic((4, 4), data=np.arange(16).reshape(4, 4))
    alternate = stock.geodetic((4, 4), data=np.zeros((4, 4)))

    # everywhere valid data is present in the primary, it takes priority;
    # elsewhere, the alternate is used.
    result = ants.analysis.merge(primary, alternate)

Where you have a shapefile describing the region the primary source is valid
for, pass it as a ``validity_polygon`` (see :doc:`tutorial_cli_walkthroughs`
for how to produce one with ``ancil_create_shapefile``). A
``blending_distance`` can also be supplied to linearly blend between the
sources over a number of grid cells either side of the polygon boundary,
rather than having a hard edge.

Filling missing data
----------------------

Once you have a merged field (or even just a single source with gaps),
:mod:`ants.analysis` provides several algorithms for filling missing points
by searching for the nearest valid neighbour:

 * :class:`~ants.analysis.KDTreeFill`
 * :class:`~ants.analysis.MooreNeighbourhood`
 * :class:`~ants.analysis.UMSpiralSearch`
 * :class:`~ants.analysis.FillMissingPoints`

.. note::
   **Use** :class:`~ants.analysis.KDTreeFill` **unless you have a specific
   reason not to.** It is the preferred fill algorithm for consistency across
   both UM and LFRic ancillary generation pipelines. The other algorithms
   exist for specialised or legacy cases - for example,
   :class:`~ants.analysis.UMSpiralSearch` reproduces the UM's historical
   spiral search behaviour bit-for-bit, but depends on the optional
   ``um_spiral_search`` package (see :doc:`install`) and is primarily
   intended where matching existing UM output exactly is required.

In practice you will usually reach these fill algorithms indirectly, via
:func:`ants.analysis.make_consistent_with_lsm`, which fills points so that a
field is consistent with a target land sea mask (land points filled from
land, sea points filled from sea):

.. code-block:: python

    target_lsm = ants.io.load.load_landsea_mask("/path/to/target_lsm.nc")

    ants.analysis.make_consistent_with_lsm(
        result, target_lsm, invert_mask=True, method="kdtree"
    )

The ``method`` argument currently accepts ``"kdtree"`` (using
:class:`~ants.analysis.KDTreeFill`, and recommended) or ``"spiral"`` (using
:class:`~ants.analysis.UMSpiralSearch`). The ``ancil_fill_n_merge`` and
``ancil_general_regrid`` command line tools expose the same choice via their
``--search-method`` argument (see :doc:`tutorial_cli_walkthroughs`).

Key Points
----------

 * Merging and filling solve different problems: merging combines two
   sources, filling replaces missing points within a single field.
 * **Prefer** :class:`~ants.analysis.KDTreeFill` **(** ``method="kdtree"`` **in**
   :func:`~ants.analysis.make_consistent_with_lsm`, **or** ``--search-method kdtree``
   **on the command line tools) for consistency across UM and LFRic ancillary
   generation pipelines.** Only reach for
   :class:`~ants.analysis.UMSpiralSearch` where bit-comparable UM legacy
   behaviour is specifically required.
 * :func:`ants.analysis.merge` and the fill algorithms both check that the
   cubes involved are compatible (matching STASH code and units) before
   combining them.

See Also
--------

 * :doc:`tutorial_regridding` for regridding data before merging/filling it.
 * :doc:`tutorial_cli_walkthroughs` for the ``ancil_fill_n_merge`` command
   line tool that wraps this workflow.

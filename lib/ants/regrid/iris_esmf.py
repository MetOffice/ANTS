# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

# Some of the content of this file has been created with the assistance of
# Met Office Github Copilot
"""
Experimental regridding schemes which wrap the ESMF-backed regridders
provided by :mod:`esmf_regrid` (the ``iris-esmf-regrid`` package), as
opposed to :mod:`ants.regrid.esmf` which uses ``esmpy`` directly.

These schemes are exposed under an ``Iris``-prefixed name (e.g.
:class:`IrisESMFAreaWeighted`) to distinguish them from ANTS' own ESMF
regridding implementation and from any future ESMF implementations that may
be plumbed in.

"""

import os
import warnings

import dask.array as da
import numpy as np
from ants.regrid.rectilinear import (
    _fill_outside_bounds,
    _override_coord_data,
    _process_cube_crs,
    _remove_undesriable_attributes,
    _zonal_mean_target,
    compare_coordinate_reference_systems,
)

ESMF_REGRID_IMPORT_MESSAGE = """To use IrisESMFAreaWeighted, ensure esmf_regrid \
(iris-esmf-regrid) is installed and set the ESMFMKFILE environment variable.
https://earthsystemmodeling.org/esmpy_doc/release/latest/html/install.html
#importing-esmpy"""

try:
    import esmf_regrid

    _ESMF_REGRID_IMPORT_ERROR = False
except Exception as _ESMF_REGRID_IMPORT_ERROR:
    if "ESMFMKFILE" not in os.environ:
        warnings.warn(ESMF_REGRID_IMPORT_MESSAGE)
    if os.environ.get("ESMFMKFILE") == "":
        warnings.warn(ESMF_REGRID_IMPORT_MESSAGE)
    esmf_regrid = None
    msg = " {}\nProceeding without capabilities provided by esmf_regrid."
    warnings.warn(msg.format(str(_ESMF_REGRID_IMPORT_ERROR)))


EXPERIMENTAL_MESSAGE = (
    "IrisESMFAreaWeighted is Experimental, for evaluation purposes only, may "
    "change or be removed without notice at a future release."
)


class _IrisESMFAreaWeightedRegridder(object):
    """
    Area weighted regridder using :mod:`esmf_regrid` (``iris-esmf-regrid``).

    Wraps :class:`esmf_regrid.schemes.ESMFAreaWeighted` applying the same
    ANTS specific data preparation and post-processing as
    :class:`ants.regrid.rectilinear.AreaWeighted`:

    - Adheres to ANTS coordinate systems of equivalence (see
      :mod:`ants.coord_systems`).
    - Target points outside the source domain will be set to 'NaN' which
      allows us to distinguish with mask values.
    - Removal of undesirable attributes (those which are no longer relevant
      after a regrid).
    - ANTS ensures that np.nan values are returned unmasked.

    """

    def __init__(self, src_cube, target_cube, mdtol=1.0):
        if esmf_regrid is None:
            raise _ESMF_REGRID_IMPORT_ERROR

        src_cube = _process_cube_crs(src_cube)
        target_cube = _process_cube_crs(target_cube)
        target_cube, self._zonal_mean_cm = _zonal_mean_target(src_cube, target_cube)
        self._grid_staggering = target_cube.attributes.get("grid_staggering", None)

        self._regridder = esmf_regrid.schemes.ESMFAreaWeighted(mdtol=mdtol).regridder(
            src_cube, target_cube
        )

        # Record source grid used in the calculation of the weights.
        self._src_grid = (src_cube.coord(axis="x"), src_cube.coord(axis="y"))

        # _fill_outside_bounds (below) only supports a common source/target
        # crs (unlike ESMF itself, which regrids between differing crs
        # directly). Only apply it in that case; otherwise defer to ESMF's
        # own handling of target points beyond the source extent.
        source_crs = self._src_grid[0].coord_system.as_ants_crs()
        target_crs = target_cube.coord(axis="x").coord_system.as_ants_crs()
        self._same_crs = not compare_coordinate_reference_systems(
            source_crs, target_crs
        )

    def __call__(self, cube):
        cube = _process_cube_crs(cube)
        csrc_dtype = np.promote_types(cube.dtype, "float64")
        if csrc_dtype != cube.dtype:
            cube.data = da.array(cube.core_data(), dtype=csrc_dtype)

        # esmf_regrid, like iris, isn't tolerant of coordinate definitions
        # even though most iris processing will not lead to bit level
        # identical coordinates.
        _override_coord_data(cube, self._src_grid)

        result = self._regridder(cube)
        if self._same_crs:
            filled = _fill_outside_bounds(cube, result, np.nan)
            if filled is not None:
                result = filled
        # Distinguish between masked values and those target points beyond
        # the source extent.
        if np.ma.is_masked(result.data):
            result.data.mask[np.isnan(result.data.data)] = False

        if self._grid_staggering:
            result.attributes["grid_staggering"] = self._grid_staggering
        # Remove attributes which are no longer relevant.
        _remove_undesriable_attributes(result)

        # If the target is a zonal mean, add it back to the result (iris
        # drops it).
        if self._zonal_mean_cm:
            result.add_cell_method(self._zonal_mean_cm)

        return result


class IrisESMFAreaWeighted(object):
    """
    Area weighted regridding scheme using ESMF via :mod:`esmf_regrid`.

    .. warning::
        Experimental, for evaluation purposes only, may change or be removed
        without notice at a future release.

    Suitable for general rectilinear and curvilinear grids.  Intended as an
    evaluation candidate for :class:`ants.regrid.rectilinear.TwoStage`,
    since ESMF is able to perform an area weighted regrid directly between
    source and target grids regardless of coordinate system, without
    requiring an intermediate reprojection step.

    """

    def __init__(self, mdtol=1.0):
        """
        Parameters
        ----------
        mdtol : float, optional
            Tolerance of missing data.  The value returned in each element
            of the returned array will be masked if the fraction of masked
            data exceeds mdtol.  mdtol=0 means no missing data is tolerated
            while mdtol=1 will mean the resulting element will be masked if
            and only if all the contributing elements of data are masked.
            Defaults to 1.

        """
        warnings.warn(EXPERIMENTAL_MESSAGE)
        self.mdtol = mdtol

    def regridder(self, src_grid_cube, target_grid_cube):
        """
        Creates an ESMF area-weighted regridder to perform regridding from
        the source grid to the target grid.

        Parameters
        ----------
        src_grid_cube : :class:`~iris.cube.Cube`
            Defining the source grid.
        target_grid_cube : :class:`~iris.cube.Cube`
            Defining the target grid.

        Returns
        -------
        ~collections.abc.Callable
           Callable with the interface `callable(cube)`

           where `cube` is a cube with the same grid as `src_grid_cube`
           that is to be regridded to the `target_grid_cube`.

        """
        return _IrisESMFAreaWeightedRegridder(
            src_grid_cube, target_grid_cube, mdtol=self.mdtol
        )

    def __repr__(self):
        return "{}(mdtol={})".format(self.__class__.__name__, self.mdtol)

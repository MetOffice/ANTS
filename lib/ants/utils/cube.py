# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import atexit
import hashlib
import logging
import os
import tempfile
import warnings
from datetime import datetime

import ants
import ants.io.save as save
import dask
import iris
import iris.cube
import numpy as np
import shapely
from ants.exceptions import (
    DateRangeNotFullyAvailableException,
    TimeConstraintOutOfBoundsException,
)
from ants.utils.coord import _get_limits
from iris.coords import DimCoord
from scipy.stats import rankdata

_LOGGER = logging.getLogger(__name__)


class CubeBuilder:
    def __init__(
        self,
        crs,
        shape=None,
        data=None,
        xlim=None,
        ylim=None,
        with_bounds=True,
        name=None,
        stash=None,
    ):
        """
        Initialises a basic cube with the parameters passed in.

        The cube must have a coordinate reference system specified
        and either a shape or data passed in.

        By default, with a iris.coord_systems.GeogCS(6371229.0) and a
        shape of (2,2), CubeBuilder will create a cube with the cube.summary() of::

            unknown / (unknown)                 (latitude: 2; longitude: 2)
                Dimension coordinates:
                    latitude                             x             -
                    longitude                            -             x

        .. versionadded :: 2.2

        Parameters
        ----------
        crs : A subclass of :class:`iris.coord_systems.CoordSystem`
        shape : :obj:`tuple`, optional
            The shape of the cube to be created.
        data : :class:`~numpy.ndarray` optional
            An array of data the cube will have.
        xlim : tuple
            A tuple(x0, x1) defining the upper and lower range for axis='x'.
        ylim : tuple
            A tuple(y0, y1) defining the upper and lower range for axis='y'.
        with_bounds : :obj:`bool`, optional
            The option for the latitude and longitude coordinates
            on the cube to contain bounds
        name : :obj:`str`, optional
            The name of the cube.

        Returns
        -------
        None
            Inplace operation

        """
        self.crs = crs
        self.x, self.y, self.data = self._create_data(
            shape, xlim, ylim, data, with_bounds
        )
        self._cube = self._create_the_cube(name, stash)

    def _create_the_cube(self, name, stash):
        """Constructs the most basic cube by putting together pre-calculated pieces."""
        cube = iris.cube.Cube(self.data)
        cube_with_coords = self._add_dimcoords(cube)
        complete_cube = self._ants_utilities(cube_with_coords)
        self._add_metadata(complete_cube, name, stash)
        return complete_cube

    def _create_x_y_and_data(self, shape, xlim, ylim, data, with_bounds):
        """Calculates the x and y data to be added to the cube."""
        # Calculates the x and y data for the minimum cube
        # Adds bounds if needed

        # converts tuple to 1d array
        shape = np.array(shape)
        # checks that the array is indeed 1 dimension
        if shape.ndim != 1:
            raise ValueError(f"Invalid shape {shape} given.")
        xdim = len(shape) - 1
        ydim = len(shape) - 2
        if data is None:
            data = np.arange(np.prod(shape)).reshape(shape)
            data = data.astype("int32")

            if xlim[0] > xlim[1]:
                slices = [slice(None)] * shape.size
                slices[xdim] = slice(None, None, -1)
                data = data[tuple(slices)]
            if ylim[0] > ylim[1]:
                slices = [slice(None)] * shape.size
                slices[ydim] = slice(None, None, -1)
                data = data[tuple(slices)]

        x_bound = np.linspace(xlim[0], xlim[1], endpoint=True, num=shape[xdim] + 1)
        x_bounds = np.array([x_bound[:-1], x_bound[1:]]).T
        x_points = x_bounds.mean(axis=1)

        y_bound = np.linspace(ylim[0], ylim[1], endpoint=True, num=shape[ydim] + 1)
        y_bounds = np.array([y_bound[:-1], y_bound[1:]]).T
        y_points = y_bounds.mean(axis=1)

        if not with_bounds:
            x_bounds = y_bounds = None
        x = {
            "points": x_points,
            "bounds": x_bounds,
            "dim": xdim,
        }
        y = {
            "points": y_points,
            "bounds": y_bounds,
            "dim": ydim,
        }
        return x, y, data

    def _create_data(self, shape, xlim, ylim, data, with_bounds):
        """Creates the data required by the cube and does some basic checks."""
        # Creates all the data a basic cube needs - sorts the xlim and ylim as well
        if data is None and shape is None:
            raise ValueError("Shape and data cannot be None values.")
        cartopy_crs = self.crs.as_cartopy_crs()
        is_geodetic = "geodetic" in cartopy_crs.__class__.__name__.lower()
        if xlim is None:
            if is_geodetic:
                xlim = (-180, 180)
            else:
                xlim = cartopy_crs.x_limits
        if ylim is None:
            if is_geodetic:
                ylim = (-90, 90)
            else:
                ylim = cartopy_crs.y_limits
        if shape is None:
            shape = data.shape
        x, y, data = self._create_x_y_and_data(shape, xlim, ylim, data, with_bounds)
        return x, y, data

    def _add_dimcoords(self, cube):
        """Adds dimension coordinates to the cube"""
        # Adds dimcoords to the cube - the stuff previously calculated
        ants_crs = ants.coord_systems.CFCRS(self.crs)
        x_coord = DimCoord(self.x["points"], bounds=self.x["bounds"])
        ants.utils.coord.set_crs(x_coord, "x", ants_crs)
        y_coord = DimCoord(self.y["points"], bounds=self.y["bounds"])
        ants.utils.coord.set_crs(y_coord, "y", ants_crs)

        cube.add_dim_coord(y_coord, self.y["dim"])
        cube.add_dim_coord(x_coord, self.x["dim"])
        return cube

    def _ants_utilities(self, cube):
        """
        Sets the coordinate reference system for the cube and derives circular status.
        """
        # set the coordinate reference system and do a bit of the workaround stuff
        ants.utils.cube.set_crs(cube, self.crs)
        ants.utils.cube.derive_circular_status(cube)
        return cube

    def _add_metadata(self, cube, name, stash):
        if stash is not None:
            cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi(stash)
        if name is not None:
            cube.rename(name)

    def set_name(self, name):
        """Rename the cube."""
        self._cube.rename(name)

    def set_units(self, units):
        """Set the units of the cube."""
        self._cube.units = units

    def add_3d_time_coord(self, times):
        """
        Adds a time coordinate to the cube.

        Parameters
        ----------
        times : int

        Returns
        -------
        None
            Inplace operation
        """
        coord = iris.coords.DimCoord(
            np.arange(times, dtype="i8"), "time", units="hours since epoch"
        )
        self._cube.add_dim_coord(coord, 0)

    def add_model_level_coordinate(self, additional_attributes=None):
        """Adds a model level coordinate to the cube.

        Parameters
        ----------
        additional_attributes : :obj:`dict`, optional
            The default option for additional attributes is None.

        Returns
        -------
        None
            Inplace operation
        """
        coord = iris.coords.DimCoord(
            np.arange(4, dtype="i8") + 10,
            "model_level_number",
            units="1",
            attributes=additional_attributes,
        )
        self._cube.add_dim_coord(coord, 1)

    def add_hybrid_height_coordinate_factory(self, longitude):
        """Adds a hybrid height coordinate factory to the cube.

        This is required to create a cube with hybrid heights.

        Parameters
        ----------
        longitude : int

        Returns
        -------
        None
            Inplace operation
        """

        # add level height
        coord = iris.coords.AuxCoord(
            np.arange(4, dtype="i8") + 40, long_name="level_height", units="m"
        )
        self._cube.add_aux_coord(coord, 1)

        # add orography - surface altitude
        coord = iris.coords.AuxCoord(
            np.arange(5 * longitude, dtype="i8").reshape(5, longitude) + 100,
            long_name="surface_altitude",
            units="m",
        )
        self._cube.add_aux_coord(coord, [2, 3])

        factory = iris.aux_factory.HybridHeightFactory(
            delta=self._cube.coord("level_height"),
            sigma=self._cube.coord("sigma"),
            orography=self._cube.coord("surface_altitude"),
        )
        self._cube.add_aux_factory(factory)

    def add_sigma_aux_coord(self):
        """Adds a sigma auxillary coordinate to the cube.

        Parameters
        ----------
        None

        Returns
        -------
        None
            Inplace operation
        """
        # needed for the 4d cube
        coord = iris.coords.AuxCoord(
            np.arange(4, dtype="i8") + 50, long_name="sigma", units="1"
        )
        self._cube.add_aux_coord(coord, 1)

    def add_hybrid_pressure_coordinate_factory(self):
        """Adds a hybrid pressure coordinate factory to the cube.

        This is required to create a cube with hybrid pressure. ANTS does not support
        hybrid pressure cubes. This should only be used to test exceptions.

        Parameters
        ----------
        None

        Returns
        -------
        None
            Inplace operation
        """
        coord = iris.coords.AuxCoord(
            np.arange(4, dtype="i8") + 40, long_name="level_pressure", units="Pa"
        )
        self._cube.add_aux_coord(coord, 1)

        coord = iris.coords.AuxCoord(
            np.arange(5 * 6, dtype="i8").reshape(5, 6) + 100,
            long_name="surface_air_pressure",
            units="Pa",
        )
        self._cube.add_aux_coord(coord, [2, 3])

        factory = iris.aux_factory.HybridPressureFactory(
            delta=self._cube.coord("level_pressure"),
            sigma=self._cube.coord("sigma"),
            surface_air_pressure=self._cube.coord("surface_air_pressure"),
        )
        self._cube.add_aux_factory(factory)

    def _unflatten_bounds(self, flat_bounds):
        """
        Re-shape bounds from the flattened bounds array provided.

        Counterclockwise starting from the bottom left::
        3-2
        | |
        0-1

        """
        m, n = flat_bounds.shape
        shape = (m - 1, n - 1, 4)
        bounds = np.zeros(shape, flat_bounds.dtype)
        # Bounds used anticlockwise indexing.
        bounds[..., 0] = flat_bounds[:-1, :-1]
        bounds[..., 3] = flat_bounds[1:, :-1]
        bounds[..., 2] = flat_bounds[1:, 1:]
        bounds[..., 1] = flat_bounds[:-1, 1:]
        return bounds

    def make_cube_curvilinear(self, crs):
        """
        Generate curvilinear lat-lon cube by translating 1D cube on the specified
        coordinate system.

        Parameters
        ----------
        crs : A subclass of :class:`iris.coord_systems.CoordSystem`.

        Returns
        -------
        None
            Inplace operation
        """
        x, y = ants.utils.cube.horizontal_grid(self._cube)

        cart_src_crs = crs.as_cartopy_crs()
        tgt_crs = iris.coord_systems.GeogCS(6371229.0)
        cart_tgt_crs = tgt_crs.as_cartopy_crs()

        # Derive x and y points in lat-lon crs
        xx_pnt, yy_pnt = np.meshgrid(x.points, y.points)
        xyz = cart_tgt_crs.transform_points(cart_src_crs, xx_pnt, yy_pnt)
        xx_pnt, yy_pnt = xyz[..., 0], xyz[..., 1]

        # Derive x and y bounds in lat-lon crs
        # - Create flat bounds arrays to provide meshgrid
        x_bounds = np.zeros(x.points.size + 1)
        y_bounds = np.zeros(y.points.size + 1)
        x_bounds[:-1] = x.bounds[:, 0]
        x_bounds[-1] = x.bounds[-1, 1]
        y_bounds[:-1] = y.bounds[:, 0]
        y_bounds[-1] = y.bounds[-1, 1]
        x_bounds, y_bounds = np.meshgrid(x_bounds, y_bounds)

        # - Reconstruct 2D bounds after transforming to the target crs.
        xyz = cart_tgt_crs.transform_points(cart_src_crs, x_bounds, y_bounds)
        x_bounds = self._unflatten_bounds(xyz[..., 0])
        y_bounds = self._unflatten_bounds(xyz[..., 1])

        # Remove original coords.
        self._cube.remove_coord(x)
        self._cube.remove_coord(y)

        # Add multi-dim coords to cube
        acrs = ants.coord_systems.CFCRS(tgt_crs)
        x_coord = iris.coords.AuxCoord(xx_pnt, bounds=x_bounds)
        ants.utils.coord.set_crs(x_coord, "x", acrs)
        y_coord = iris.coords.AuxCoord(yy_pnt, bounds=y_bounds)
        ants.utils.coord.set_crs(y_coord, "y", acrs)
        self._cube.add_aux_coord(x_coord, [0, 1])
        self._cube.add_aux_coord(y_coord, [0, 1])

    @staticmethod
    def derive_crs(ellipsoid, north_pole_latitude, north_pole_longitude):
        """Checks the north pole coordinates and updates crs accordingly.

        Parameters
        ----------
        ellipsoid : A subclass of :class:`iris.coord_systems.CoordSystem`.
        north_pole_latitude : float
        north_pole_longitude : float

        Returns
        -------
        A subclass of :class:`iris.coord_systems.CoordSystem`.

        """
        if north_pole_latitude != 90.0 or north_pole_longitude != 0.0:
            crs = iris.coord_systems.RotatedGeogCS(
                north_pole_latitude, north_pole_longitude, ellipsoid=ellipsoid
            )
        else:
            crs = ellipsoid
        return crs


def sort_cubes(primary_sources, alternate_sources):
    """
    Sort the alternate sources to match the ordering of the primary set.

    Sorting applies in the case where there is more than one primary and
    alternate source.  The sorting key is firstly uses the STASH attribute, but
    a fall-back to the name is used where not present.  The order
    of the primary sources will always be unchanged.

    Parameters
    ----------
    primary_sources : Iterable of :class:`~iris.cube.Cube` objects
        The primary dataset which has a highest priority i.e. overriding values
        in the alternate dataset.
    alternate_sources : Iterable of :class:`~iris.cube.Cube` objects
        The alternate data set which is to be merged, taking a lower priority
        to values contained within the primary dataset.

    Returns
    -------
    : tuple(iterable of :class:`~iris.cube.Cube` objects,
            iterable of :class:`~iris.cube.Cube` objects)
        Return the primary and alternative sources respectively, sorted
        according to their STASH or cube.name

    Raises
    ------
    ValueError
        When there is no stash/name pair between primary and alternative
        sources.  This means an ambiguous relationship and sorting is not
        possible.

    """

    def get_target(src, targets, con, ref):
        msg = "'primary_cubes' and 'alternate_cubes' don't share common " "fields '{}'"
        msg2 = (
            "'alternate_cubes' contains more than one field corresponding "
            "to 'primary_cubes': '{}'\nBad metadata is commonly the cause "
            "of such an occurrence.\n"
            "On occasion, iris necessarily returns more than one cube to "
            "describe a set of related fields on load where the metadata "
            "is not correct."
        )
        target = targets.extract(con)
        if len(target) == 0:
            raise ValueError(msg.format(ref))
        elif len(target) > 1:
            raise ValueError(msg2.format(ref))
        return target[0]

    primary_sources = iris.cube.CubeList(primary_sources)
    alternate_sources = iris.cube.CubeList(alternate_sources)
    if len(alternate_sources) == len(primary_sources) == 1:
        # Nothing to sort...
        return primary_sources, alternate_sources

    sorted_targets = iris.cube.CubeList()
    for src in primary_sources:
        if "STASH" in src.attributes:
            stash_con = iris.AttributeConstraint(STASH=src.attributes["STASH"])
            target = get_target(
                src, alternate_sources, stash_con, src.attributes["STASH"]
            )
        else:
            target = get_target(src, alternate_sources, src.name(), src.name())
        sorted_targets.append(target)
    return primary_sources, sorted_targets


def is_equal_hgrid(cubes):
    """
    Determine whether all cubes provided are defined on the same grid.

    Parameters
    ----------
    cube : iterable of :class:`~iris.cube.Cube` objects

    Returns
    -------
    bool
        Returns True if all cubes provided are defined on the same horizontal
        grid while returns False if not.

    """

    ref = cubes[0]
    ref_x, ref_y = ants.utils.cube.horizontal_grid(ref)
    if _is_ugrid(ref):
        raise ValueError("ANTS doesn't support ugrid data. Please use UG-ANTS instead.")

    result = True
    for i in range(1, len(cubes)):
        cube = cubes[i]
        if _is_ugrid(cube):
            raise ValueError(
                "ANTS doesn't support ugrid data. Please use UG-ANTS instead."
            )

        x, y = ants.utils.cube.horizontal_grid(cube)
        equal_x = ants.utils.coord.relaxed_equality(x, ref_x)
        equal_y = ants.utils.coord.relaxed_equality(y, ref_y)

        different_grid = not equal_x or not equal_y

        different_metadata = False

        if different_grid or different_metadata:
            result = False
            break
    return result


def _global_extent(coord, global_extent):
    result = False
    if hasattr(coord.units, "modulus") and coord.units.modulus:
        coord_copy = coord.copy()
        ants.utils.coord.guess_bounds(coord_copy, False)
        if coord_copy.has_bounds():
            xmin, xmax = coord_copy.bounds.min(), coord_copy.bounds.max()
            if ants.utils.ndarray.isclose((xmax - xmin), (global_extent - 1e-4)):
                result = True
    return result


def is_global(cube, x_axis_only=False):
    """
    Determine if grid extent is global.

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube`
        Source cube on which to determine global extent of its horizontal
        grid.
    x_axis_only : :class:`bool`, optional
        Check 'x' axis only.

    Returns
    -------
    : bool
        Whether field is global or not (regional)

    """
    x, y = ants.utils.cube.horizontal_grid(cube)
    res = _global_extent(x, 360)
    if not x_axis_only:
        res = res and _global_extent(y, 180)
    return res


def set_month_mean_for_year(cube, year):
    """
    Set metadata on a cube as if it were a single year of monthly mean data.

    This function overrides the existing time coordinate on the cube. It also
    assumes that the time coordinate starts in January.

    In ANTS, until we have better climatology support, this function should
    be used to set representative climatology times.

    Parameters
    ----------
    cube : :class:`iris.cube.Cube`
    year : int
        year for the data.

    Returns
    -------
    : None
        In-place operation.

    Raises
    ------
    RuntimeError
        If the cube does not have exactly one time based coordinate.

    Warning
    -------
    Correct representation of climatologies are subject to changes in both
    iris and ANTS.

    Note
    --------
    See :doc:`/appendixA_time_handling` for further information.

    """
    time_coords = find_time_coordinates(cube)

    if len(time_coords) == 1:
        time_coord = time_coords[0]
    elif len(time_coords) > 1:
        # Ensure there isn't any other time based coordinates.
        msg = "More than one time based coordinate: {}"
        time_coord_names = []
        for coord in time_coords:
            time_coord_names.append(coord.name())
        raise RuntimeError(msg.format(time_coord_names))
    else:
        raise RuntimeError("No time based coordinates")

    bounds = time_coord.units.date2num(
        [datetime(year, i, 1) for i in range(1, 13)] + [datetime(year + 1, 1, 1)]
    )
    bounds = np.array([bounds[:-1], bounds[1:]]).T
    points = bounds.mean(axis=1)

    time_coord.points = points
    time_coord.bounds = bounds

    # Pre-existing 'time' cell methods.
    time_mean_cm = iris.coords.CellMethod("mean", coords="time")
    cell_methods = [x for x in cube.cell_methods if "time" in x.coord_names]
    if cell_methods:
        if len(cell_methods) > 1 or (cell_methods[0] != time_mean_cm):
            msg = "Pre-existing unexpected methods relating to time: {}"
            raise RuntimeError(msg.format(cell_methods))
    else:
        cube.add_cell_method(time_mean_cm)


def sanitise_auxcoords(cube):
    """
    Enforce increasing dimension mappings for all coordinates.

    Helper function to transpose multidimensional coordinates as necessary to
    enforce increasing order dimension mappings.

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube`

    Note
    ----
    Common usage can be after using :meth:`iris.cube.Cube.transpose`, see
    https://github.com/SciTools/iris/issues/2606.

    """
    for coord in cube.aux_coords:
        if coord.ndim > 1:
            dims = cube.coord_dims(coord)
            dim_rank = (rankdata(dims, method="ordinal") - 1).tolist()
            if dim_rank != range(coord.ndim):
                # Sanitise coordinate
                new_order = range(len(dim_rank))
                transpose_indx = [dim_rank.index(val) for val in new_order]
                points = coord.points.transpose(transpose_indx)
                bounds = None
                if coord.has_bounds():
                    bounds = coord.bounds.transpose(transpose_indx + [-1])
                new_coord = coord.copy(points, bounds=bounds)

                # Update the aux factories before removing coordinates from the
                # cube so as not to break them.
                for factory in cube.aux_factories:
                    factory.update(coord, new_coord)
                cube.remove_coord(coord)
                cube.add_aux_coord(new_coord, sorted(dims))


def update_history(cube, string, date=None, add_date=True):
    """
    Generalised function for updating a cube history attribute.

    ISO-format date stamped history attribute update.

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube` or :class:`~iris.cube.CubeList`
        Cube or CubeList to modify its history attribute.
        If CubeList then all Cubes will be given an identical history update.
    string : str
        Content to populate the history attribute.
    add_date : :obj:`bool`, optional
        Boolean to determine whether the date should be prepended to
        the history content string. True by default.
    """

    if date:
        warnings.warn(
            "The date option in ants.utils.cube.update_history has been deprecated."
            "If add_date is true then the current date and time will be used. "
            "Cubelists can be passed directly to update_history to be updated with an "
            "identical history attribute.",
            FutureWarning,
        )

    cubes = as_cubelist(cube)

    if add_date:
        date = datetime.today()
        date = date.replace(microsecond=0)

        history = f"{date.isoformat()}: {string}"
    else:
        history = string

    for cc in cubes:
        cube_history = history
        if "history" in cc.attributes:
            cube_history = "\n".join([history, cc.attributes["history"]])
        cc.attributes["history"] = cube_history


def get_slices(source, ylim, xlim, pad_width=0):
    """
    Return slice objects representing the horizontal grid limits specified.

    If cells even only partially overlap the limits, they are included in the
    slices returned.  In the case where there are no bounds, these are
    inferred.

    Parameters
    ----------
    source : :class:`iris.cube.Cube`
      Source cube to slice.
    ylim : tuple
      A tuple(y0, y1) defining the upper and lower range for axis='y'.
    xlim : tuple
      A tuple(x0, x1) defining the upper and lower range for axis='x'.
    pad_width : :obj:`int`, optional
        Pad the slices by the specified number of cells.

    Returns
    -------
    : tuple(slice, slice)
        Slice objects for slicing the provided cube.  The order of the slices
        corresponds to the mapping to the source provided.

    Raises
    ------
    ants.exceptions.NoCoverageError
        When no cells can be found within the grid limits specified.

    Note
    ----
    This function is wraparound aware.

    """
    xmin, xmax = min(xlim), max(xlim)
    ymin, ymax = min(ylim), max(ylim)
    guess_horizontal_bounds(source)
    source_x, source_y = horizontal_grid(source, dim_coords=True)
    source_x_bounds = source_x.bounds.copy()

    if getattr(source_x.units, "modulus", None) is not None:
        source_x_bounds = ants.utils.ndarray.wrap_lons(
            source_x.bounds, xmin, source_x.units.modulus, endpoint=True
        )

    x_contained = ants.utils.ndarray.greater(source_x_bounds, xmin).sum(axis=1) > 0
    x_contained *= ants.utils.ndarray.less(source_x_bounds, xmax).sum(axis=1) > 0
    y_contained = ants.utils.ndarray.greater(source_y.bounds, ymin).sum(axis=1) > 0
    y_contained *= ants.utils.ndarray.less(source_y.bounds, ymax).sum(axis=1) > 0

    # Test the case where the specified extract range lies entirely within the
    # bounds of one source cell in either axis.
    if x_contained.sum() == 0:
        if getattr(source_x.units, "modulus", None) is not None:
            if source_x.bounds[-1, -1] > source_x.bounds[0, 0]:
                direction = ants.utils.ndarray.less(np.diff(source_x_bounds), 0)
                source_x_bounds[direction[:, 0], 0] -= source_x.units.modulus
            else:
                direction = ants.utils.ndarray.greater(np.diff(source_x_bounds), 0)
                source_x_bounds[direction[:, 0], -1] -= source_x.units.modulus
        x_contained = ants.utils.ndarray.greater(xmin, source_x_bounds).sum(axis=1) > 0
        x_contained *= ants.utils.ndarray.less(xmax, source_x_bounds).sum(axis=1) > 0
    if y_contained.sum() == 0:
        y_contained = ants.utils.ndarray.greater(ymin, source_y.bounds).sum(axis=1) > 0
        y_contained *= ants.utils.ndarray.less(ymax, source_y.bounds).sum(axis=1) > 0

    xslice = np.where(x_contained)[0]
    yslice = np.where(y_contained)[0]

    if xslice.size == 0 or yslice.size == 0:
        xslice = yslice = None
    else:
        for pad in range(pad_width):
            if source_x.circular:
                # Extend x-slices with wraparound.
                xslice = np.unique(
                    np.hstack([xslice, xslice - 1, xslice + 1]) % source_x.points.size
                )
            else:
                # Extend x-slices without wraparound.
                xslice = np.hstack([xslice, xslice - 1, xslice + 1])
                xslice = np.unique(
                    xslice[(xslice >= 0) * (xslice <= source_x.points.size - 1)]
                )

            # Extend y-slices with no wraparound.
            yslice = np.hstack([yslice, yslice - 1, yslice + 1])
            yslice = np.unique(
                yslice[(yslice >= 0) * (yslice <= source_y.points.size - 1)]
            )

        # Group indices to optimise extraction
        ydiff = np.diff(yslice)
        if (np.unique(ydiff) == 1).all():
            yslice = [slice(yslice.min(), yslice.max() + 1)]
        else:
            # Runtime rather than Value is raise as this might occur when
            # considering polar wraparound.
            raise RuntimeError(
                "Unable to resolve discontiguous extraction " "along y-axis"
            )
        xdiff = np.diff(xslice)
        if (np.unique(xdiff) == 1).all():
            xslice = [slice(xslice.min(), xslice.max() + 1)]
        else:
            xslice = ants.utils.ndarray.group_indices(xslice)
            yslice = yslice * len(xslice)

    if xslice is None or yslice is None:
        raise ants.exceptions.NoCoverageError()

    if len(xslice) != len(yslice):
        raise ValueError(
            "Underspecified slicing specification.  There is a "
            "mismatch between the number of x and y slices"
        )

    # Return the slices according to the provided source dimension mapping
    slices = [[slice(None)] * source.ndim] * len(xslice)
    for ss in range(len(slices)):
        slices[ss][source.coord_dims(source_x)[0]] = xslice[ss]
        slices[ss][source.coord_dims(source_y)[0]] = yslice[ss]
        slices[ss] = tuple(slices[ss])
    return slices


def concatenate_cube(cubes):
    """
    As :func:`concatenate`, only raise an exception on returning more than 1 cube.

    Warning
    -------
    :func:`ants.utils.cube.concatenate_cube` is deprecated as of ANTS 2.0
    and will be removed in a future release.
    Please use the iris method :meth:`iris.cube.CubeList.concatenate_cube`.

    """
    result = concatenate(cubes)
    if len(result) > 1:
        msg = ["Expected only a single cube, found {}.".format(len(result))]
        raise iris.exceptions.ConcatenateError(msg)
    return result[0]


def concatenate(cubes):
    """
    Concatenate cubes together.

    Convenience wrapper around the iris concatentation functionality, allowing
    cubes with missing dimension coordinates to be concatenated where there are
    common aux coords.

    Parameters
    ----------
    cubes : :class:`iris.cube.CubeList` objects
        Cubes in which to concatenate.

    Returns
    -------
    : :class:`iris.cube.CubeList`
        New CubeList object of concatenated cubes.

    Warning
    -------
    :func:`ants.utils.cube.concatenate` is deprecated as of ANTS 2.0
    and will be removed in a future release.
    Please use the iris method :meth:`iris.cube.CubeList.concatenate`.


    See Also
    --------
    :meth:`iris.cube.CubeList.concatenate` : for underlying iris function.

    """
    warnings.warn(
        "ants.utils.cube.concatenate and ants.utils.cube.concatenate_cube are "
        "deprecated as of ANTS 2.0 and will be removed in a future release. "
        "Please use the iris method iris.cube.CubeList.concatenate.",
        FutureWarning,
    )
    for cube in cubes:
        for aux_coord in cube.aux_coords:
            try:
                tmp_coord = iris.coords.DimCoord.from_coord(aux_coord)
                m = hashlib.md5()
                m.update(tmp_coord.name().encode("utf-8"))
                tmp_coord.rename("temporary_concat_coord_{}".format(m.hexdigest()))
                cube.add_dim_coord(tmp_coord, cube.coord_dims(aux_coord))
            except ValueError:
                pass

    result = cubes.concatenate()

    # Remove all temporary dimension coordinates created now that we have
    # concatenated.
    for res in result:
        for coord in res.dim_coords:
            if coord.long_name and "temporary_concat_coord" in coord.long_name:
                res.remove_coord(coord)

    return result


def reverse_coordinate(cube, coordinate):
    """
    Reverse the direction of a coordinate in a cube.

    Parameters
    ----------
    cube : :class:`iris.cube.Cube`
    coordinate : basestring or :class:`iris.coords.Coord` object.

    Returns
    -------
    : :class:`iris.cube.Cube`

    Note
    ----
    The returned cube shares the same data.

    """
    coord = cube.coord(coordinate)
    if coord not in cube.dim_coords:
        raise RuntimeError(
            "Only an inversion of a dimension coordinate "
            "is supported ({})".format(coord.name())
        )
    dims = cube.coord_dims(coord)[0]

    # Invert data
    data = cube.lazy_data()
    rcube = cube.copy(iris.util.reverse(data, dims))
    coord = rcube.coord(coord)
    coord.points = iris.util.reverse(coord.points, 0)

    if coord.has_bounds():
        coord.bounds = iris.util.reverse(coord.bounds, [0, 1])
    return rcube


def as_cubelist(cubes):
    """
    Function for ensuring that we return a Cubelist, irrespective of whether
    a Cube or a CubeList has been provided.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube` or :class:`iris.cube.CubeList`

    Returns
    -------
    :class:`iris.cube.CubeList`

    """
    # Function for ensuring that we always deal with a cubelists
    if isinstance(cubes, iris.cube.Cube):
        cubes = iris.cube.CubeList([cubes])
    return cubes


def guess_horizontal_bounds(cubes):
    """
    Guess the bounds on the horizontal grid coordinates of one or more cubes.

    Parameters
    ----------
    cubes : One or more :class:`~iris.cube.Cube`
        Source cubes on which to guess bounds.

    """
    cubes = as_cubelist(cubes)
    for cube in cubes:
        x, y = horizontal_grid(cube)
        ants.utils.coord.guess_bounds(x, strict=False)
        ants.utils.coord.guess_bounds(y, strict=False)


def horizontal_grid(cube, dim_coords=None):
    """
    Return the horizontal coordinates of the cube.

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube`
        Source cube on which to extract the horizontal grid coordinates
    dim_coords : :obj:`bool`, optional
        Constrain horizontal grid extraction to those amongst dimension
        coordinates only.

    Returns
    -------
    : tuple
        Tuple of :class:`~iris.coords.Coord` objects: (x, y) corresponding to the
        horizontal grid of the provided cube.

    """
    x = cube.coord(axis="x", dim_coords=dim_coords)
    y = cube.coord(axis="y", dim_coords=dim_coords)
    return x, y


def derive_circular_status(cube):
    """
    Derive circular attribute of the provided cubes, setting to True where
    applicable.

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube`
        Source cube(s).

    """
    cubes = as_cubelist(cube)
    for cc in cubes:
        x, _ = horizontal_grid(cc)
        if is_global(cc, x_axis_only=True) and hasattr(x, "circular"):
            x.circular = True


def defer_cube(cube):
    """
    Defer the provided Cube or CubeList.

    Write the cube data to disk and load back again resulting in a deferred
    cube.  Automatically cleans up after itself when the python process
    completes normally.  If the python process exits abnormally or is killed
    (e.g. by a job scheduler), temporary files may remain that need to be
    deleted manually.

    Parameters
    ----------
    cube : :class:`iris.cube.Cube`
        Cube(s) to defer.

    Returns
    -------
    : :class:`iris.cube.Cube`
        Cube(s) with its data deferred to disk.

    Note
    ----
    The temporary file location for output files is determined by the
    ANTS_TEMPORARY_DIR environment variable.

    See :mod:`ants.decomposition`.

    See :py:data:`tempfile.tempdir` for further information concerning
    temporary file locations.

    """

    # Developer notes:
    #
    # Multiprocessing does not allow the sharing of file handles between
    # processors.  This has implications for associating the filehandle to
    # the lazy array.
    #
    # Ipython parallel cannot support associating our FileCleanup within the
    # individual engines as copies are returned, not the originals
    # themselves.  This has an undesirable effect of calling the object
    # tidy-up (thus deleting the files early).
    cubes = as_cubelist(cube)
    res = iris.cube.CubeList()
    for cc in cubes:
        fh = tempfile.NamedTemporaryFile(suffix=".nc")
        _LOGGER.info("Deferring data to {}".format(fh.name))
        # Close the created filehandle as we cannot share it between processes
        # if we could then it would clear up the file on garbage collection.
        fh.close()
        save.netcdf(cc, fh.name, update_history=False)
        cc = ants.io.load.load_cube(fh.name)
        cc._fh = fh.name
        res.append(cc)
        atexit.register(_delete_temporary_file, fh.name)
    cubes = res
    if isinstance(cube, iris.cube.Cube):
        cubes = cubes[0]
    return cubes


def _delete_temporary_file(filename):
    try:
        os.remove(filename)
    except FileNotFoundError:
        # Implies that file has already been deleted.
        pass


def inherit_metadata(source, reference):
    """
    Inherit cube metadata from a provided reference.

    Metadata from target is inherited to source from the following:
    1. Name (cube.name())
    2. Units
    3. cube.attributes['grid_staggering']

    Parameters
    ----------
    source : :class:`iris.cube.Cube`
        Source to have its metadata update.
    reference : :class:`iris.cube.Cube`
        Reference which defines the metadata to inherit from.

    """
    source.rename(reference.name())
    source.units = "1"
    if reference.units != "unknown":
        source.units = reference.units
    if "grid_staggering" in reference.attributes:
        source.attributes["grid_staggering"] = reference.attributes["grid_staggering"]


def set_crs(cube, crs=None):
    """
    Set cube coordinate system.

    Set coordinate system of the cube, correcting and populating metadata
    where possible.

    Parameters
    ----------
    cube : :class:`iris.cube.Cube`
        Cube to infer suitable coordinate_system.
    crs : `iris.coord_systems.CoordSystem`, optional
        Defaults to a UM Sphere where unspecified and undefined in the cube
        (ants.coord_systems.UM_SPHERE).

    """
    sx, sy = horizontal_grid(cube)
    if crs is None:
        if sy.coord_system is None and sx.coord_system is not None:
            crs = sx.coord_system
            sx.coord_system = None
        elif sy.coord_system is not None and sx.coord_system is None:
            crs = sy.coord_system
            sy.coord_system = None
        elif sy.coord_system is not None and sx.coord_system is not None:
            crs = sx.coord_system
            crsy = sy.coord_system
            if crs != crsy:
                msg = "Coordinate systems do not agree across axes"
                raise ValueError(msg)
    ants.utils.coord.set_crs(sx, "x", crs)
    ants.utils.coord.set_crs(sy, "y", crs)


def _is_ugrid(cube):
    """
    Returns whether the provided Cube is a UGrid cube.

    Parameters
    ----------
    cube : :class:`iris.cube.Cube`
        Cube to classify.

    Returns
    -------
    : boolean
        Whether cube is UGrid cube
    """
    # This method of determining if a cube is UGrid may need to be more
    # nuanced in future:
    # https://github.com/cf-convention/cf-conventions/issues/153
    has_conventions = "Conventions" in cube.attributes
    ugrid = False
    if has_conventions and "ugrid" in cube.attributes["Conventions"].lower():
        ugrid = True
    return ugrid


def find_time_coordinates(cube):
    """
    Returns the time coodinates of the cube.

    Returns the time coordinates of the cube. These are recognised by units,
    not name, as defined in the `CF conventions
    <http://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#time-coordinate>`_.
    Coordinates 'forecast_reference_time' and 'forecast_period' are ignored
    for the purposes of this function as they are deleted on load in ANTS.

    Parameters
    ----------
    cube : :class:`iris.cube.Cube`
        Cube to find the time coordinates of.

    Returns
    -------
    : list of :class:`iris.coords.Coord` instances
        The time coordinates of the cube.

    Raises
    ------
    ValueError
        If the cube has a coordinate with time units that is not called
        'time' or if the cube has a coordinate called 'time' which does
        not have time units.

    """
    times = []
    for coord in cube.coords():
        # Find any coordinates with units of time.
        if coord.units.is_time_reference():
            # Ignore 'forecast_reference_time' and 'forecast_period'
            # coordinates. These are known coordinates with time units
            # which ANTS removes from cubes on load().
            if (
                coord.name() == "forecast_reference_time"
                or coord.name() == "forecast_period"
            ):
                continue
            # Check that coordinates with units of time are called 'time'.
            if not (coord.name() == "time"):
                msg = (
                    "Coordinate has the units of a time coordinate but "
                    "does not have the standard name of 'time' as per "
                    "CF conventions: ({})"
                )
                raise ValueError(msg.format(coord.name()))
            else:
                times.append(coord)
        # Check that there are no coordinates called 'time' which do not
        # have time units.
        elif coord.name() == "time":
            msg = (
                "Coordinate has the standard name of 'time' but does "
                "not have the units of a time coordinate as per CF "
                "conventions: ({})"
            )
            raise ValueError(msg.format(coord.name()))

    return times


def fix_mask(cube_input):
    """
    Helper routine used to adjust a cube's mask so that it is of the same shape
    as the associated data.

    Tests the input to see if it should be handled as a cube or cubelist and
    uses ```_fix_cube_mask(cube)``` to carry out the work of adjusting the mask(s).

    Parameters
    ----------
    cube_input : :class:`iris.cube.Cube` or :class:`iris.cube.CubeList`

    Returns
    -------
    : None
        In-place operation.

    """
    if isinstance(cube_input, iris.cube.CubeList):
        for cube in cube_input:
            _fix_cube_mask(cube)
    else:
        _fix_cube_mask(cube_input)


def _fix_cube_mask(cube):
    """
    If the input cube has no mask, this routine returns an mask array of
    False values that matches the shape of the input core data array.
    It is designed to address cases where a single False numpy boolean
    is being returned as a mask rather than a data sized array of False
    values. It maintains unrealised data if input is lazy.
    """
    lazy = cube.has_lazy_data()
    cube_core_data = cube.core_data()
    if lazy:
        mask_values = dask.array.ma.getmaskarray(cube_core_data)
    else:
        mask_values = np.ma.getmask(cube_core_data)

    if cube_core_data.shape != mask_values.shape:
        if lazy:
            cube.data = dask.array.ma.masked_array(
                cube_core_data, mask=np.zeros(cube_core_data.shape, dtype=bool)
            )
        else:
            cube.data = np.ma.masked_array(
                cube_core_data, mask=np.zeros(cube_core_data.shape, dtype=bool)
            )
    return


def _create_time_constraint(begin_year, end_year):
    """
    Creates the time constraint

    Parameters
    ----------
    begin_year
    end_year

    Returns
    -------
    An iris time constraint for the requested years.

    """
    return iris.Constraint(time=lambda cell: begin_year <= cell.point.year <= end_year)


def _check_data_availability(cube, begin_year, end_year):
    """
    Checks the years requested are within the range available in the data, raises an
    exception to inform the user if not all years are available.

    Parameters
    ----------
    cube
    begin_year
    end_year

    Returns
    -------
    A DateRangeNotFullyAvailableException letting the user know what years are available
    in the data, compared with what they asked for.

    """
    cube_start_year = _get_cube_start_year(cube)
    cube_end_year = _get_cube_end_year(cube)
    start_in_range = _is_year_in_range(cube_start_year, begin_year, cube_end_year)
    end_in_range = _is_year_in_range(cube_start_year, end_year, cube_end_year)
    requested_range = f"{begin_year} to {end_year}"
    if (
        (start_in_range and not end_in_range)
        or (end_in_range and not start_in_range)
        or (not start_in_range and not end_in_range)
    ):
        cube_date_range = f"{cube_start_year} to {cube_end_year}"
        raise DateRangeNotFullyAvailableException(requested_range, cube_date_range)


def _is_year_in_range(cube_start_year, test_year, cube_end_year):
    """
    Boolean utility function to test if a year is within the available range.

    """
    return cube_start_year <= test_year <= cube_end_year


def _get_cube_start_year(cube):
    """
    Uses the _get_limits function to return the minimum and maximum time bounds, then
    returns the minimum.

    Parameters
    ----------
    cube

    Returns
    -------
    minimum time bounds of the cube

    """
    time_coord = cube.coord(axis="t")
    start_time = time_coord.units.num2date(_get_limits(time_coord)[0])
    return start_time.year


def _get_cube_end_year(cube):
    """
    Uses the _get_limits function to return the minimum and maximum time bounds, then
    returns the maximum.

    Parameters
    ----------
    cube

    Returns
    -------
    maximum time bounds of the cube

    """
    time_coord = cube.coord(axis="t")
    end_time = time_coord.units.num2date(_get_limits(time_coord)[1])
    return end_time.year


def create_time_constrained_cubes(cubes, begin_year, end_year):
    """
    Returns the cubes after constraining to the period between begin_year and end_year.

    This includes both the begin_year and end_year in the result.  Each cube
    is filtered in turn: this means this function returns the same number of
    cubes as was input, but each cube is constrained individually.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube` or :class:`iris.cube.CubeList`
        The cubes to be constrained.

    begin_year : int
        The first year of data to return.
    end_year : int
        The last year of data to return.

    Returns
    -------
    : :class:`iris.cube.CubeList`
        A CubeList from constraining each individual cube to the time range
        specified.  Note that a :class:`iris.cube.CubeList` is always
        returned, even if the `cubes` argument is a single
        :class:`iris.cube.Cube`.

    Raises
    ------
    TimeConstraintOutOfBoundsException
        If a cube does not contain data in the specified time range.
    DateRangeNotFullyAvailableException
        If a cube does not contain all the years requested.

    """
    cubes = ants.utils.cube.as_cubelist(cubes)
    constrained_cubes = []
    for cube in cubes:
        new_cube = cube.extract(_create_time_constraint(begin_year, end_year))
        if new_cube is None:
            requested = f"{begin_year} to {end_year}"
            raise TimeConstraintOutOfBoundsException(requested)
        else:
            _check_data_availability(cube, begin_year, end_year)
            if cube.units == "unknown":
                new_cube.units = "1"
            constrained_cubes.append(new_cube)

    return constrained_cubes


def extract_region_by_geometry(cube: iris.cube.Cube, geom: shapely.Polygon):
    """
    .. versionadded:: 2.2
       Relocated from the ``proc_ants`` package, which was removed in ANTS 2.2.

    Given a cube and a geometry, extract the cube sub-region corresponding to
    that geometry.

    To get a generous bounding box for a geometry (for example, a lake),
    we buffer this geometry by a percentage of the region size.
    Two such bufferings are used, and both buffered geometries are returned:

    * The "extraction geometry" is the geometry we use to extract the cube sub region,
      using a buffer of 0.25 * region size
    * The "containment geometry" is the geometry we use to constrain the flood fill,
      using a buffer of 0.2 * region size

    Parameters
    ----------
    cube : iris.cube.Cube
        A cube to extract a sub region from
    geom : shapely.Polygon
        The geometry defining the area of the cube to extract

    Returns
    -------
    tuple[iris.cube.Cube, shapely.Polygon, shapely.Polygon, tuple]
        A tuple containing:

        * The extracted cube sub-region
        * The buffered extraction geometry
        * The buffered containment geometry
        * A tuple of slices which subset the source cube to the sub-region, as returned
          by :func:`ants.utils.cube.get_slices`

    """
    minx, miny, maxx, maxy = geom.bounds
    x = np.array([minx, minx, maxx, maxx])
    y = np.array([miny, maxy, miny, maxy])
    distances = np.sqrt((x[1:] - x[:-1]) ** 2 + (y[1:] - y[:-1]) ** 2)
    distance = distances.max()
    containment_geom = geom.buffer(distance * 0.02)
    extraction_geom = geom.buffer(distance * 0.25)

    # Slice out region corresponding to geometry (lake)
    minx, miny, maxx, maxy = extraction_geom.bounds
    slices = get_slices(cube, [miny, maxy], [minx, maxx])
    if len(slices) != 1:
        msg = "Expecting 1 slice, got {} slices".format(len(slices))
        raise RuntimeError(msg)
    slices = slices[0]
    region_cube = cube[slices]
    return region_cube, extraction_geom, containment_geom, slices


def fetch_seed_index(cube, seed):
    """
    .. versionadded:: 2.2
       Relocated from the ``proc_ants`` package, which was removed in ANTS 2.2.

    Given seed value in lat-lon, return the corresponding index within the
    cube provided.

    Parameters
    ----------
    cube: iris.cube.Cube
        Cube to find lat-lon seed point
    seed: tuple[float, float]
        Latitude, longitude point to find within the provided cube

    Returns
    -------
    tuple[int, int]
        The x, y indices indentifying the position of the seed point within the cube

    Raises
    ------
    ValueError
        If the provided seed point is not contained within the extent of the provided
        source cube domain
    """
    x, y = ants.utils.cube.horizontal_grid(cube, dim_coords=True)
    if (
        seed[1] < x.points.min()
        or seed[1] > x.points.max()
        or seed[0] < y.points.min()
        or seed[0] > y.points.max()
    ):
        msg = (
            "Seed value x,y:{} is not contained within the extent of the "
            "extracted domain: xlim [{}, {}], ylim [{}, {}]"
        )
        raise ValueError(
            msg.format(
                seed,
                x.points.min(),
                x.points.max(),
                y.points.min(),
                y.points.max(),
            )
        )
    xd = abs(x.points - seed[1]).argmin()
    yd = abs(y.points - seed[0]).argmin()
    return xd, yd

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import warnings

import ants
import dask.array as da
import iris
import iris.analysis
import numpy as np


def _remove_undesriable_attributes(cube):
    # Temporary workaround for the valid_x attributes which should likely not
    # persist a regrid operation.
    rm_attributes = ["valid_range", "valid_min", "valid_max"]
    [
        cube.attributes.pop(key, None)
        for key in list(cube.attributes.keys())
        if key in rm_attributes
    ]


def _process_cube_crs(cube):
    # Convert to ANTS equivalent crs so that regridding schemes can utilise
    # coordinate system equivelence.
    # see ants.coord_systems.as_ants_crs
    sx, _ = ants.utils.cube.horizontal_grid(cube)
    src_crs = sx.coord_system.as_ants_crs()
    cube = cube.copy(cube.lazy_data())
    sx, sy = ants.utils.cube.horizontal_grid(cube)
    sx.coord_system = src_crs
    sy.coord_system = src_crs
    ants.utils.cube.guess_horizontal_bounds(cube)
    return cube


def _is_spherical(cube):
    x, _ = ants.utils.cube.horizontal_grid(cube)
    crs = x.coord_system
    return (
        isinstance(crs, (iris.coord_systems.GeogCS, iris.coord_systems.RotatedGeogCS))
        or x.units == "degrees"
        or x.units == "radians"
    )


def _gen_regular_target(source_cube, target_grid, shape=None):
    """
    Generate a grid cube which covers the same area as the target cube only
    that it has the coordinate system of the target grid and specified shape.

    Parameters
    ----------
    source_cube : :class:`~iris.cube.Cube`
        Source cube that we wish to regularise.
    target_grid : :class:`~iris.cube.Cube`
        Target cube which is used to determine properties of the regular target
        such as coordinate coordinate system and metadata as well as data
        dtype.
    shape : tuple
        The chosen shape of the regular target.  If not specified, the shape is
        set as the same as the source cube shape so that resulting resolution
        is similar to the source.

    Returns
    -------
    : :class:`~iris.cube.Cube`
        Regular target grid which covers the same are as the source cube with
        the coordinate system of the provided target grid.

    .. note::
        This function is not sensitive to the point values of the provided
        target grid.

    """

    def gen_regular_coord(coord, size):
        # Determine whether we are using points/bounds.
        points = coord.points
        if coord.has_bounds():
            points = coord.bounds
        xmin, xmax = points.min(), points.max()

        # Generate regular points by utilising bounds if available.
        bounds = None
        if coord.has_bounds():
            bound = np.linspace(xmin, xmax, endpoint=True, num=size + 1)
            bounds = np.array([bound[:-1], bound[1:]]).T
            points = bounds.mean(axis=1)
        else:
            points = np.linspace(xmin, xmax, num=size)

        regular_coord = coord.copy(points, bounds=bounds)
        ants.utils.coord.guess_bounds(regular_coord, strict=False)
        return regular_coord

    # Derive the intermediate grid based on the overlap, not the original
    # source.
    target_area_constraint = ants.ExtractConstraint(target_grid)
    source_cube = source_cube.extract(target_area_constraint)
    source_area_constraint = ants.ExtractConstraint(source_cube)
    target_grid = target_grid.extract(source_area_constraint)

    src_x_coord, src_y_coord = ants.utils.cube.horizontal_grid(
        source_cube, dim_coords=True
    )
    dim_x = source_cube.coord_dims(src_x_coord)[0]
    dim_y = source_cube.coord_dims(src_y_coord)[0]

    if shape is None:
        shape = tuple(
            [source_cube.shape[min(dim_y, dim_x)]]
            + [source_cube.shape[max(dim_y, dim_x)]]
        )
    # Support horizontal coordinate mappings on multidimensional cubes by
    # returning the index of the mapping order
    dim_y, dim_x = np.argsort([dim_y, dim_x])

    dtype = target_grid.lazy_data().dtype

    data = da.ones(shape, dtype=dtype, chunks=shape)
    grid_cube = iris.cube.Cube(data)

    tgt_x_coord, tgt_y_coord = ants.utils.cube.horizontal_grid(
        target_grid, dim_coords=True
    )
    grid_x_coord = gen_regular_coord(tgt_x_coord, shape[dim_x])
    grid_y_coord = gen_regular_coord(tgt_y_coord, shape[dim_y])
    grid_cube.add_dim_coord(grid_y_coord, dim_y)
    grid_cube.add_dim_coord(grid_x_coord, dim_x)

    if (grid_x_coord.points.size < tgt_x_coord.points.size) or (
        grid_y_coord.points.size < tgt_y_coord.points.size
    ):
        # Note: We issue a warning as performing a linear regrid where the
        # intermediate target is lower resolution compared to the target, in
        # general defeats the point of calling TwoStage (linear is typically
        # better suited).
        # It's possible that we could consider deriving 'shape' by ALSO
        # considering the target overlap shape, not just the source overlap
        # shape (that is, the larger of the two perhaps in each dimension).
        warnings.warn(
            "Target grid ({}) is coarser than the source grid ({})."
            "Is the TwoStage intended for usage?".format(
                grid_cube.shape, target_grid.shape
            )
        )
    ants.utils.cube.derive_circular_status(grid_cube)

    return grid_cube


def _fill_outside_bounds(source, target, fill_value):
    """
    Target points outside the source domain will be assigned the provided fill
    value.

    """
    sx, sy = ants.utils.cube.horizontal_grid(source)
    tx, ty = ants.utils.cube.horizontal_grid(target)
    if sx.coord_system != tx.coord_system:
        raise ValueError(
            "Currently, source and target crs must be identical "
            "to perform extrapolation"
        )

    tx_decreasing = tx.bounds[-1, 0] < tx.bounds[0, 0]
    ty_decreasing = ty.bounds[-1, 0] < ty.bounds[0, 0]

    tx_bounds = tx.bounds
    if _is_spherical(source):
        base = np.min(sx.bounds)
        modulus = sx.units.modulus
        if np.min(tx.bounds) < base or np.max(tx.bounds) > (base + modulus):
            tx_bounds = ants.utils.ndarray.wrap_lons(
                tx_bounds, base, modulus, endpoint=False
            )

    y_outside_bounds = outside_bounds(sy.bounds, ty.bounds, ty_decreasing)
    x_outside_bounds = outside_bounds(sx.bounds, tx_bounds, tx_decreasing)
    target = fill_range(target, x_outside_bounds, fill_value, tx)
    target = fill_range(target, y_outside_bounds, fill_value, ty)
    return target


def fill_range(source_cube, indices, value, coord):
    if indices.any():
        dim = source_cube.coord_dims(coord)[0]
        my_cube = source_cube.copy()
        # use "float64" to handle NaN values
        data = my_cube.core_data().astype("float64")
        # Set specified indices to specified value
        slices = [slice(None)] * data.ndim
        slices[dim] = indices
        data[tuple(slices)] = value
        my_cube.data = data
        return my_cube
    return source_cube


def outside_bounds(bounds1, bounds2, decreasing):
    min_bound = np.min(bounds1)
    max_bound = np.max(bounds1)
    if decreasing:
        upper, lower = bounds2.T
    else:
        lower, upper = bounds2.T
    # Total overlap considered 'within'
    indices = ((lower <= max_bound) * (lower >= min_bound)) * (
        (upper <= max_bound) * (upper >= min_bound)
    )
    # # Partial overlap considered 'within' - alternative to total overlap
    # indices = (((lower <= max_bound) * (lower >= min_bound)) |
    #            ((upper <= max_bound) * (upper >= min_bound)))
    return ~indices


def _override_coord_data(source, target):
    # Iris operations are often sensitive to bit level differences to
    # coordinates so we override them (like regridder instances).
    sx = source.coord(axis="x")
    sy = source.coord(axis="y")
    tx = target[0]
    ty = target[1]
    equal_x = ants.utils.coord.relaxed_equality(sx, tx)
    equal_y = ants.utils.coord.relaxed_equality(sy, ty)
    if not equal_x or not equal_y:
        raise ValueError(
            "The given cube is not defined on the same source grid as this regridder."
        )
    sx.points = tx.points
    sy.points = ty.points
    sx.bounds = tx.bounds
    sy.bounds = ty.bounds


class _AreaWeightedRegridder(iris.analysis.AreaWeightedRegridder):
    def __init__(self, *args, **kwargs):
        """
        AreaWeighted regridder.

        The AreaWeighted approach differs from iris
        (:class:`iris.analysis.AreaWeighted`) in the following way:

        - Adheres to ANTS coordinate systems of equivalence (see
          :mod:`ants.coord_systems`).
        - Target points outside the source domain will be set to 'NaN' which
          allows us to distinguish with mask values.
        - Removal of undesirable attributes (those which are no longer relevant
          after a regrid).
        - Target points outside the source domain will be assigned a value of
          np.nan
        - ANTS ensures that np.nan values are returned unmasked (iris sometimes
          masks nan elements).

        """
        args = list(args)
        args[0] = _process_cube_crs(args[0])
        args[1] = _process_cube_crs(args[1])
        self._orig_tgt_crs = args[1].coord(axis="x").coord_system
        args[1], self._zonal_mean_cm = _zonal_mean_target(args[0], args[1])
        self._grid_staggering = args[1].attributes.get("grid_staggering", None)
        super().__init__(*args, **kwargs)

    def __call__(self, cube):
        cube = _process_cube_crs(cube)
        csrc_dtype = np.promote_types(cube.dtype, "float64")
        if csrc_dtype != cube.dtype:
            cube.data = da.array(cube.core_data(), dtype=csrc_dtype)

        # Iris area weighted regridder isn't tolerant of coordinate definitions
        # even though most iris processing will not lead to bit level identical
        # coordinates.
        _override_coord_data(cube, self._src_grid)

        result = super().__call__(cube)
        filled = _fill_outside_bounds(cube, result, np.nan)
        if filled is not None:
            result = filled
        # Distinguish between masked values and those target points beyond the
        # source extent.
        # Ensure that all nan values are recognised as such (iris area weighted
        # regrid can overlay a mask over nan values).
        if np.ma.is_masked(result.data):
            result.data.mask[np.isnan(result.data.data)] = False

        if self._grid_staggering:
            result.attributes["grid_staggering"] = self._grid_staggering
        # Remove attributes which are no longer relevant.
        _remove_undesriable_attributes(result)

        # If the target is a zonal mean, add it back to the result (iris drops
        # it).
        if self._zonal_mean_cm:
            result.add_cell_method(self._zonal_mean_cm)

        return result


class _TwoStageRegridder(object):
    """
    TwoStage regridder

    Utilises :class:`ants.regrid.rectilinear.Linear` for an intermediate regrid
    followed by the area weighted regrid using
    :class:`ants.regrid.rectilinear.AreaWeighted`.

    """

    def __init__(self, *args, **kwargs):
        args = list(args)
        args[0] = _process_cube_crs(args[0])
        args[1] = _process_cube_crs(args[1])

        # Instantiate the iris AreaWeightedRegridder with source-target or
        # intermediate_target-target depending on the coordinate systems.
        source_crs = args[0].coord(axis="x").coord_system.as_ants_crs()
        target_crs = args[1].coord(axis="x").coord_system.as_ants_crs()
        self._twostage = compare_coordinate_reference_systems(source_crs, target_crs)
        if self._twostage:
            intermediate_target = _gen_regular_target(args[0], args[1])
            self._linear_regridder = Linear().regridder(args[0], intermediate_target)
            args[0] = intermediate_target
            self._iris_area_regridder = _AreaWeightedRegridder(*args, **kwargs)
        else:
            self._iris_area_regridder = _AreaWeightedRegridder(*args, **kwargs)

    def __call__(self, cube):
        cube = _process_cube_crs(cube)

        if self._twostage:
            intermediate_target = self._linear_regridder(cube)
            result = self._iris_area_regridder(intermediate_target)
        else:
            result = self._iris_area_regridder(cube)
        # Remove attributes which are no longer relevant.
        _remove_undesriable_attributes(result)
        return result


def compare_coordinate_reference_systems(source_crs, target_crs):
    """return True if the two CRSs are not equivalent and
    therefore a two stage regrid is required"""
    return source_crs != target_crs


class AreaWeighted(iris.analysis.AreaWeighted):
    def regridder(self, src_grid_cube, target_grid_cube):
        """
        Creates an area-weighted regridder to perform regridding from the
        source grid to the target grid.

        Typically you should use :meth:`iris.cube.Cube.regrid` for
        regridding a cube. There are, however, some situations when
        constructing your own regridder is preferable. These are detailed in
        the :ref:`user guide <caching_a_regridder>`.

        - This regridder automatically converts the target to zonal mean data
          if required.

        Parameters
        ----------
        src_grid_cube : :class:`~iris.cube.Cube`
            defining the source grid.
        target_grid_cube : :class:`~iris.cube.Cube`
            defining the target grid.

        Returns
        -------
        ~collections.abc.Callable
           Callable with the interface `callable(cube)`

        """
        return _AreaWeightedRegridder(src_grid_cube, target_grid_cube, mdtol=self.mdtol)


class TwoStage(AreaWeighted):
    """
    Two-stage regridding scheme.

    In the case where the source an target are the same coordinate system,
    the a single step area weighted regrid is performed between the provided
    source and target.
    When this is not the case, bilinear interpolation occurs between the
    original source and an intermediate grid.  The intermediate grid has the
    same dimension size as the original source, covering the same extent, but
    with coordinate system matching the target grid.  Following this, an area
    weighted regrid is performed between this intermediate grid and the target
    grid provided.

    - This regridder automatically converts the target to zonal mean data if
      required.

    """

    def regridder(self, src_grid_cube, target_grid_cube):
        """
        Creares a two-stage regridding scheme.

        Parameters
        ----------
        src_grid_cube : :class:`~iris.cube.Cube`
            Definning the source grid.
        target_grid_cube : :class:`~iris.cube.Cube`
            Definning the target grid.

        Returns
        -------
        ~collections.abc.Callable
           Callable with the interface `callable(cube)`

           where `cube` is a cube with the same grid as `src_grid_cube`
           that is to be regridded to the `target_grid_cube`.

        """
        return _TwoStageRegridder(src_grid_cube, target_grid_cube, mdtol=self.mdtol)

    def __repr__(self):
        return "{}(mdtol={})".format(self.__class__.__name__, self.mdtol)


def _zonal_mean_target(source, target):
    """
    Convert target grid into a zonal mean definition.

    Convert to a zonal mean target where:
    - Source and target have global extent in the 'x' axis.
    - Source has only one column ('x').

    """
    new_target = target
    sx, _ = ants.utils.cube.horizontal_grid(source)
    tx, _ = ants.utils.cube.horizontal_grid(target)

    global_x = ants.utils.cube.is_global(
        source, x_axis_only=True
    ) and ants.utils.cube.is_global(target, x_axis_only=True)
    same_crs = sx.coord_system.as_ants_crs() == tx.coord_system.as_ants_crs()

    zonal_mean_cm = None
    if global_x and sx.points.size == 1 and same_crs:
        if tx.points.size != 1:
            slices = [slice(None)] * target.ndim
            slices[target.coord_dims(tx)[0]] = slice(0, 1)
            new_target = target[tuple(slices)]
            ntx, _ = ants.utils.cube.horizontal_grid(new_target)
            ntx.bounds = [tx.bounds.min(), tx.bounds.max()]
            ntx.points = np.mean(ntx.bounds)
            warnings.warn("Output converted to zonal mean.")

        zonal_mean_cm = iris.coords.CellMethod("mean", coords=tx.name())
        if zonal_mean_cm not in new_target.cell_methods:
            new_target.add_cell_method(zonal_mean_cm)

    return new_target, zonal_mean_cm


class _RectilinearRegridder(iris.analysis.RectilinearRegridder):
    def __init__(self, *args, **kwargs):
        args = list(args)
        args[0] = _process_cube_crs(args[0])
        args[1] = _process_cube_crs(args[1])
        self._orig_tgt_crs = args[1].coord(axis="x").coord_system
        args[1], self._zonal_mean_cm = _zonal_mean_target(args[0], args[1])

        super(_RectilinearRegridder, self).__init__(*args, **kwargs)
        self._grid_staggering = args[1].attributes.get("grid_staggering", None)

    def __call__(self, src):
        src = _process_cube_crs(src)
        res = super(_RectilinearRegridder, self).__call__(src)
        if self._grid_staggering:
            res.attributes["grid_staggering"] = self._grid_staggering
        # Remove attributes which are no longer relevant.
        _remove_undesriable_attributes(res)
        # If the target is a zonal mean, add it back to the result (iris drops
        # it).
        if self._zonal_mean_cm:
            res.add_cell_method(self._zonal_mean_cm)
        # If NaNs are introduced by extrapolation, raise a warning
        if (
            self.extrapolation_mode == "nan"
            and np.all(~np.isnan(src.data))
            and np.any(np.isnan(res.data))
        ):
            warnings.warn("NaN values introduced by extrapolation")

        return res


class _RectilinearInterpolator(iris.analysis.RectilinearInterpolator):
    def __init__(self, *args, **kwargs):
        args = list(args)

        # Since we process the cube crs, the coord passed-in may not be equal
        # after we have done so.  This means matching them first.
        args[1] = [args[0].coord(coord).name() for coord in args[1]]
        args[0] = _process_cube_crs(args[0])
        super(_RectilinearInterpolator, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        res = super(_RectilinearInterpolator, self).__call__(*args, **kwargs)
        # Remove attributes which are no longer relevant.
        _remove_undesriable_attributes(res)
        return res


class Linear(iris.analysis.Linear):
    def __init__(self, extrapolation_mode="nan"):
        """
        Linear interpolation and regridding scheme.

        Suitable for interpolating or regridding over one or more orthogonal
        coordinates.  This class acts as a wrapper to the iris
        :class:`iris.analysis.Linear`, with the following differences:

        - Default extrapolation mode to 'nan'.
        - Adheres to ANTS coordinate systems of equivalence (see
          :mod:`ants.coord_systems`).
        - This regridder automatically converts the target to zonal mean data
          if required.

        """
        super(Linear, self).__init__(extrapolation_mode=extrapolation_mode)
        self._extrapolation = self._normalised_extrapolation_mode()

    def regridder(self, src_grid, target_grid):
        """
        Creates a linear regridder to regrid from the source to target grid.
        This regridder automatically converts the target to zonal mean data if
        required.

        Parameters
        ----------
        src_grid : :class:`~iris.cube.Cube`
           Defining the source grid.
        target_grid : :class:`~iris.cube.Cube`
            Defining the target grid.

        Returns
        -------
        ~collections.abc.Callable
           Callable with the interface `callable(cube)`

           where `cube` is a cube with the same grid as `src_grid`
           that is to be regridded to the `target_grid`.


        """
        return _RectilinearRegridder(
            src_grid, target_grid, "linear", self._extrapolation
        )

    def interpolator(self, cube, coords):
        """
        Creates a linear interpolator.

        Interpolation is to perform over the given :class:`~iris.cube.Cube`
        specified by the dimensions of the given coordinates.

        Parameters
        ----------
        cube : :class:`iris.cube.Cube`
            Source to be interpolated.
        coords : ~collections.abc.Iterable
            The names or coordinate instances that are to be interpolated
            over.

        Returns
        -------
        ~collections.abc.Callable
            Callable with the interface:
            `callable(sample_points, collapse_scalar=True)`

            where `sample_points` is a sequence containing an array of values
            for each of the coordinates passed to this method, and
            `collapse_scalar` determines whether to remove length one
            dimensions in the result cube caused by scalar values in
            `sample_points`.

        """
        return _RectilinearInterpolator(cube, coords, "linear", self._extrapolation)

    def __repr__(self):
        return "{}(extrapolation_mode={})".format(
            self.__class__.__name__, self._extrapolation
        )

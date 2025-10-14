# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import copy
import warnings
from functools import partial

import ants.utils
import iris
import numpy as np
from iris.coords import AuxCoord, DimCoord
from iris.cube import Cube

"""
Routines for putting data on new strata (aka. isosurfaces), often in the
Z direction.

"""


try:
    import stratify

    _STRATIFY_IMPORT_ERROR = False
except Exception as _STRATIFY_IMPORT_ERROR:
    stratify = None
    msg = (
        ' {}\nUnable to import "stratify", proceeding without the '
        "capabilities it provides.  See install.rst"
    )
    warnings.warn(msg.format(str(_STRATIFY_IMPORT_ERROR)))


def _copy_coords_without_z_dim(src, tgt, z_dim):
    """
    Helper function to copy across non z-dimension coordinates between cubes.

    Parameters
    ----------
    src : :class:`~iris.cube.Cube`
        Incoming cube containing the coordinates to be copied from.

    tgt : :class:`~iris.cube.Cube`
        Outgoing cube for the coordinates to be copied to.

    z_dim : int
        Dimension within the `src` cube that is the z-dimension.
        This dimension will not be copied. For example, the incoming
        z-dimension cube has model level_height, whilst the outgoing
        z-dimension cube has pressure.

    """
    # Copy across non z-dimension coordinates.
    for coord in src.dim_coords:
        [dim] = src.coord_dims(coord)
        if dim != z_dim:
            tgt.add_dim_coord(coord.copy(), dim)

    for coord in src.aux_coords:
        dims = src.coord_dims(coord)
        if z_dim not in dims:
            tgt.add_aux_coord(coord.copy(), dims)

    for coord in src.derived_coords:
        dims = src.coord_dims(coord)
        if z_dim not in dims:
            tgt.add_aux_coord(coord.copy(), dims)


def _relevel(cube, src_levels, tgt_levels, interpolator, axis):
    """
    General interface for interpolation algorithms

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube`
        The phenomenon data to be re-levelled.

    src_levels : :class:`~iris.coords.Coord`
        Describes the source levels of the `cube` that will be interpolated
        over. The `src_levels` must be in the same system as the `tgt_levels`.
        The dimensions of `src_levels` must be broadcastable to the dimensions
        of the `cube`.
        Note that, the coordinate name containing the source levels in the
        `cube` may be provided.

    tgt_levels : :class:`~iris.coords.Coord`
        Describes the target levels of the `cube` to be interpolated to. The
        `tgt_levels` must be in the same system as the `src_levels`. The
        dimensions of the `tgt_levels` must be broadcastable to the dimensions
        of the `cube`, except in the nominated axis of interpolation.

    axis : int
        The axis of interpolation.

    interpolator : ~collections.abc.Callable
        The interpolator to use when computing the interpolation. The function
        will be passed the following positional arguments::

            (tgt-data, src-data, cube-data, axis-of-interpolation)

    """
    # The following is a code smell.  Changes will be required to
    # python-stratify to allow a more Pythonic API.
    interpolator_name = (
        getattr(getattr(interpolator, "func", None), "__name__", None)
        or getattr(interpolator, "__name__")
    ).lower()
    uses_bounds = "conservative" in interpolator_name

    tgt_aux_dims = axis
    if tgt_levels.points.ndim != 1:
        dim_delta = cube.data.ndim - tgt_levels.points.ndim
        tgt_aux_dims = list(range(cube.data.ndim))[dim_delta:]

    # Now perform the interpolation by providing either points or bounds
    # depending on the family of algorithm.
    if uses_bounds:
        src_data = src_levels.bounds
        tgt_data = tgt_levels.bounds
        msg = (
            'coord "{}" does not have bounds.  Interpolation method "{}" '
            "requires bounds."
        )
        msg = msg.format(src_levels.name(), interpolator_name)
        if src_data is None:
            raise ValueError("Source " + msg)
        if tgt_data is None:
            raise ValueError("Target " + msg)
    else:
        src_data = src_levels.points
        tgt_data = tgt_levels.points

    new_data = interpolator(tgt_data, src_data, cube.data, axis=axis)

    # Create a result cube with the correct shape and metadata.
    result = Cube(new_data, **cube.copy().metadata._asdict())

    # Copy across non z-dimension coordinates from the source cube
    # to the result cube.
    _copy_coords_without_z_dim(cube, result, axis)

    kwargs = dict(
        standard_name=src_levels.standard_name,
        long_name=src_levels.long_name,
        var_name=src_levels.var_name,
        units=src_levels.units,
        attributes=src_levels.attributes,
    )

    # Add our new interpolated coordinate to the result cube.
    try:
        # Ensure we do not promote the interpolation coordinate to a dimension
        # coordinate if the target grid doesn't define it as such.
        if isinstance(tgt_levels, iris.coords.DimCoord):
            coord = DimCoord(tgt_levels.points, bounds=tgt_levels.bounds, **kwargs)
            result.add_dim_coord(coord, axis)
        else:
            coord = AuxCoord(tgt_levels.points, bounds=tgt_levels.bounds, **kwargs)
            result.add_aux_coord(coord, axis)
    except ValueError:
        # Attach the data to the trailing dimensions.
        coord = AuxCoord(tgt_levels.points, bounds=tgt_levels.bounds, **kwargs)
        result.add_aux_coord(coord, tgt_aux_dims)

    return result


def scalar_coord(cube, coord_name):
    """Determine whether coordinate is scalar."""
    found_coord = None
    for coord in cube.coords(coord_name):
        if not cube.coord_dims(coord):
            found_coord = coord
            break
    return found_coord


def _guess_axis_interpolation(cube):
    dims = cube.coord_dims("model_level_number")
    if len(dims) != 1:
        raise ValueError(
            "Expecting only a single axis of interpolation, " "got {}".format(len(dims))
        )
    return dims


def _fetch_vertical_grid_definition(cube, zcoord):
    """
    Slice the cube along dimensions which vary with zcoord and remove any
    scalar coordinates that result from such slicing as well any coordinates
    that vary along dimensions not shared by zcoord (for example, the removal
    of aux factories where we are interpolating between level_heights).

    """
    ants.utils.cube.sanitise_auxcoords(cube)

    slices = cube.coord_dims(zcoord)
    z_slices = [0] * cube.ndim
    for s in slices:
        z_slices[s] = slice(None)
    ref_grid = cube[tuple(z_slices)]

    # Remove newly created scalar coordinates as a result of the slicing
    # as these are independent of the vertical grid definition.
    ref_scalars = filter(
        lambda x: x, [scalar_coord(ref_grid, coord) for coord in ref_grid.coords()]
    )
    ref_scalars = [coord.name() for coord in ref_scalars]
    cube_scalars = filter(
        lambda x: x, [scalar_coord(cube, coord) for coord in cube.coords()]
    )
    cube_scalars = [coord.name() for coord in cube_scalars]
    diff_scalars = set(ref_scalars) - set(cube_scalars)
    for coord in diff_scalars:
        ref_grid.remove_coord(coord)

    # Also remove any coordinates which vary along dimensions beyond what
    # zcoord varies.
    for coord in ref_grid.coords():
        if len(ref_grid.coord_dims(coord.name())) != len(cube.coord_dims(coord.name())):
            ref_grid.remove_coord(coord.name())
    for factory in ref_grid.aux_factories:
        if factory.standard_name != zcoord.name():
            ref_grid.remove_aux_factory(factory)

    return ref_grid


def _get_source_target_pair(source, target):
    """
    Fetch the target grid definition which is compatible with the source.

    source and target are returned transposed in a consistent order and
    suitable for use with stratify.  That is, to make the dimension to which
    the vertical maps, the trailing ones.

    """
    # First work with a copy of source to ensure that any transpose or
    # re-ordering doesn't affect the original dataset.
    source = source.copy(source.lazy_data())
    target = target.copy(target.lazy_data())

    coord_names = [
        "altitude",
        "height",
        "level_height",
        "air_pressure",
        "level_pressure",
    ]
    # Determine if a suitable vertical coordinate can be found.
    for coord_name in coord_names:
        szcoord = source.coords(coord_name)
        tzcoord = None
        if len(szcoord) == 1:
            szcoord = szcoord[0]
            tzcoord = target.coord(szcoord.name())
            break

    ref_target = None
    if szcoord:
        # Ensure consistent units between target and source coordinates.
        szcoord.convert_units(tzcoord.units)

        # Fetch the vertical grid definitions.
        ref_target = _fetch_vertical_grid_definition(target, tzcoord)
        ref_source = _fetch_vertical_grid_definition(source, szcoord)
        if ref_source.ndim != ref_target.ndim:
            msg = (
                "Expecting the source and target vertical grid to vary "
                "over the same number of dimensions, {} != {}"
            )
            raise RuntimeError(msg.format(ref_source.ndim, ref_target.ndim))

        # Ensure that the vertical grid definitions have the same dimension
        # mapping along all but the axis of interpolation.
        src_axis = _guess_axis_interpolation(ref_source)
        tgt_axis = _guess_axis_interpolation(ref_target)
        src_dim_coords = ref_source.coords(dim_coords=True)
        tgt_dim_coords = ref_target.coords(dim_coords=True)
        src_names = [src_dim_coords[i].name() for i in list(range(len(src_dim_coords)))]
        tgt_names = [tgt_dim_coords[i].name() for i in list(range(len(tgt_dim_coords)))]

        # Exclude those along the axis of interpolation.
        src_names_no_axis = [
            name for name in src_names if ref_source.coord_dims(name) != src_axis
        ]
        tgt_names_no_axis = [
            name for name in tgt_names if ref_target.coord_dims(name) != tgt_axis
        ]
        diff_names = set(src_names_no_axis).symmetric_difference(set(tgt_names_no_axis))
        if diff_names:
            msg = (
                "Expecting common dimension coordinates between both "
                "source and target along those which the vertical grid "
                "vary (except the axis of interpolation).  "
                "This is neccessary to perform consistency checks."
                "The following were not common: {}."
            )
            raise RuntimeError(msg.format(diff_names))

        # Transpose the target to make consistent with the source.
        transpose = [tgt_names.index(name) for name in src_names_no_axis]
        transpose.insert(src_axis[0], tgt_axis[0])
        ref_target.transpose(transpose)
        ants.utils.cube.sanitise_auxcoords(ref_target)
        assert _guess_axis_interpolation(ref_source) == _guess_axis_interpolation(
            ref_target
        )

        # Reorder target dimensions direction to make consistent with source.
        src_direction = [
            src_coord.points[-1] > src_coord.points[0] for src_coord in src_dim_coords
        ]
        tgt_direction = [
            ref_target.coord(src_name).points[-1] > ref_target.coord(src_name).points[0]
            for src_name in src_names
        ]
        slices = [
            slice(None, None, -1) if src_d != tgt_d else slice(None)
            for src_d, tgt_d in zip(src_direction, tgt_direction)
        ]
        ref_target = ref_target[tuple(slices)]

        # Fetch fresh references to the current transposed grids.
        szcoord = ref_source.coord(szcoord.name())
        tzcoord = ref_target.coord(szcoord.name())

        # Ensure we fall over if the vertical coordinate varies over
        # coordinates relating to the horizontal domain - which suggest
        # incompatibility.
        consistent_coords = [
            ref_source.coords("surface_altitude"),
            ref_source.coords("surface_pressure"),
            ref_source.coords(axis="x"),
            ref_source.coords(axis="y"),
        ]
        for src_coord in consistent_coords:
            if src_coord:
                src_coord = src_coord[0]
                tgt_coord = ref_target.coords(src_coord.name())
                if tgt_coord:
                    tgt_coord = tgt_coord[0]
                    if src_coord != tgt_coord:
                        msg = (
                            "The {} coordinate of source and target do "
                            "not agree when the vertical coordinate varies "
                            "over it.  Case not currently supported."
                        )
                        raise RuntimeError(msg.format(src_coord.name()))

    return source, szcoord, ref_target, tzcoord


def _vertical_regrid(source, target, interpolator):
    """
    Vertically regrid between source and target.

    Parameters
    ----------
    source : :class:`~iris.cube.Cube`
        Defining the source dataset.
    target : :class:`~iris.cube.Cube`
        Defining the target vertical coordinates.

    Returns
    -------
    : :class:`~iris.cube.Cube`
        The source interpolated to the vertical levels as defined in the
        target.

    Notes
    -----
    The model_level_number is used to infer the axis of interpolation.

    Warnings
    --------
    Z variation is generally MUCH greater than horizontal variation.  This
    means that true 3D interpolation is not generally wanted and we can treat
    horizontal and vertical regridding as separate in cases where vertical
    information is invariant over XY as well as when variant over XY.

    """
    result = source
    # Fetch a suitable source-target pair for stratify.
    source, szcoord, target, tzcoord = _get_source_target_pair(source, target)

    if tzcoord and (
        (szcoord.points.shape != tzcoord.points.shape)
        or not ants.utils.ndarray.allclose(szcoord.points, tzcoord.points)
    ):
        if "pressure" in tzcoord.name():
            msg = "Currently pressure coordinates ({}) are not supported"
            raise RuntimeError(msg.format(tzcoord.name()))

        # Re-order the source to make suitable for use with stratify.
        zdim = source.coord_dims(szcoord)
        src_transpose = set(range(source.ndim)) - set(zdim)
        src_transpose = list(src_transpose) + list(set(zdim))
        source.transpose(src_transpose)
        ants.utils.cube.sanitise_auxcoords(source)

        # Re-order the target to make suitable for use with stratify.
        zdim = target.coord_dims(tzcoord)
        tgt_transpose = set(range(target.ndim)) - set(zdim)
        tgt_transpose = list(tgt_transpose) + list(set(zdim))
        target.transpose(tgt_transpose)
        ants.utils.cube.sanitise_auxcoords(target)

        axis = _guess_axis_interpolation(source)
        result = _relevel(source, szcoord, tzcoord, interpolator, axis[0])

        # Re-apply the coordinate and those associated with a hybrid-height/
        # hybrid-pressure coordinate onto the result cube.
        existing_factories = [factory.standard_name for factory in result.aux_factories]
        for hybrid_factory in target.aux_factories:
            dependent_coords = [
                coord.name()
                for coord in hybrid_factory.dependencies.values()
                if coord is not None
            ] + [hybrid_factory.standard_name]
            if tzcoord.name() not in dependent_coords:
                # Hybrid factory isn't dependent on our interpolation coord.
                continue
            if hybrid_factory.standard_name in existing_factories:
                # Hybrid factory already exists.
                continue

            factory = copy.deepcopy(hybrid_factory)
            result.remove_coord(tzcoord.name())
            dependents = factory.dependencies
            for name, coord in dependents.items():
                if coord is None:
                    continue
                dims = target.coord_dims(coord.name())
                dims = np.array(dims) + (source.ndim - target.ndim)

                # Remove coordinate if present.
                try:
                    result.remove_coord(coord.name())
                except iris.exceptions.CoordinateNotFoundError:
                    pass

                # Re-apply coordinate as found in the factory.
                try:
                    if isinstance(coord, iris.coords.DimCoord):
                        result.add_dim_coord(coord, dims)
                    else:
                        result.add_aux_coord(coord, dims)
                except ValueError:
                    result.add_aux_coord(coord, dims)
            result.add_aux_factory(factory)

        # Add all target coordinates onto the result cube which vary along this
        # axis of interpolation (that are not associated with a aux factory).
        target_axis = _guess_axis_interpolation(target)
        for coord in target.coords():
            dims = target.coord_dims(coord)
            if dims == target_axis and len(result.coords(coord.name())) == 0:
                try:
                    result.add_dim_coord(coord.copy(), axis)
                except ValueError:
                    # Coordinate mapped to this dimension already.
                    result.add_aux_coord(coord.copy(), axis)

        # Transpose to its original mapping.
        invert_transpose = [
            src_transpose.index(ord) for ord in list(range(source.ndim))
        ]
        result.transpose(invert_transpose)
        ants.utils.cube.sanitise_auxcoords(result)
    return result


class StratifyInterpolator(object):
    """
    Stratification interpolator.

    """

    def __init__(self, src_grid, tgt_grid, interpolator):
        """
        Return a stratify regridder object.

        Parameters
        ----------
        interpolation : str
            Interpolation schemes include, 'linear', optional

        """
        self._interpolator = interpolator
        self._tgt_grid = tgt_grid

    def __call__(self, src):
        """
        Regrid the provided source.

        Parameters
        ----------
        src :  :class:`~iris.cube.Cube`
            Source dataset to be regridded.

        Returns
        -------
        : :class:`~iris.cube.Cube`
            Interpolated result.

        """
        return _vertical_regrid(src, self._tgt_grid, self._interpolator)


class _StratifyScheme(object):
    def __init__(self):
        if stratify is None:
            raise _STRATIFY_IMPORT_ERROR


class _StratifyPointsScheme(_StratifyScheme):
    def regridder(self, src_grid, tgt_grid):
        """
        Return a vertical regridder callable to regrid from source to target.

        Parameters
        ----------
        src_grid : :class:`~iris.cube.Cube`
           Defining the source grid.
        tgt_grid : :class:`~iris.cube.Cube`
            Defining the target grid.

        Returns
        -------
        ~collections.abc.Callable
           Callable with the interface `callable(cube)`

           where `cube` is a cube with the same grid as `src_grid` and is to
           be regridded to the `tgt_grid`.

        """
        interpolator = partial(
            stratify.interpolate,
            interpolation=self.INTERPOLATION,
            extrapolation=self._extrapolation,
        )
        return StratifyInterpolator(src_grid, tgt_grid, interpolator)

    def __repr__(self):
        return "{}(extrapolation={})".format(
            self.__class__.__name__, self._extrapolation
        )


class Linear(_StratifyPointsScheme):
    """
    Linear regridding scheme.

    """

    INTERPOLATION = "linear"

    def __init__(self, extrapolation="linear"):
        """
        Return a Linear regridder object.

        Parameters
        ----------
        extrapolation : :obj:`str`, optional
            Extrapolation modes include, 'nearest', 'linear' and 'nan'.

        """
        self._extrapolation = extrapolation


class Nearest(_StratifyPointsScheme):
    """
    Nearest neighbour regridding scheme.

    """

    INTERPOLATION = "nearest"

    def __init__(self, extrapolation="nearest"):
        """
        Return a Nearest regridder object.

        Parameters
        ----------
        extrapolation : :obj:`str`, optional
            Extrapolation modes include, 'nearest', 'linear' and 'nan'.

        """
        self._extrapolation = extrapolation


class Conservative(_StratifyScheme):
    """
    Conservative regridding scheme.

    """

    def regridder(self, src_grid, tgt_grid):
        """
        Return a conservative vertical interpolator.

        A callable is returned for performing vertical interpolation between
        a specified source and target.  This is done via the regridding
        interface to iris (iris.regrid(target, scheme)).

        Parameters
        ----------
        src_grid : :class:`~iris.cube.Cube`
           Defining the source grid.
        tgt_grid : :class:`~iris.cube.Cube`
            Defining the target grid.

        Returns
        -------
        ~collections.abc.Callable
           Callable with the interface `callable(cube)`

           where `cube` is a cube with the same grid as `src_grid` and is to
           be nterpolated to `tgt_grid`.

        """
        interpolator = stratify.interpolate_conservative
        return StratifyInterpolator(src_grid, tgt_grid, interpolator)

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)

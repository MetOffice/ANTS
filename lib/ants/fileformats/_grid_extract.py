# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
This module is intended to capture the merge logic required to return a single
grid via the ants.io.load.load_grid interface.

"""
import ants
import dask.array as da
import iris
import numpy as np


def _has_coord(cubes, axis):
    res = []
    for cube in cubes:
        if cube.coords(axis=axis):
            res.append(cube)
    return res


def _get_first_cube(cubes):
    if cubes:
        cubes = cubes[0]
    return cubes


def _add_coord(cube, coord, dims):
    if not dims:
        dims = None
    if isinstance(coord, iris.coords.DimCoord):
        if dims:
            cube.add_dim_coord(coord, dims)
        else:
            cube.add_aux_coord(coord, dims)
    else:
        cube.add_aux_coord(coord, dims)


def _add_vertical(vertical_def, return_cube):
    # Add vertical definition if present.
    # Where present, the return cube must be replaced as the shape will
    # have changed.
    original_return_cube = return_cube.copy()
    shape = vertical_def.shape + return_cube.shape
    ret_data = da.zeros(shape, chunks=shape, dtype=return_cube.dtype)
    return_cube = iris.cube.Cube(ret_data)

    for h_coord in original_return_cube.coords():
        dims = original_return_cube.coord_dims(h_coord)
        if dims:
            dims = (np.array(dims) + 1).tolist()
        _add_coord(return_cube, h_coord, dims)

    for v_coord in vertical_def.coords():
        dims = vertical_def.coord_dims(v_coord)
        _add_coord(return_cube, v_coord, dims)
    return return_cube


def _add_surface_altitude(surface_altitude, return_cube):
    # Add surface altitude if present.
    sa_y, sa_x = (surface_altitude.coord(axis="y"), surface_altitude.coord(axis="x"))
    h_y, h_x = (return_cube.coord(axis="y"), return_cube.coord(axis="x"))
    if (sa_y != h_y) or (sa_x != h_x):
        msg = (
            "Surface altitude not compatible with the existing "
            "horizontal grid definition."
        )
        raise ValueError(msg)
    surf_alt_coord = iris.coords.AuxCoord(
        points=surface_altitude.data,
        units=surface_altitude.units,
        standard_name=surface_altitude.standard_name,
    )

    # Make sure we map it to the correct dimensions.
    xdim = return_cube.coord_dims(return_cube.coord(axis="x"))[0]
    ydim = return_cube.coord_dims(return_cube.coord(axis="y"))[0]
    xsadim = surface_altitude.coord_dims(sa_x)[0]
    ysadim = surface_altitude.coord_dims(sa_y)[0]
    if (ydim > xdim) is not (ysadim > xsadim):
        points = surf_alt_coord.points.transpose()
        bounds = surf_alt_coord.bounds.transpose((1, 0))
        surf_alt_coord = surf_alt_coord.copy(points, bounds=bounds)
    mapping = (ydim, xdim)
    if ydim > xdim:
        mapping = (xdim, ydim)
    return_cube.add_aux_coord(surf_alt_coord, mapping)


def _check_hybrid_height(return_cube):
    # Add hybrid height factory if appropriate.
    # This is it's own independent step from 'add_surface_altitude', as the
    # surface altitude may have been present from the very beginning (i.e.
    # it could have been the reference cube not a merging component).
    if (
        len(return_cube.coords("surface_altitude")) > 0
        and len(return_cube.aux_factories) == 0
        and len(return_cube.coords("level_height")) > 0
    ):
        hybrid_height = iris.aux_factory.HybridHeightFactory(
            delta=return_cube.coord("level_height"),
            sigma=return_cube.coord("sigma"),
            orography=return_cube.coord("surface_altitude"),
        )
        return_cube.add_aux_factory(hybrid_height)


def extract_grid(cubes):
    """Merge a set of components to return a single grid definition."""

    # Check there are no conflicting coordinates.
    ref_coords = cubes[0].coords()
    for cube in cubes:
        for coord in ref_coords:
            if cube.coords(coord.name()) and not ants.utils.coord.relaxed_equality(
                coord, cube.coord(coord.name())
            ):
                msg = "Unable to resolve a single grid, conflicting " "coordinate: {}"
                raise ValueError(msg.format(coord.name()))

    # Pull out horizontal, vertical and orography components.
    surface_altitude = cubes.extract("surface_altitude")
    vertical_def = cubes.extract("Model vertical definition") or _has_coord(cubes, "z")
    horizontal_def = (
        surface_altitude or cubes.extract("Model Grid") or _has_coord(cubes, "x")
    )
    surface_altitude = _get_first_cube(surface_altitude)
    vertical_def = _get_first_cube(vertical_def)
    horizontal_def = _get_first_cube(horizontal_def)

    # The return cube is what we return from the function and so is updated
    # and or replaced as we merge various components.
    return_cube = horizontal_def or vertical_def

    # Add vertical definition if present.
    if vertical_def and (return_cube != vertical_def):
        return_cube = _add_vertical(vertical_def, return_cube)

    # Add surface altitude if present.
    if surface_altitude:
        _add_surface_altitude(surface_altitude, return_cube)

    # Add hybrid height factory if appropriate.
    if return_cube:
        _check_hybrid_height(return_cube)

    return_cube.rename(None)
    return_cube.units = None
    return_cube = return_cube.copy(
        da.zeros(return_cube.shape, chunks=return_cube.shape, dtype=return_cube.dtype)
    )
    return return_cube

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

"""
Tools for generating the template required for saving ancillary files.

"""
import itertools
import re

import ants
import iris
import numpy as np

from . import time_headers

GRIDS = {"newdynamics": 3, "endgame": 6}
"""dict: Map of model formulation to grid staggering fixed length header value.

Used in saving ancillaries, to set the grid staggering in the fixed length header."""


def _ancil_version():
    """
    Parse the ants version into a form suitable for the model version
    element of the fixed length header.

    The convention is as follows:
        (100 * release_number) + subrelease
    For example, ants version 1.2 would become 102.

    """
    version_identity = [int(v) for v in re.findall(r"(\d+).{0,1}", ants.__version__)]
    version = 0
    if version_identity[0] > 0:
        version = 100 * version_identity[0]
    if len(version_identity) > 1:
        version += version_identity[1]

    return version


def _get_base_headers(cubes, field):
    # Base template
    headers = {}
    headers["fixed_length_header"] = {
        "data_set_format_version": 20,  # for MASS storage: always 20
        # for ancillaries
        "sub_model": 1,  # Atmosphere
        "dataset_type": 4,  # Ancillary
        "vert_coord_type": 1,  # Hybrid heights
        "model_version": _ancil_version(),  # version of ancillary program
    }
    headers["integer_constants"] = {
        "num_times": 1,  # Workaround for xconv
        "num_field_types": len(cubes),
        "num_cols": field.lbnpt,
        "num_rows": field.lbrow,
    }
    headers["real_constants"] = {}
    return headers


def _unvertical_coords(cube):
    """Returns iterator over the non-vertical coordinates of cube."""
    return (
        coord for coord in cube.coords() if iris.util.guess_coord_axis(coord) != "Z"
    )


def _check_non_vertical_coords_f03_compatible(cubes):
    """Raise exception if cubes look like they are incompatible with F03."""
    refcube = cubes[0]
    refcube_coords_names = set(coord.name() for coord in _unvertical_coords(refcube))
    msg = "Currently, only support writing cubes with identical coordinates."

    for cube in cubes:
        cube_coords_names = set(coord.name() for coord in _unvertical_coords(cube))
        missing_coords = cube_coords_names.symmetric_difference(refcube_coords_names)
        if missing_coords:
            msg = "{}  {} coordinates not common to all cubes.".format(
                msg, " ".join(missing_coords)
            )
            raise RuntimeError(msg)
        for coord in _unvertical_coords(cube):
            try:
                if not ants.utils.coord.relaxed_equality(
                    coord, refcube.coord(coord.name())
                ):
                    msg = "{}  {} not identical in all cubes.".format(msg, coord.name())
                    raise RuntimeError(msg)
            except TypeError:
                raise RuntimeError(
                    f"Invalid values found in {coord.name()} coordinate."
                ) from None


def _get_grid(cubes):
    _check_non_vertical_coords_f03_compatible(cubes)

    grids = [
        cube.attributes["grid_staggering"]
        for cube in cubes
        if "grid_staggering" in cube.attributes
    ]
    unique_grids = set(grids)
    # Check grid staggering is consistent across all cubes
    grid_check = len(grids) != 0 and len(grids) != len(cubes)
    if grid_check or len(unique_grids) > 1:
        msg = "Cubes provided are defined with different grid " "staggering: ({})"
        raise RuntimeError(msg.format(grids))
    try:
        grid = unique_grids.pop()
    except KeyError:
        grid = GRIDS["endgame"]
    return grid


def _set_grid_definition(headers, grid, field):
    """
    Sets the grid definition for standard grids or rotated pole grids.

    Uses grid to specify the grid staggering and the provided field to
    determine whether the grid is rotated, and to populate grid
    information.

    """
    headers["fixed_length_header"]["grid_staggering"] = grid
    # Horizontal grid type
    horiz_grid_type = field.lbhem
    if field.is_rotated:
        horiz_grid_type += 100

    headers["fixed_length_header"]["horiz_grid_type"] = horiz_grid_type

    # REAL CONSTANTS
    (regular_x, regular_y) = field.is_regular
    if regular_x:
        headers["real_constants"]["col_spacing"] = field.bdx
        # Longitude of first column in degrees (longitudes in range 0-360)
        start_lon = field.bzx + field.bdx
        headers["real_constants"]["start_lon"] = start_lon
    else:
        if grid in GRIDS.values():
            headers["column_dependent_constants"] = {
                "dims": (len(field.x), None),
                "lambda_p": list(field.x),
            }
        else:
            msg = (
                'Can only derive "x" values for variable resolution '
                "grids for NewDynamics/EndGame.  Got grid staggering: "
                "{}"
            )
            raise RuntimeError(msg.format(grid))

    if regular_y:
        # NS (y) grid spacing in degrees (RMDI for variable resolution
        # grids)
        headers["real_constants"]["row_spacing"] = field.bdy
        # Latitude of first row in degrees (latitudes in range 90 to -90)
        start_lat = field.bzy + field.bdy
        headers["real_constants"]["start_lat"] = start_lat
    else:
        if grid == GRIDS["newdynamics"]:
            headers["row_dependent_constants"] = {
                "dims": (len(field.y), None),
                "phi_p": list(field.y),
            }
        elif grid == GRIDS["endgame"]:
            row_data = np.zeros(len(field.y) + 1)
            row_data[:-1] = list(field.y)
            headers["row_dependent_constants"] = {
                "dims": (len(field.y) + 1, None),
                "phi_p": row_data,
            }
        else:
            msg = (
                'Can only derive "y" values for variable resolution '
                "grids for NewDynamics/EndGame.  Got grid stagerring: "
                "{}"
            )
            raise RuntimeError(msg.format(grid))

    # Real latitude of 'pseudo' N pole in degrees
    headers["real_constants"]["north_pole_lat"] = field.bplat
    # Real longitude of 'pseudo' N pole in degrees
    headers["real_constants"]["north_pole_lon"] = field.bplon


def _nlevels(cube):
    result = 1
    vert_coords = cube.coords(axis="z")
    if len(vert_coords) > 0:
        result = len(vert_coords[0].points)
    return result


def _vert_coords_eq(cube1, cube2):
    vcs1 = cube1.coords(axis="z")
    vcs2 = cube2.coords(axis="z")
    if len(vcs1) != len(vcs2):
        result = False
    else:
        result = all(
            ants.utils.coord.relaxed_equality(vc1, vc2) for vc1, vc2 in zip(vcs1, vcs2)
        )
    return result


def _check_vert_coords_f03_compatible(cubes):
    """
    Raise exception if cubes have vertical coordinates incompabile with f03.
    """
    multis = (cube for cube in cubes if _nlevels(cube) > 1)
    for cube1, cube2 in itertools.combinations(multis, 2):
        if not (_vert_coords_eq(cube1, cube2)):
            raise RuntimeError(
                "Multi-level ancillary fields must share the "
                "same vertical coordinate."
            )


def _cube_with_max_levels(cubes):
    cmax = cubes[0]
    for cube in cubes[1:]:
        cmax = cube if _nlevels(cube) > _nlevels(cmax) else cmax
    return cmax


def _set_levels(cubes, headers):
    _check_vert_coords_f03_compatible(cubes)
    cube = _cube_with_max_levels(cubes)
    vert_coords = cube.coords(axis="z")
    if len(vert_coords) > 0:
        for coord in vert_coords:
            # Check for depth (otherwise, default mule vertical coord type is
            # used).  Note that the depth coordinates we support are defined
            # in ants.fileformats.ancil._cubes_to_ancilfile\
            # ._reject_unsupported_coords
            if coord.name() == "depth":
                headers["fixed_length_header"]["vert_coord_type"] = 4
    headers["integer_constants"]["num_levels"] = _nlevels(cube)


def create(cubes, field):
    """
    Creates a template set of headers.

    The template is designed to be compatible with "from_template" method of
    :class:`mule.ancil.AncilFile`.

    Parameters
    ----------
    cubes : :class:`iris.cube.CubeList`
        The cubes used to derive the some of the header values.
    field : :class:`mule.Field3`
        A realised reference field used to derive the remaining header values.

    Returns
    -------
    : dict
        Contains the derived header values in a format suitable to be used to
        generate a mule AncilFile via the "from_template" method of
        :class:`mule.ancil.AncilFile`.

    """
    headers = _get_base_headers(cubes, field)
    _set_levels(cubes, headers)
    _set_grid_definition(headers, _get_grid(cubes), field)
    time_headers.set_headers_time_information(cubes[0], headers)
    return headers

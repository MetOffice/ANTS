# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Module for reading Fortran namelist files and constructing Python or Iris
objects, as appropriate, from the contents.
"""
import warnings

import ants
import ants.utils
import iris

from .umgrid import CAPGridRegular, CAPGridVariable, VerticalLevels

try:
    import f90nml

    _F90NML_IMPORT_ERROR = None
except Exception as _F90NML_IMPORT_ERROR:
    f90nml = None
    msg = (
        ' {}\nUnable to import "f90nml", proceeding without the '
        "capabilities it provides.  See install.rst"
    )
    warnings.warn(msg.format(str(_F90NML_IMPORT_ERROR)))


def _read_namelist(filename):
    """
    Wrapper around the f90nml namelist reader.

    Read a Fortran namelist file into a dictionary-like object.  Dictionary
    keys equate to the top-level namelist group(s) specified within
    `filename`.  This function rationalises f90nml exceptions, raising
    IOError instead.

    Parameters
    ----------
    filename : str
        The filename of the Fortran namelist.

    Returns
    -------
    :class:`f90nml.NmlDict` object
        Dictionary keys represent namelist groups while values represent group
        variables and their values.

    """
    if f90nml is None:
        raise _F90NML_IMPORT_ERROR

    msg = 'Invalid Fortran namelist file: "{}"{}.'
    nldict = None
    try:
        nldict = f90nml.read(filename)
    except (StopIteration, ValueError, AssertionError):
        raise IOError(msg.format(filename, ""))
    if not nldict:
        raise IOError(msg.format(filename, " no groups found"))
    return nldict


def apply_um_conventions(cube):
    """
    Apply UM specific conventions to the resulting cube.

    - Latitude cells are enforced S-N in direction.

    """
    # Enforce S-N for latitudes
    x, y = ants.utils.cube.horizontal_grid(cube)
    points = y.points.copy()
    bounds = y.bounds.copy()
    if points[-1] < points[0]:
        points = points[::-1]
    if bounds is not None and (bounds[-1, -1] < bounds[0, 0]):
        bounds = bounds[::-1, ::-1]
    y.points = points
    y.bounds = bounds

    return cube


def _gen_dict(filenames):
    if isinstance(filenames, str):
        filenames = [filenames]

    # Read each of the supplied namelists, checking that no duplicate groups
    # are found.
    groups = {}
    for filename in filenames:
        nldict = _read_namelist(filename)
        for group, subdict in nldict.items():
            if group in groups:
                msg = "Cannot handle duplicate namelist groups."
                raise RuntimeError(msg)
            groups[group] = subdict
    return groups


def load_um_vertical(filenames, callback=None):
    """
    Load the vertical namelist definition.

    Applies a correction to the loaded namelist to be consistent with the UM
    expectations.  Specifically, removes the zeroth level, and modifies the
    boundaries of the first level to compensate.

    Parameters
    ----------
    filenames : str
        Pathname of a Fortran namelist file, or a list of such paths.

    Returns
    -------
    : :class:`iris.cube.Cube`
        Cube representing the vertical grid defined.

    See Also
    --------
    :class:`umgrid.VerticalLevels` : for the vertical definition specification.

    """
    return _load_vertical(filenames, True, callback)


def load_lfric_vertical(filenames, callback=None):
    """
    Load the vertical namelist definition.

    Includes the zeroth level in the returned cube.

    Parameters
    ----------
    filenames : str
        Pathname of a Fortran namelist file, or a list of such paths.

    Returns
    -------
    : :class:`iris.cube.Cube`
        Cube representing the vertical grid defined.

    See Also
    --------
    :class:`umgrid.VerticalLevels` : for the vertical definition specification.

    """
    return _load_vertical(filenames, False, callback)


def _load_vertical(filenames, apply_um_workaround=True, callback=None):
    groups = _gen_dict(filenames)

    result = None
    if "vertlevs" in groups:
        result = VerticalLevels(groups).get_cube(apply_um_workaround)
    else:
        msg = "No supported groups found: {}.  Supported groups include: {}."
        raise ValueError(msg.format(list(groups.keys()), "vertlevs"))

    result = iris.io.run_callback(callback, result, groups, filenames)

    yield result


def load_cap_horizontal(filenames, callback=None):
    """
    Load the horizontal namelist definition.

    Load a model grid definition from one or more Fortran namelists, supporting
    both regular and variable resolution, global and regional grids.

    See Also
    --------
    :class:`umgrid.CAPGridRegular` : for regular grids,
    :class:`umgrid.CAPGridVariable` : for variable resolution grids

    Parameters
    ----------
    filenames : str
        Pathname of a Fortran namelist file, or a list of such paths.

    Returns
    -------
    : :class:`iris.cube.Cube`
        Cube representing the grid defined.

    """
    groups = _gen_dict(filenames)

    # Groups identify which namelist convention (CAP/UM)
    result = None
    mapping = {"horizgrid": CAPGridVariable, "grid": CAPGridRegular}

    if "horizgrid" in groups:
        result = mapping["horizgrid"](groups).get_cube()
    elif "grid" in groups:
        result = mapping["grid"](groups).get_cube()
    else:
        msg = "No supported groups found: {}.  Supported groups include: {}."
        raise ValueError(msg.format(list(groups.keys()), list(mapping.keys())))

    if result is None:
        raise RuntimeError("No grid found")
    apply_um_conventions(result)

    result = iris.io.run_callback(callback, result, groups, filenames)

    yield result

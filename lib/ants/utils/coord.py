# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.utils
import iris
import numpy as np


def set_crs(coord, axis=None, crs=None):
    """
    Set coord coordinate system.

    Set coordinate system of the coordinate, correcting and populating metadata
    where possible.

    Parameters
    ----------
    coord : :class:`iris.coords.Coord`
        Coordinate object to infer a suitable coordinate_system.
    axis : :obj:`str`, optional
        The desired coordinate axis.  If not specified, it will be guessed,
        see :func:`iris.util.guess_coord_axis`.
    crs : :class:`iris.coord_systems.CoordSystem`, optional
        Defaults to a UM Sphere where unspecified and undefined by the coord
        (ants.coord_systems.UM_SPHERE).

    Returns
    -------
    None
        Inplace operation

    """

    def populate_crs(coord, axis, crs, override):
        metadata = ["standard_name", "units"]
        for meta in metadata:
            if not override:
                if getattr(coord, meta) and getattr(coord, meta) != getattr(
                    getattr(crs, axis), meta
                ):
                    msg = "Conflicting {}, cannot set inferred crs"
                    raise RuntimeError(msg.format(meta))

            setattr(coord, meta, getattr(getattr(crs, axis), meta))
        coord.coord_system = crs.crs

    if axis is None:
        axis = iris.util.guess_coord_axis(coord)

    override = True
    if crs is None:
        if coord.coord_system is None:
            crs = ants.coord_systems.UM_SPHERE
            # Do not override metadata as we are guessing the CRS.
            override = False
        else:
            crs = coord.coord_system
    if not isinstance(crs, ants.coord_systems.CFCRS):
        crs = ants.coord_systems.CFCRS(crs)
    populate_crs(coord, axis, crs, override)


def guess_bounds(coord, strict=True):
    """
    Guess bounds wrapper around the iris guess bounds functionality.

    Additional capability from iris includes sensible guessing of latitude
    bounds to ensure they remain contiguous and guessing of time bounds for
    any calendar where points are in the middle of a month.

    Parameters
    ----------
    coord : :class:`iris.coords.Coord`
        Iris coordinate in which to guess its bounds.
    strict : bool
        Define whether an existing bounds on the coordinate should raise an
        exception (True - default iris/ants behaviour).  When strict is False,
        coordinates with only one point should continue without failure.

    Raises
    ------
    ValueError
        Raised if guessing time coordinate bounds isn't possible.  Currently,
        guessing time bounds is only supported for the case where points are
        the middle of each month.

    """

    def guess_time_bounds(coord):
        dates = coord.units.num2date(coord.points)
        lower_bounds = []
        upper_bounds = []
        for date in dates:
            if date.month == 12:
                lyear = date.year
                uyear = date.year + 1
                lmonth = 12
                umonth = 1
            else:
                lyear = uyear = date.year
                lmonth = date.month
                umonth = date.month + 1

            lower_bounds.append(date.__class__(lyear, lmonth, 1, 0, 0))
            upper_bounds.append(date.__class__(uyear, umonth, 1, 0, 0))
        bounds = coord.units.date2num(np.array([lower_bounds, upper_bounds]).T)
        contiguous = ants.utils.ndarray.allclose(bounds[1:, 0], bounds[:-1, 1])
        pointsismean = ants.utils.ndarray.allclose(bounds.mean(axis=1), coord.points)
        if not contiguous or not pointsismean:
            msg = (
                "Unsupported time coordinate for guess_bounds."
                "time bounds can only be guessed where the points "
                "are the middle of each month."
            )
            raise ValueError(msg)
        coord.bounds = bounds

    if not strict:
        if coord.has_bounds() or coord.points.size < 2:
            return
    if coord.units.is_time_reference():
        guess_time_bounds(coord)
    else:
        coord.guess_bounds()
        if "latitude" in coord.name().lower():
            bounds = coord.bounds.copy()
            bounds[bounds > 90.0] = 90.0
            bounds[bounds < -90.0] = -90.0
            coord.bounds = bounds


def relaxed_equality(coord1, coord2):
    """
    Return whether the provided coordinate is equal to the other provided.

    Equality is performed with some tolerance as defined by
    ants.config.TOLERANCE, however in the case of bounds, a more relaxed
    independent arbitrary tolerance specified.  Where bounds are present on one
    but not both coordinates, a temporary guess is made of these bounds where
    possible and a comparison made.

    Parameters
    ----------
    coord1 : :class:`iris.coords.Coord`
    coord2 : :class:`iris.coords.Coord`

    Returns
    -------
    : bool
        True if coord1 == coord2.  False if coord1 != coord2

    """
    result = coord1.attributes.keys() == coord2.attributes.keys()

    if result:
        result = coord1.points.shape == coord2.points.shape

    if result:
        result = coord1.is_compatible(coord2)

    if result:
        result = ants.utils.ndarray.allclose(coord1.points, coord2.points)
        if not np.isscalar(result):
            result = result.all()

    tot_bounds = sum([coord1.has_bounds(), coord2.has_bounds()])
    if result and tot_bounds != 0:
        if tot_bounds == 1:
            # The bounds on one of the coordinates is not present.  Attempt to
            # guess them for the comparison.
            coord1 = coord1.copy()
            coord2 = coord2.copy()
            guess_bounds(coord1, strict=False)
            guess_bounds(coord2, strict=False)
        # We do not check tolerance against the globally specified as bounds
        # are so often derived.
        result = np.allclose(coord1.bounds, coord2.bounds)

    return result


def _get_limits(coord):
    """
    Finds the minimum and maximum values of a coord bounds, without assuming an order
    for the input

    Parameters
    ----------
    coord

    Returns
    -------
    A tuple containing the minimum and maximum bounds
    """
    # Assumes points are within the range defined by the bounds.
    values = coord.points
    if coord.has_bounds():
        values = coord.bounds
    minimum = np.min(values)
    maximum = np.max(values)
    return minimum, maximum

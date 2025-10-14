# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import numpy as np
import shapely.geometry as sgeom

from . import coord, cube, dask, ndarray

__all__ = ["coord", "cube", "ndarray", "dask"]


def det_globe_shape(degrees=None, arc_minutes=None, arc_seconds=None):
    """
    Return the shape for a regular global grid of specified resolution.

    Given the number of degrees OR arc minutes OR arc seconds, return the shape
    of the resulting grid.  Provide only one argument at a time.

    Parameters
    ----------
    degrees : ~numbers.Number, optional
        Number of degrees.
    arc_minutes : ~numbers.Number, optional
        Number of arc minutes.
    arc_seconds : ~numbers.Number, optional
        Number of arc seconds.

    Returns
    -------
    : tuple
        The regular grid shape for a globe with the specified resolution.

    >>> det_globe_shape(degrees=1)
    (180, 360)
    >>> det_globe_shape(arc_minutes=1)
    (10800, 21600)
    >>> det_globe_shape(arc_seconds=30)
    (21600, 43200)

    """
    msg = "Plese provide only one argument."
    if sum([kwarg is not None for kwarg in [degrees, arc_minutes, arc_seconds]]) != 1:
        raise ValueError(msg)

    if degrees is not None:
        x = 360 // degrees
    elif arc_minutes is not None:
        x = (360 * 60) // arc_minutes
    elif arc_seconds is not None:
        x = (360 * 60 * 60) // arc_seconds
    y = x // 2
    return (y, x)


def transform_bbox(points, src_crs, tgt_crs):
    """
    Transform the given points defining a bounding box from the source
    coordinate system to the specified target coordinate system.

    Parameters
    ----------
    points : iterable
        A list of x, y pairs defining the corners of a bounding box.  These
        must be provided in a clock-wise or counter-clock-wise order.
    src_crs : :class:`iris.coord_system.CoordSystem`
        Source coordinate system of the provided points.
    tgt_crs : :class:`iris.coord_systems.CoordSystem`
        Target coordinate system to transform the bounding box.

    Returns
    -------
    : shapely MultiPolygon

        The bounding box is in the target reference system.
        In cases where the bounding box straddles the date line
        or the pole more than one bounding box geometry will be
        returned.  For instance a bounding box that straddles the
        date line will be returned as two geometries, one for each
        side of the date line. See:
        https://shapely.readthedocs.io/en/latest/reference/shapely.MultiPolygon.html

    >>> from iris.coord_systems import GeogCS, OSGB
    >>> bbox = [(0, 45), (10, 45), (10, 55), (0, 55)]
    >>> print(transform_bbox(bbox, GeogCS(6371229), OSGB())[0].bounds)
    (527915.8213500988, 0.0, 700000.0, 577349.2303676738)

    """
    cartopy_src_crs = src_crs.as_cartopy_projection()
    cartopy_tgt_crs = tgt_crs.as_cartopy_projection()

    # Check whether points lie beyond the extent of the target crs definition.
    xpnts = np.array([pnt[0] for pnt in points])
    ypnts = np.array([pnt[1] for pnt in points])
    cartopy_tgt_crs.transform_points(cartopy_src_crs, xpnts, ypnts)
    src_geom = sgeom.Polygon(points)
    tgt_geom = cartopy_tgt_crs.project_geometry(src_geom, cartopy_src_crs)

    for item in tgt_geom.bounds:
        if np.isnan(item):
            msg = (
                "Attempting to project bounding box ({}) beyond the extent of "
                "the target coordinate system limits ({})."
            )
            raise ValueError(msg.format(src_crs, tgt_crs))

    return tgt_geom


def convert_to_cartesian(cube):
    """Return an array of xyz cartesian coordinates for a given cube.

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube`
        Cube to be converted. Note that the provided cube must
        have a coordinate system.

    Returns
    -------
    :class:`~numpy.ndarray`
        An array representing the xyz coordinates of the cube
        in 3D (cartesian) space. The returned array will have
        shape ``(n_lon, n_lat, 3)``, where ``n_lon`` and ``n_lat``
        are the numbers of longitude and latitude points, respectively.
    """
    crs = cube.coord_system()
    projection = crs.as_cartopy_projection()
    geocentric_projection = projection.as_geocentric()
    x_coords = cube.coord(axis="x").points
    y_coords = cube.coord(axis="y").points
    # Example np.meshgrid output:
    # x_coords = [1 2 3 4]
    # y_coords = [6 7 8]
    # x, y = np.meshgrid(x_coords, y_coords)
    #
    # x = [1 2 3 4]
    #     [1 2 3 4]
    #     [1 2 3 4]
    #
    # y = [6 6 6 6]
    #     [7 7 7 7]
    #     [8 8 8 8]
    x, y = np.meshgrid(x_coords, y_coords)
    xyz = geocentric_projection.transform_points(projection, x, y)
    return xyz

#!/usr/bin/env python
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Shapefile creation application
******************************

Creates and saves a shapefile from a list of pairs of longitude, latitude
points defining a single polygon in a specified polygon file.

Rotated pole domains can be specified using the land sea mask argument,
where the longitude, latitude pairs are transformed to the new pole.
Unless a source cube is provided with the source coordinate reference system,
it is assumed that the points defined in the json file are on a standard spherical
unrotated geodetic coordinate reference system.

Points crossing the antimeridian after rotation are transformed to ensure the
resulting polygon is contiguous. The user can optionally specify a minimum longitude.
The longitudes will then be translated by k*360 so the minimum longitude of
the transformed points lies in [minimum_lon, minimum_lon + 360.0).
"""

import argparse
import json
import logging
import os
import warnings

import ants
import iris.coord_systems
import numpy as np
from ants.io.load import load_cube
from ants.utils.cube import CubeBuilder
from osgeo import ogr
from shapely.geometry import Polygon
from shapely.validation import explain_validity

_LOGGER = logging.getLogger(__name__)


def _check_coord_system_type(target_lsm):
    """
    Check that target_lsm has a rotated pole coordinate system.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube specifying the rotated pole coordinate system.

    Raises
    ------
    ValueError :
        If target_lsm does not have a rotated pole coordinate system.
    """

    is_pole_coords = isinstance(
        target_lsm.coord_system(), iris.coord_systems.RotatedGeogCS
    )
    if not is_pole_coords:
        raise ValueError(
            f"target_lsm.coord_system() {target_lsm.coord_system()} is not"
            f" an instance of {iris.coord_systems.RotatedGeogCS}."
            f" The landsea mask should specify a valid rotated pole coordinate"
            f" system."
        )


def _check_polygon_validity(polygon):
    """
    Check if polygon is valid.

    Parameters
    ----------
    polygon : :class:`~shapely.geometry.Polygon`
        The polygon constructed from the input points.

    Raises
    ------
    ValueError :
        If the polygon is invalid (for example intersecting edges).
    """

    if not polygon.is_valid:
        raise ValueError(f"Polygon is invalid: {explain_validity(polygon)}")


def _validate_orientation(source, target_lsm):
    """
    Validate if a transformation would take place between the target and
    a geodetic spherical source.

    Parameters
    ----------
    source : :class: `iris.cube.Cube`
        An iris cube specifying the coordinate system of the input json
        file.
    target_lsm : :class:`iris.cube.Cube`
        The target lsm cube specifying the rotated pole coordinate system.

    Returns
    -------
    bool
        True if target_lsm is a valid rotated pole, False otherwise.

    Warns
    -----
    UserWarning
        If the rotated pole would leave the input points unchanged.
    """

    target_crs = target_lsm.coord_system()

    grid_lon = target_crs.grid_north_pole_longitude
    grid_lat = target_crs.grid_north_pole_latitude
    pole_lon_rotation = target_crs.north_pole_grid_longitude

    # net longitude change
    delta_lon = pole_lon_rotation - grid_lon
    lon_shift = delta_lon % 360.0

    is_geodetic = source.coord_system() == iris.coord_systems.GeogCS(6371229.0)
    is_identity = np.isclose(lon_shift, 180.0, rtol=0.0, atol=1e-10) and np.isclose(
        grid_lat, 90.0, rtol=0.0, atol=1e-10
    )

    if is_identity and is_geodetic:
        warnings.warn(
            "target_lsm has a geodetic coordinate system with pole located"
            f" at grid_longitude={grid_lon}, grid_latitude={grid_lat}."
            " No transformation will be carried out."
        )
        return False
    else:
        return True


def _validate_args(target_lsm_path, source_path, minimum_lon):
    if source_path is not None and target_lsm_path is None:
        raise ValueError("If --source is passed then --target-lsm must also be given.")
    if minimum_lon is not None and target_lsm_path is None:
        raise ValueError(
            "If --minimum-lon is passed then --target-lsm must also be given."
        )


def _check_within_domain(target_lsm, rotated_points):
    """
    Warn if the transformed points lie outside the target lsm domain.

    Bounds are guessed on copies of the coordinates if not present, so the
    target lsm is not modified.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube defining the target domain.
    rotated_points : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of transformed longitude-latitude pairs.

    Warns
    -----
    UserWarning
        If any point lies outside the target lsm domain.
    """
    # Find the bounds of the target lsm if there are none
    target_x_coord = target_lsm.coord(axis="X").copy()
    target_y_coord = target_lsm.coord(axis="Y").copy()
    if not target_x_coord.has_bounds():
        target_x_coord.guess_bounds()
    if not target_y_coord.has_bounds():
        target_y_coord.guess_bounds()

    # Find the extent of the target lsm domain.
    bounds_lon = target_x_coord.bounds
    bounds_lat = target_y_coord.bounds
    min_lon, max_lon = bounds_lon.min(), bounds_lon.max()
    min_lat, max_lat = bounds_lat.min(), bounds_lat.max()
    lons, lats = rotated_points[:, 0], rotated_points[:, 1]

    # Check if the polygon lies in the domain specified by the target lsm.
    if (
        lons.min() < min_lon
        or lons.max() > max_lon
        or lats.min() < min_lat
        or lats.max() > max_lat
    ):
        warnings.warn("The transformed points lie outside the target lsm domain.")


def _translate_lons_to_minimum(lons, minimum_lon):
    """
    Uniformly translate longitudes so that the minimum longitude lies
    in [minimum_lon, minimum_lon + 360.0).

    Parameters
    ----------
    lons : :class:`numpy.ndarray`
        Contiguous longitudes in degrees.
    minimum_lon : float
        Longitude from which the points are translated.

    Returns
    -------
    : :class:`numpy.ndarray`
        The translated longitudes.
    """

    period = 360.0
    n_periods = (minimum_lon - lons.min()) / period
    translation = int(np.ceil(n_periods))

    return lons + translation * period


def _make_contiguous(rotated_points):
    """Translate points so a contiguous polygon is formed.

    If the distance between sequential transformed longitude points exceeds
    180.0 degrees, it is assumed these points cross the antimeridian as a
    shorter path exists joining these two points. The points are then unwrapped
    to use the complementary shorter distance.

    Longitudes are treated as a closed ring which must return to its starting
    point. If after unwrapping the points do not return to the starting value,
    the ring winds around the globe and it is rejected as pole-encircling
    points. Points containing the pole are not supported.

    Parameters
    ----------
    rotated_points : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of transformed longitude-latitude pairs.

    Returns
    -------
    : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of transformed longitude-latitude pairs.

    Raises
    ------
    ValueError
        If unwrapping finds non-zero longitude winding.

    Warns
    -----
    UserWarning.
        If the transformed points are assumed to cross the antimeridian.
    """

    new_points = np.array(rotated_points, dtype=float)
    lons = new_points[:, 0]
    closed_lons = np.concatenate((lons, lons[:1]))

    # Unwrap by taking the complement of large step sizes with respect to
    # the period.
    unwrapped_lons = np.unwrap(closed_lons, period=360.0)

    # A non-zero longitude offset following unwrapping means the closed set
    # of points winds around the pole.
    if not np.isclose(
        unwrapped_lons[0],
        unwrapped_lons[-1],
    ):
        raise ValueError("Points encircling a pole are not supported.")

    # If the unwrapped points have changed,
    if not np.allclose(unwrapped_lons[:-1], lons):
        warnings.warn(
            "The transformed points are assumed to cross the antimeridian. "
            "The points will instead be defined so that a contiguous polygon "
            "can be made."
        )

        # wrapping depends on the first point and can wrap by -360 degrees
        # instead of +360 degrees
        if np.any(unwrapped_lons[:-1] < -180.0):
            unwrapped_lons += 360.0

        new_points[:, 0] = unwrapped_lons[:-1]

    return new_points


def _transform_coordinates(target_lsm, source, points):
    """
    Transform the longitude-latitude points to the rotated pole.

    By default, the transformed longitudes are output in the interval
    [-180.0, 180.0] from the cartopy crs projection limits.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube specifying the rotated pole coordinate system.
    source : :class:`iris.cube.Cube`
        An iris cube specifying the coordinate system of the input json
        file.
    points : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of m longitude-latitude pairs.

    Returns
    -------
    : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of transformed longitude-latitude pairs.
    """

    source_crs = source.coord_system().as_cartopy_crs()
    target_coord = target_lsm.coord_system()
    target_crs = target_coord.as_cartopy_crs()

    # We only return longitude and latitude and discard the z coordinate.
    rotated_points = target_crs.transform_points(
        source_crs, points[:, 0], points[:, 1]
    )[:, :2]

    _LOGGER.info(
        "Input json file transformed to new pole rotated coordinate system at "
        "pole longitude=%s, pole latitude=%s, central rotated longitude=%s.",
        target_coord.grid_north_pole_longitude,
        target_coord.grid_north_pole_latitude,
        target_coord.north_pole_grid_longitude,
    )

    return rotated_points


def _load_cubes(target_lsm_path, source_path):
    """
    Load the target lsm and create a source cube if not provided.

    Parameters
    ----------
    target_lsm_path : str
        File path to a land sea mask that provides the new rotated pole.
    source_path : str
        File path to a source file specifying the coordinate system of the
        input json file.

    Returns
    -------
    : tuple(:class:`iris.cube.Cube`, :class:`iris.cube.Cube`)
        A tuple containing the target lsm and the source cube respectively.
    """

    target_lsm = load_cube(target_lsm_path)

    if source_path is None:
        crs = iris.coord_systems.GeogCS(6371229.0)
        source = CubeBuilder(crs, (2, 2))._cube
    else:
        source = load_cube(source_path)

    return target_lsm, source


def _transform_if_required(target_lsm, source, points, minimum_lon):
    """
    Transform the points to a target crs if required.

    The points are transformed to the specified rotated pole coordinate system
    if the provided coordinate system is a rotated pole and is not coincident
    with the geographic north pole. Following transformation, the longitudes
    are adjusted so that the polygon does not wrap the antimeridian. If
    ``minimum_lon`` is passed, the longitudes are translated by the same multiple
    of 360.0 degrees.

    If the input target lsm  is coincident with the north pole, the points
    are returned and ``minimum_lon`` is ignored.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube specifying the rotated pole coordinate system.
    source : :class:`iris.cube.Cube`
        An iris cube specifying the coordinate system of the input json
        file.
    points : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of m longitude-latitude pairs.
    minimum_lon : float or None
        Longitude from which the transformed points are translated. If None,
        no translation is applied.

    Returns
    -------
    : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of transformed longitude-latitude pairs.
    """

    _check_coord_system_type(target_lsm)

    if _validate_orientation(source, target_lsm):
        rotated_points = _transform_coordinates(target_lsm, source, points)
        rotated_points = _make_contiguous(rotated_points)
        if minimum_lon is not None:
            rotated_points[:, 0] = _translate_lons_to_minimum(
                rotated_points[:, 0], minimum_lon
            )
        _check_within_domain(target_lsm, rotated_points)
    else:
        rotated_points = np.copy(points)

    return rotated_points


def _save_json(output, target_lsm_path, source_path, target_lsm, source):
    """
    Save a json file containing metadata about the target lsm and source.

    Notes
    -----
    Normally a crs can be saved as a projection file (.prj) alongside the shapefile,
    however, for rotated poles this is not possible for Esri Shapefiles.
    See https://github.com/OSGeo/gdal/issues/4726.
    """

    parent_path = os.path.dirname(output)
    filename = os.path.splitext(os.path.basename(output))[0]

    target_crs = target_lsm.coord_system()
    target_proj_params = target_crs.as_cartopy_crs().proj4_params
    source_crs = source.coord_system()
    source_proj_params = source_crs.as_cartopy_crs().proj4_params

    prj_metadata = {
        "target_lsm": {
            "target_lsm_path": target_lsm_path,
            "coord_system": type(target_crs).__name__,
            "grid_north_pole_longitude": target_crs.grid_north_pole_longitude,
            "grid_north_pole_latitude": target_crs.grid_north_pole_latitude,
            "north_pole_grid_longitude": target_crs.north_pole_grid_longitude,
            "proj4_params": target_proj_params,
        },
        "source": {
            "source_path": source_path,
            "coord_system": type(source_crs).__name__,
            "proj4_params": source_proj_params,
        },
    }
    json_name = filename + "_prj"

    with open(os.path.join(parent_path, json_name + ".json"), "w") as json_file:
        json.dump(prj_metadata, json_file, indent=4)


def _load_points_from_json(json_file):
    """
    Load a json file containing a list of pairs of longitude-latitude points.

    Parameters
    ----------
    json_file : str
        Path to json file.

    Returns
    -------
    : :class:`numpy.ndarray`
    """

    with open(json_file, "r") as polygon_json:
        points = json.load(polygon_json)
    points = np.array(points, dtype=float)

    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("The input longitude-latitude pairs must have shape (n, 2).")
    return points


def main(json_file, output, target_lsm_path, source_path, minimum_lon):
    """
    Create a shape file from pairs of longitude, latitude points.

    Loads in a provided json file that defines pairs of longitude, latitude
    points to create a polygon from. That polygon is then used to create a
    shape file that is saved to the specified output location.

    If target_lsm_path is provided, the points are first transformed from a
    source geodetic coordinate system to a rotated pole coordinate system
    specified by the lsm. It is assumed that the points in the json file
    are on an unrotated spherical geodetic grid, unless otherwise specified.

    Parameters
    ----------
    json_file : str
        Path to json file
    output : str
        Location to store generated shape file
    target_lsm_path : str
        File path to a land sea mask that provides the new rotated pole.
    source_path : str
        File path to a source file specifying the coordinate system of the
        input json file.
    minimum_lon : float or None
        Longitude from which the transformed points are translated. If None,
        no translation is applied.
    """

    # Load a json and make a polygon
    points = _load_points_from_json(json_file)

    # Transform points to a rotated pole if required
    if target_lsm_path is not None:
        target_lsm, source = _load_cubes(target_lsm_path, source_path)
        points = _transform_if_required(target_lsm, source, points, minimum_lon)

    polygon = Polygon(points)
    _check_polygon_validity(polygon)

    # Now convert it to a shapefile with OGR
    driver = ogr.GetDriverByName("Esri Shapefile")
    datasource = driver.CreateDataSource(output)
    layer = datasource.CreateLayer("", None, ogr.wkbPolygon)

    # Add one attribute
    layer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    defn = layer.GetLayerDefn()

    # Create a new feature (attribute and geometry)
    feature = ogr.Feature(defn)
    feature.SetField("id", 123)

    # Make a geometry, from Shapely object
    geometry = ogr.CreateGeometryFromWkb(polygon.wkb)
    feature.SetGeometry(geometry)

    layer.CreateFeature(feature)
    feature = geometry = None  # destroy these

    # Save and close everything
    datasource = layer = feature = geometry = None

    # Save metadata on the projection
    if target_lsm_path is not None:
        _save_json(output, target_lsm_path, source_path, target_lsm, source)


def _get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "json_file", help="Path to json file defining polygon to generate."
    )
    parser.add_argument("output", help="File to save shape file to.")
    parser.add_argument(
        "--target-lsm",
        type=ants.config.filepath_readable,
        required=False,
        help="Path to the land sea mask containing the rotated pole"
        " coordinate system.",
    )
    parser.add_argument(
        "--minimum-lon",
        type=float,
        required=False,
        help="Longitude from which the transformed points are translated. All "
        "points are translated by the same multiple of 360 degrees so that the "
        "polygon's minimum longitude lies in [minimum-lon, minimum-lon + 360). "
        "If not given, no translation is applied. Requires --target-lsm."
        "Only applied if a transformation is performed.",
    )
    parser.add_argument(
        "--source",
        type=ants.config.filepath_readable,
        required=False,
        help="Path to a source specifying the coordinate system of the json file.",
    )
    return parser


def cli_interface():
    parser = _get_parser()
    args = parser.parse_args()

    _validate_args(args.target_lsm, args.source, args.minimum_lon)
    main(args.json_file, args.output, args.target_lsm, args.source, args.minimum_lon)


if __name__ == "__main__":
    cli_interface()

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
it assumed that the points defined in the json file are on a standard spherical
unrotated geodetic coordinate reference system.
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
        The lsm cube specifiying the rotated pole coordinate system.

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


def _check_polygon_validity(polygon, ccw_expected):
    """
    Check if polygon is valid and has the expected orientation.

    A rotation should not change the orientation of the points. If the orientation
    does change, it is a sign that the transformation has not behaved as expected.

    Parameters
    ----------
    polygon : :class:`~shapely.geometry.Polygon`
        The polygon made from the input json file.
    ccw_expected : bool
        Expected polygon orientation before transformation.

    Raises
    ------
    ValueError :
        If the polygon is invalid (for example intersecting edges).
    ValueError :
        If the polygon has a different orientation after transformation.
    """

    if not polygon.is_valid:
        raise ValueError(f"Polygon is invalid: {explain_validity(polygon)}")
    if polygon.exterior.is_ccw != ccw_expected:
        raise ValueError(
            f"Polygon orientation has changed. Expected is_ccw={ccw_expected}, "
            f"current polygon has is_ccw={polygon.exterior.is_ccw}."
        )


def _validate_orientation(target_lsm):
    """
    Validate that the rotated pole coordinate system is not coincident with the
    geographic north pole.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The target lsm cube specifying the rotated pole coordinate system.

    Returns
    -------
    bool
        True if target_lsm is a valid rotated pole, False otherwise.

    Warns
    -----
    UserWarning
        If the rotated pole is coincident with the geographic north pole.
    """

    target_crs = target_lsm.coord_system()

    grid_lon = target_crs.grid_north_pole_longitude
    grid_lat = target_crs.grid_north_pole_latitude
    pole_lon_rotation = target_crs.north_pole_grid_longitude

    invalid_crs = ants.utils.ndarray.allclose(
        [grid_lon, grid_lat, pole_lon_rotation], [0.0, 90.0, 0.0]
    )

    if invalid_crs:
        warnings.warn(
            "target_lsm has a geodetic coordinate system with pole located"
            f" at grid_longitude={grid_lon}, grid_latitude={grid_lat}."
            " No transformation will be carried out."
        )
    return not invalid_crs


def _validate_args(target_lsm_path, source_path):
    if source_path is not None and target_lsm_path is None:
        raise ValueError("If --source is passed then --target-lsm must also be given.")


def _transform_coordinates(target_lsm, source, points):
    """
    Transform the longitude-latitude points to the rotated pole.

    If the transformation results in the points spanning the antimeridian, this
    can cause incorrect polygons to be created because shapely does not wrap
    between 180.0 and -180.0 degrees.

    If the distance between sequential transformed longitude points exceeds
    180.0 degrees, it is assumed these points cross the antimeridian. The points
    are instead defined in the interval [0.0, 360.0] by adding 360.0 degrees
    to the negative longitudes.

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
    Warns
    -----
    UserWarning
        If the transformed points are assumed to cross the antimeridian.
    UserWarning
        If the transformed polygon lies at least partially outside of the
        domain specified in the target lsm.
    """

    source_crs = source.coord_system().as_cartopy_crs()
    target_coord = target_lsm.coord_system()
    target_crs = target_coord.as_cartopy_crs()

    # We only return longitude and latitude and discard the z coordinate.
    rotated_points = target_crs.transform_points(
        source_crs, points[:, 0], points[:, 1]
    )[:, :2]

    # Create a wrapped array of longitudes and find the point-wise difference.
    closed_lon = np.vstack([rotated_points, rotated_points[0, :]])
    lon_diff = np.abs(closed_lon[:-1, 0] - closed_lon[1:, 0])

    # Add 360.0 degrees to negative longitudes if the points cross the antimeridian.
    if np.any(lon_diff > 180.0):
        warnings.warn(
            "The transformed points are assumed to cross the antimeridian. "
            "The longitudinal points will instead be defined in the interval"
            " [0, 360.0] degrees."
        )
        neg_indices = np.where(rotated_points[:, 0] < 0)
        rotated_points[neg_indices, 0] += 360.0

    # Find the bounds of the target lsm.
    bounds_lon = target_lsm.coord(axis="X").bounds
    bounds_lat = target_lsm.coord(axis="Y").bounds
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


def _transform_if_required(target_lsm, source, points):
    """
    Perform the transformation to a rotated pole if the coordinate system
    is valid.

    The points are transformed to the specified rotated pole coordinate system
    if the provided coordinate system is a rotated pole and is not coincident
    with the geographic north pole.

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

    _check_coord_system_type(target_lsm)

    if _validate_orientation(target_lsm):
        rotated_points = _transform_coordinates(target_lsm, source, points)
    else:
        rotated_points = np.copy(points)

    return rotated_points


def _save_json(output, target_lsm_path, source_path, target_lsm, source):
    """
    Save a json file containing metadata about the target lsm and source.
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
    points = np.array(points)

    return points


def main(json_file, output, target_lsm_path, source_path):
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
    """

    # Load a json and make a polygon
    points = _load_points_from_json(json_file)
    ccw_expected = Polygon(points).exterior.is_ccw

    # Transform points to a rotated pole if required
    if target_lsm_path is not None:
        target_lsm, source = _load_cubes(target_lsm_path, source_path)
        points = _transform_if_required(target_lsm, source, points)
        _save_json(output, target_lsm_path, source_path, target_lsm, source)

    polygon = Polygon(points)
    _check_polygon_validity(polygon, ccw_expected)

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
        "--source",
        type=ants.config.filepath_readable,
        required=False,
        help="Path to a source specifying the coordinate system of the json file.",
    )
    return parser


def cli_interface():
    parser = _get_parser()
    args = parser.parse_args()

    _validate_args(args.target_lsm, args.source)
    main(args.json_file, args.output, args.target_lsm, args.source)


if __name__ == "__main__":
    cli_interface()

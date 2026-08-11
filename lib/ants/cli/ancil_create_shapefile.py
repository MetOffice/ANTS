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
where the longitude, latitude pairs are rotated to the new pole.
Unless a source cube is provided with the source coordinate reference system,
it assumed that the points defined in the json file are on a standard spherical
unrotated geodetic coordinate reference system.
"""
import argparse
import json
import logging
import warnings

import ants
import iris.coord_systems
import numpy as np
from ants.io.load import load_cube, load_landsea_mask
from ants.utils.cube import CubeBuilder
from osgeo import ogr
from shapely.geometry import Polygon

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

    valid_crs = not (
        ants.utils.ndarray.allclose(
            [grid_lon, grid_lat, pole_lon_rotation], [0.0, 90.0, 0.0]
        )
    )
    if not valid_crs:
        warnings.warn(
            "target_lsm has a geodetic coordinate system with pole located"
            f"at grid_longitude={grid_lon}, grid_latitude={grid_lat}."
            "No transformation will be carried out."
        )
    return valid_crs


def _validate_args(target_lsm_path, source_cube_path):
    if source_cube_path is not None and target_lsm_path is None:
        raise ValueError(
            "If --source-cube is passed then --target-lsm must also be given."
        )


def _transform_coordinates(target_lsm, source_cube, points):
    """
    Transform the longitude-latitude points to the rotated pole.

    If the distance between transformed longitude points exceeds 180.0,
    it is assumed these points cross the antimeridian. The points are
    changed so they are instead defined in the interval [0.0, 360.0].

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube specifying the rotated pole coordinate system.
    source_cube : :class:`iris.cube.Cube`
        An iris cube specifying the coordinate system of the input json
        file.
    points : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of m longitude-latitude pairs.

    Returns
    -------
    : :class:`numpy.ndarray`
        An ``(m, 2)`` numpy array of transformed longitude-latitude pairs.
    """

    source_crs = source_cube.coord_system().as_cartopy_crs()
    target_coord = target_lsm.coord_system()
    target_crs = target_coord.as_cartopy_crs()

    rotated_points = target_crs.transform_points(
        source_crs, points[:, 0], points[:, 1]
    )[:, :2]

    closed_longitudes = np.vstack([rotated_points, rotated_points[0, :]])
    long_diff = np.abs(closed_longitudes[:-1, 0] - closed_longitudes[1:, 0])

    if np.any(long_diff > 180.0):
        neg_indices = np.where(rotated_points[:, 0] < 0)
        rotated_points[neg_indices, 0] += 360.0

    _LOGGER.info(
        "Input json file transformed to new pole rotated coordinate system at "
        "pole longitude=%s, pole latitude=%s, central rotated longitude=%s.",
        target_coord.grid_north_pole_longitude,
        target_coord.grid_north_pole_latitude,
        target_coord.north_pole_grid_longitude,
    )

    return rotated_points


def _load_cubes(target_lsm_path, source_cube_path):
    """
    Load the target lsm and create a source cube if not provided.

    Parameters
    ----------
    target_lsm_path : str
        File path to a land sea mask that provides the new rotated pole.
    source_cube_path : str
        File path to an iris cube specifying the coordinate system of the
        input json file.

    Returns
    -------
    : tuple(:class:`iris.cube.Cube`, :class:`iris.cube.Cube`)
        A tuple containing the target lsm and the source cube respectively.
    """

    target_lsm = load_landsea_mask(target_lsm_path)

    if source_cube_path is None:
        crs = iris.coord_systems.GeogCS(6371229.0)
        source_cube = CubeBuilder(crs, (2, 2))._cube
    else:
        source_cube = load_cube(source_cube_path)

    return target_lsm, source_cube


def _transform_if_required(target_lsm, source_cube, points):
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
    source_cube : :class:`iris.cube.Cube`
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
        rotated_points = _transform_coordinates(target_lsm, source_cube, points)
    else:
        rotated_points = np.copy(points)

    return rotated_points


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


def main(json_file, output, target_lsm_path, source_cube_path):
    """
    Create a shape file from pairs of longitude, latitude points.

    Loads in a provided json file that defines pairs of longitude, latitude
    points to create a polygon from. That polygon is then used to create a
    shape file that is saved to the specified output location.

    If target_lsm_path is provided, the points are first transformed from a
    source geodetic coordinate system to a rotated pole coordinate system
    specified by the lsm. It is assumed that the points in the json
    file are on an unrotated geodetic grid, unless otherwise specified.

    Parameters
    ----------
    json_file : str
        Path to json file
    output : str
        Location to store generated shape file
    target_lsm_path : str
        File path to a land sea mask that provides the new rotated pole.
    source_cube_path : str
        File path to an iris cube specifying the coordinate system of the
        input json file.
    """

    # Load a json and make a polygon
    points = _load_points_from_json(json_file)

    if target_lsm_path is not None:
        target_lsm, source_cube = _load_cubes(target_lsm_path, source_cube_path)
        points = _transform_if_required(target_lsm, source_cube, points)

    polygon = Polygon(points)
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
        "--source-cube",
        type=ants.config.filepath_readable,
        required=False,
        help="Path to an iris cube which specifies the co-ordinate"
        " system of the json file.",
    )
    return parser


def cli_interface():
    parser = _get_parser()
    args = parser.parse_args()

    _validate_args(args.target_lsm, args.source_cube)
    main(args.json_file, args.output, args.target_lsm, args.source_cube)


if __name__ == "__main__":
    cli_interface()

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
where the longitude, latitude pairs are rotated to the new pole
It is assumed that the shapefile is on a standard unrotated lon-lat grid.
"""
import argparse
import json
import logging
import warnings

import ants
import cartopy.crs as ccrs
import iris.coord_systems
import numpy as np
from ants.io.load import load_landsea_mask
from osgeo import ogr
from shapely.geometry import Polygon

_LOGGER = logging.getLogger(__name__)


def _validate_coord_system(target_lsm):
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
            f"""target_lsm.coord_system() {target_lsm.coord_system()} is not
            an instance of {iris.coord_systems.RotatedGeogCS}. The landsea mask
            should specify a valid rotated pole coordinate system."""
        )


def _transform_coordinates(target_lsm, points):
    """
    Transforms the longitude, latitude points in the source coordinate
    system to the rotated pole coordinate system defined by target_lsm.

    he source coordinate system is assumed to be unrotated geodetic
    defined on a sphere. Does nothing if the target coordinate system
    is unrotated.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube specifiying the rotated pole coordinate system.
    points : :class:`np.ndarry`
        An (m,2) sized numpy array of m longitude and m latitude points.

    Returns
    -------
    rotated_points : :class:`np.ndarry`
        An (m,2) sized numpy array of rotated longitude and latitude points.

    Raises
    ------
    Warns : UserWarning
        If target_lsm is coincident with the true north pole and is
        defined on a sphere.
    """

    sphere = ccrs.Globe(semimajor_axis=6371000.0, semiminor_axis=6371000.0)

    source_crs = ccrs.Geodetic(globe=sphere)
    target_coord = target_lsm.coord_system()

    ref_crs = ccrs.RotatedGeodetic(
        pole_latitude=90.0,
        pole_longitude=0,
        globe=sphere,
    )

    # get the cube proj4 parameters
    target_crs = target_lsm.coord_system().as_cartopy_crs()
    target_proj4 = target_crs.proj4_params

    # Checks that the poles and also underlying ellipses are the same
    if ref_crs == target_crs:
        warnings.warn(
            f"""target_lsm has a geodetic coordinate system with pole located at
              grid_latitude={target_proj4['o_lat_p']},
              grid_longitude={target_proj4['o_lon_p']}.
              No transformation will be carried out."""
        )
        rotated_points = np.copy(points)
        return rotated_points

    rotated_points = target_coord.as_cartopy_crs().transform_points(
        source_crs, points[:, 0], points[:, 1]
    )[:, :2]

    _LOGGER.info(
        "Input json file transformed to new pole rotated coordinate system at"
        "pole longitude=%s, pole latitude=%s, central rotated longitude=%s.",
        target_coord.grid_north_pole_longitude,
        target_coord.grid_north_pole_latitude,
        target_coord.north_pole_grid_longitude,
    )

    return rotated_points


def _load_polygon_from_json(json_file, target_lsm_path):
    """
    Load a json file containing a list of pairs of longitude, latitude points
    to create a polygon from.

    Parameters
    ----------
    json_file : str
        Path to json file
    target_lsm_path : str
        File path for a land sea mask that provides the new rotated pole
        coordinates to which the longitude, latitude pairs will be transformed.

    Returns
    -------
    : :class:`~shapely.geometry.Polygon`
    """
    with open(json_file, "r") as polygon_json:
        points = json.load(polygon_json)
    points = np.array(points)

    if target_lsm_path is not None:
        target_lsm = load_landsea_mask(target_lsm_path)
        _validate_coord_system(target_lsm)
        points = _transform_coordinates(target_lsm, points)

    polygon = Polygon(points)

    return polygon


def main(json_file, output, target_lsm_path):
    """
    Loads in a provided json file that defines pairs of longitude, latitude
    points to create a polygon from. That polygon is then used to create a
    shape file that is saved to the specified output location.

    If target_lsm_path is provided, the points are first transformed from an
    unrotated geodetic coordinate system to a rotated pole coordinate system
    specified by the lsm. It is assumed that the points specified in the json
    file are on an unrotated geodetic grid.

    Parameters
    ----------
    json_file : str
        Path to json file
    output : str
        Location to store generated shape file
    target_lsm_path : str
        File path for a land sea mask that provides the new rotated pole
        coordinates to which the longitude, latitude pairs will be transformed.
    """

    # Load a json and make a polygon
    polygon = _load_polygon_from_json(json_file, target_lsm_path)

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
    parser.add_argument(
        "--target-lsm",
        type=ants.config.filepath_readable,
        required=False,
        help="Path to the land sea mask containing the rotated pole"
        " coordinate system.",
    )
    parser.add_argument("output", help="File to save shape file to.")
    return parser


def cli_interface():
    parser = _get_parser()
    args = parser.parse_args()
    main(args.json_file, args.output, args.target_lsm)


if __name__ == "__main__":
    cli_interface()

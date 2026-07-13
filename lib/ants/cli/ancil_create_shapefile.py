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
It is assumed that the shapefile is on a standard unrotated lat-lon grid.
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
    Check that target_lsm has a rotated pole co-ordinate system.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube specifiying the rotated pole co-ordinate system.

    Raises
    ------
    ValueError :
        If target_lsm does not have a rotated pole co-ordinate system.
    """

    is_pole_coords = isinstance(
        target_lsm.coord_system(), iris.coord_systems.RotatedGeogCS
    )
    if not is_pole_coords:
        raise ValueError(
            f"""target_lsm.coord_system() {target_lsm.coord_system()} is not
            an instance of {iris.coord_systems.RotatedGeogCS}. The landsea mask
            should specify a valid rotated pole co-ordinate system."""
        )


def _check_pole_orientation(target_lsm):
    """
    Check if target_lsm is already orientated with the true north pole.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube specifiying the rotated pole co-ordinate system.

    Raises
    ------
    warning :
        If target_lsm is already coincident with the true north pole.
    """

    # TODO : I don't know what to specify here
    sphere = ccrs.Globe(semimajor_axis=6371000.0, semiminor_axis=6371000.0)

    ref_crs = ccrs.RotatedGeodetic(
        pole_latitude=90.0,
        pole_longitude=0,
        globe=sphere,
    )

    # get the cube proj4 parameters
    target_crs = target_lsm.coord_system().as_cartopy_crs()
    target_proj4 = target_crs.proj4_params

    if ref_crs == target_crs:
        warnings.warn(
            f"""target_lsm has a geodetic co-ordinate system with pole located at
              grid_latitude={target_proj4['o_lat_p']},
              grid_longitude={target_proj4['o_lon_p']}.
              No rotation will be carried out."""
        )


def _transform_coordinates(target_lsm, lons, lats):
    """
    Transforms the longitude, latitude points in the source co-ordinate
    system to the rotated pole co-ordinate system defined by target_lsm.
    The source co-ordinate is assumed to be unrotated geodetic.

    Parameters
    ----------
    target_lsm : :class:`iris.cube.Cube`
        The lsm cube specifiying the rotated pole co-ordinate system.
    lons : :class:`np.ndarry`
        Longitude points to rotate of length m.
    lats : :class:`np.ndarry`
        Latitude points to rotate of length m.

    Returns
    -------
    rotated_points : :class:`np.ndarry`
        A (m,2) numpy array of rotated longitude and latitude pairs.

    """

    sphere = ccrs.Globe(semimajor_axis=6371000.0, semiminor_axis=6371000.0)

    source_crs = ccrs.Geodetic(globe=sphere)
    target_coord = target_lsm.coord_system()

    rotated_points = target_coord.as_cartopy_crs().transform_points(
        source_crs, lons, lats  # longitude  # latitude
    )[:, :2]

    _LOGGER.info(
        "Input json file transformed to new pole rotated co-ordinate system at"
        "grid_latitude=%s, grid_longitude=%s.",
        target_coord.grid_north_pole_latitude,
        target_coord.grid_north_pole_longitude,
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
        coordinates to which the longitude, latitude pairs will be mapped.

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
        _check_pole_orientation(target_lsm)

        lon, lat = points[:, 0], points[:, -1]
        points = _transform_coordinates(target_lsm, lon, lat)

    polygon = Polygon(points)

    return polygon


def main(json_file, output, target_lsm_path):
    """
    Loads in a provided json file that defines pairs of longitude, latitude
    points to create a polygon from. That polygon is then used to create a
    shape file that is saved to the specified output location.

    If a target_lsm_path is provided, the points will first be transformed
    from a geodetic co-ordinate system to a rotated pole co-ordinate system
    specified by the lsm file.

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
        " co-ordinate system.",
    )
    parser.add_argument("output", help="File to save shape file to.")
    return parser


def cli_interface():
    parser = _get_parser()
    args = parser.parse_args()
    main(args.json_file, args.output, args.target_lsm)


if __name__ == "__main__":
    cli_interface()

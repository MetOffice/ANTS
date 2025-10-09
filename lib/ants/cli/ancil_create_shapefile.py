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
"""
import argparse
import json

import numpy as np
from osgeo import ogr
from shapely.geometry import Polygon


def _load_polygon_from_json(json_file):
    """
    Load a json file containing a list of pairs of longitude, latitude points
    to create a polygon from.

    Parameters
    ----------
    json_file : str
        Path to json file

    Returns
    -------
    : :class:`~shapely.geometry.Polygon`
    """
    with open(json_file, "r") as polygon_json:
        polygon = json.load(polygon_json)
    polygon = np.array(polygon)
    polygon = Polygon(polygon)
    return polygon


def main(json_file, output):
    """
    Loads in a provided json file that defines pairs of longitude, latitude
    points to create a polygon from. That polygon is then used to create a
    shape file that is saved to the specified output location.

    Parameters
    ----------
    json_file : str
        Path to json file
    output : str
        Location to store generated shape file

    """

    # Load a json and make a polygon
    polygon = _load_polygon_from_json(json_file)

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
    return parser


def cli_interface():
    parser = _get_parser()
    args = parser.parse_args()
    main(args.json_file, args.output)


if __name__ == "__main__":
    cli_interface()

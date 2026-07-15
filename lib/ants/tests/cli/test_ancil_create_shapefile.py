# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import re
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.cli.ancil_create_shapefile import (
    _transform_coordinates,
    _validate_coord_system,
)
from ants.tests.stock import geodetic


def _create_cube(north_pole_lon, north_pole_lat, ellipsoid):
    # stock geodetic automatically returns an identity rotated geodetic
    # back to geodetic
    crs = iris.coord_systems.RotatedGeogCS(
        grid_north_pole_latitude=north_pole_lat,
        grid_north_pole_longitude=north_pole_lon,
        ellipsoid=ellipsoid,
    )
    lons, lats = [0.0], [0.0]
    lon_coord = iris.coords.DimCoord(
        lons,
        standard_name="grid_longitude",
        units="degrees",
        coord_system=crs,
    )

    lat_coord = iris.coords.DimCoord(
        lats,
        standard_name="grid_latitude",
        units="degrees",
        coord_system=crs,
    )

    data = np.zeros((len(lats), len(lons)))

    cube = iris.cube.Cube(data, dim_coords_and_dims=[(lat_coord, 0), (lon_coord, 1)])
    return cube


class Common(object):
    def setUp(self):
        # unrotated source cube
        self.source_cube = geodetic((2, 2))
        # spherical input coordinate systems are simple to test
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0, 6371229.0)

        self.sphere_source = geodetic((2, 2), crs=self.sphere_crs)

        self.sphere_identity_target_lsm = _create_cube(0.0, 90.0, self.sphere_crs)
        self.sphere_equator_target_lsm = geodetic(
            (2, 2), north_pole_lat=0.0, north_pole_lon=0.0, crs=self.sphere_crs
        )


class Test__validate_coord_system(Common, ants.tests.TestCase):

    def test_unrotated_target_lsm(self):
        target_lsm = geodetic((2, 2))
        error_msg = re.escape(
            f"target_lsm.coord_system() {target_lsm.coord_system()} is not"
            f" an instance of {iris.coord_systems.RotatedGeogCS}."
            f" The landsea mask should specify a valid rotated pole coordinate"
            f" system."
        )

        with self.assertRaisesRegex(ValueError, error_msg):
            _validate_coord_system(target_lsm)


# add test that checks results are made positive with a mock
class Test__transform_coordinates(Common, ants.tests.TestCase):
    def setUp(self):
        super().setUp()
        self.vary_latitudes = np.array(
            [[0.0, 0.0, 0.0, 0.0, 0.0], [90.0, 45.0, 0.0, -45.0, -90.0]]
        ).T
        self.vary_longitudes = np.array(
            [
                [-135.0, -90.0, -45.0, 0.0, 45.0, 90.0, 135.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ]
        ).T

    def test_identity_rotation_sphere(self):

        true_lats = np.array([90, 45, 0, -45, -90])
        # The rotated geodesic system flips the longitude
        # Rotated geodesic has some odd properties, like the central
        # longitude being set to 180.0
        true_lons = np.array([np.nan, 180.0, 180.0, 180.0, 180.0])

        expected_rotation = np.array([true_lons, true_lats]).T
        # we cannot check the longitude at the pole (any longitude is valid)
        check_mask = ~np.isnan(expected_rotation)

        rotated_coords = _transform_coordinates(
            self.sphere_identity_target_lsm, self.sphere_source, self.vary_latitudes
        )

        assert ants.utils.ndarray.allclose(
            expected_rotation[check_mask], rotated_coords[check_mask]
        )

    def test_rotation_to_equator_sphere(self):
        true_lats = np.array([-45.0, 0.0, 45.0, 90.0, 45.0, 0.0, -45.0])
        # Again the results for lon depend on where the central lon is
        true_lons = np.array([90.0, 90.0, 90.0, np.nan, 270.0, 270.0, 270.0])
        expected_rotation = np.array([true_lons, true_lats]).T
        check_mask = ~np.isnan(expected_rotation)
        rotated_coords = _transform_coordinates(
            self.sphere_equator_target_lsm, self.sphere_source, self.vary_longitudes
        )
        assert ants.utils.ndarray.allclose(
            expected_rotation[check_mask], rotated_coords[check_mask]
        )

    def test_negative_longitudes_converted(self):

        true_coords = np.array([[90.0, 160.0, 326.7], [0.0, 0.0, 0.0]]).T
        # presumably I can't get a -400.0 for example
        neg_lons = np.array([[-270.0, -200.0, -33.3], [0.0, 0.0, 0.0]]).T

        target_lsm, source_cube = mock.Mock(), mock.Mock()
        source_crs, target_crs = mock.Mock(), mock.Mock()
        target_coord = mock.Mock()

        source_cube.coord_system.return_value.as_cartopy_crs.return_value = source_crs
        target_lsm.coord_system.return_value = target_coord

        target_coord.as_cartopy_crs.return_value = target_crs

        target_crs.transform_points.return_value = neg_lons

        result = _transform_coordinates(target_lsm, source_cube, neg_lons)
        assert ants.utils.ndarray.allclose(true_coords, result)


class test_main:
    pass


class test_cli:
    pass

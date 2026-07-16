# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import argparse
import re
from unittest import mock
from unittest.mock import Mock

import ants.tests
import iris
import numpy as np
from ants.cli.ancil_create_shapefile import (
    _load_polygon_from_json,
    _transform_coordinates,
    _validate_args,
    _validate_coord_system,
    _validate_orientation,
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
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_source = geodetic((2, 2), crs=self.sphere_crs)
        self.sphere_identity_target_lsm = _create_cube(0.0, 90.0, self.sphere_crs)
        self.sphere_equator_target_lsm = geodetic(
            (2, 2), north_pole_lat=0.0, north_pole_lon=0.0, crs=self.sphere_crs
        )
        self.sphere_rotate_lon = geodetic(
            (2, 2), north_pole_lat=90.0, north_pole_lon=90.0, crs=self.sphere_crs
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


class Test__validate_orientation(Common, ants.tests.TestCase):
    def setUp(self):
        super().setUp()
        self.warning_msg = (
            "target_lsm has a geodetic coordinate system with pole located"
            "at grid_longitude=0.0, grid_latitude=90.0."
            "No transformation will be carried out."
        )

    def test_warning_raised(self):
        with self.assertWarnsRegex(UserWarning, self.warning_msg):
            _validate_orientation(self.sphere_identity_target_lsm)

    def test_no_warning_raised(self):
        self.assertFalse(_validate_orientation(self.sphere_rotate_lon))


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

    def test_longitudinal_rotation(self):
        # these tests can be counter-intuitive as the prime-meridian
        # is by default at 180.0 so a rotation of 90.0 causes the prime meridian
        # to be at 270.0 (it is always 180 further round from the longitude given)
        points = np.array([[0.0, 45.0, 90.0, 135.0], [0.0, 0.0, 0.0, 0.0]]).T

        true_lats = np.array([0.0, 0.0, np.nan, 0.0])
        true_lons = np.array([90.0, 135.0, 180.0, 225.0])
        expected_rotation = np.array([true_lons, true_lats]).T
        check_mask = ~np.isnan(expected_rotation)

        rotated_coords = _transform_coordinates(
            self.sphere_rotate_lon, self.sphere_source, points
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

        target_lsm, source_cube = Mock(), Mock()
        source_crs, target_crs = Mock(), Mock()
        target_coord = Mock()

        source_cube.coord_system.return_value.as_cartopy_crs.return_value = source_crs
        target_lsm.coord_system.return_value = target_coord

        target_coord.as_cartopy_crs.return_value = target_crs

        target_crs.transform_points.return_value = neg_lons

        result = _transform_coordinates(target_lsm, source_cube, neg_lons)
        assert ants.utils.ndarray.allclose(true_coords, result)


class Test__load_polygon_from_json(Common, ants.tests.TestCase):
    def setUp(self):
        super().setUp()
        self.json_values = [[1, 2], [3, 4], [5, 6], [7, 8]]

    def patch_loader(func):
        @mock.patch("ants.cli.ancil_create_shapefile.load_landsea_mask")
        @mock.patch("ants.cli.ancil_create_shapefile.load_cube")
        @mock.patch("ants.cli.ancil_create_shapefile._validate_coord_system")
        @mock.patch("ants.cli.ancil_create_shapefile._transform_coordinates")
        @mock.patch("builtins.open", new_callable=mock.mock_open)
        @mock.patch("ants.cli.ancil_create_shapefile.json.load")
        def wrapper(
            self,
            mock_json,
            mock_open,
            mock_transform,
            mock_validate,
            mock_load,
            mock_load_lsm,
            *args,
            **kwargs,
        ):
            return func(
                self,
                mock_json,
                mock_open,
                mock_transform,
                mock_validate,
                mock_load,
                mock_load_lsm,
                *args,
                **kwargs,
            )

        return wrapper

    @patch_loader
    def test_load_call(
        self,
        mock_json,
        mock_open,
        mock_transform,
        mock_validate,
        mock_load,
        mock_load_lsm,
    ):

        mock_json.return_value = self.json_values
        _ = _load_polygon_from_json("json/path", None, None)

        mock_json.assert_called_once()
        mock_load_lsm.assert_not_called()
        mock_load.assert_not_called()
        mock_validate.assert_not_called()
        mock_transform.assert_not_called()

    @patch_loader
    def test_transform_not_called(
        self,
        mock_json,
        mock_open,
        mock_transform,
        mock_validate,
        mock_load,
        mock_load_lsm,
    ):

        mock_json.return_value = self.json_values
        mock_validate.return_value = True
        mock_load_lsm.return_value = Mock()
        mock_load.return_value = Mock()

        _ = _load_polygon_from_json("json/path", "lsm/path", "source_cube/path")

        mock_load_lsm.assert_called_once()
        mock_load.assert_called_once()
        mock_transform.assert_not_called()

    @patch_loader
    def test_transform_called(
        self,
        mock_json,
        mock_open,
        mock_transform,
        mock_validate,
        mock_load,
        mock_load_lsm,
    ):

        mock_json.return_value = self.json_values
        mock_validate.return_value = False
        mock_load_lsm.return_value = Mock()
        mock_load.return_value = Mock()
        mock_transform.return_value = self.json_values

        _ = _load_polygon_from_json("json/path", "lsm/path", "source_cube/path")

        mock_load_lsm.assert_called_once()
        mock_load.assert_called_once()
        mock_transform.assert_called_once()

    """
    I need to figure out how to get this patch to work
    @patch_loader
    def test_load_call(self, mock_json, mock_open, mock_transform,
                    mock_validate, mock_load, mock_load_lsm):

        ants_cube = ants.utils.cube.CubeBuilder(self.sphere_crs,(2,2))._cube
        mock_json.return_value = self.json_values
        mock_validate.return_value = False
        mock_load_lsm.return_value = Mock()
        mock_transform.return_value = self.json_values

        _ = _load_polygon_from_json("json/path", "lsm/path", None)

        mock_json.assert_called_once()
        mock_load_lsm.assert_called_once()
        mock_load.assert_not_called()
        mock_validate.assert_called_once()
        mock_transform.assert_called_once_with(mock_load_lsm.return_value,
                                               ants_cube,
                                               np.array(self.json_values))
    """


class Test__validate_args(ants.tests.TestCase):

    def test_error_raised(self):
        args = argparse.Namespace(
            json_file="json/path",
            output="output/path",
            target_lsm=None,
            source_cube="source/path",
        )
        error_msg = "If --source-cube is passed then --target-lsm must" "also be given."
        with self.assertRaisesRegex(ValueError, error_msg):
            _validate_args(args)

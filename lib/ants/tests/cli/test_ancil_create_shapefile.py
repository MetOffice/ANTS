# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import argparse
import re
from unittest import mock

import ants.tests
import iris
import numpy as np
from ants.cli.ancil_create_shapefile import (
    _check_coord_system_type,
    _load_polygon_from_json,
    _transform_coordinates,
    _transform_if_required,
    _validate_args,
    _validate_orientation,
)
from ants.tests.stock import geodetic
from ants.utils.cube import CubeBuilder


class Test__check_coord_system_type(ants.tests.TestCase):

    def test_unrotated_target_lsm(self):
        target_lsm = geodetic((2, 2))
        error_msg = re.escape(
            f"target_lsm.coord_system() {target_lsm.coord_system()} is not"
            f" an instance of {iris.coord_systems.RotatedGeogCS}."
            f" The landsea mask should specify a valid rotated pole coordinate"
            f" system."
        )

        with self.assertRaisesRegex(ValueError, error_msg):
            _check_coord_system_type(target_lsm)


class Test__validate_orientation(ants.tests.TestCase):
    def setUp(self):
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_identity_crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, ellipsoid=self.sphere_crs
        )
        self.sphere_rotated_crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, 180.0, ellipsoid=self.sphere_crs
        )
        self.sphere_identity_target_lsm = CubeBuilder(
            self.sphere_identity_crs, (2, 2)
        )._cube
        self.sphere_rotated_target_lsm = CubeBuilder(
            self.sphere_rotated_crs, (2, 2)
        )._cube
        self.sphere_rotate_lon = geodetic(
            (2, 2), north_pole_lat=90.0, north_pole_lon=90.0, crs=self.sphere_crs
        )
        self.warning_msg = (
            "target_lsm has a geodetic coordinate system with pole located"
            "at grid_longitude=0.0, grid_latitude=90.0."
            "No transformation will be carried out."
        )

    def test_warning_raised(self):
        with self.assertWarnsRegex(UserWarning, self.warning_msg):
            _validate_orientation(self.sphere_identity_target_lsm)

    def test_no_warning_raised(self):
        self.assertTrue(_validate_orientation(self.sphere_rotate_lon))

    def test_no_warning_raised_rotated(self):
        # The pole can be optionally rotated in longitude after relocation.
        self.assertTrue(_validate_orientation(self.sphere_rotated_target_lsm))


class Test__transform_coordinates(ants.tests.TestCase):
    def setUp(self):
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_identity_crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, ellipsoid=self.sphere_crs
        )
        self.sphere_identity_target_lsm = CubeBuilder(
            self.sphere_identity_crs, (2, 2)
        )._cube
        self.sphere_source = geodetic((2, 2), crs=self.sphere_crs)
        self.sphere_equator_target_lsm = geodetic(
            (2, 2), north_pole_lat=0.0, north_pole_lon=0.0, crs=self.sphere_crs
        )
        self.sphere_rotate_lon = geodetic(
            (2, 2), north_pole_lat=90.0, north_pole_lon=90.0, crs=self.sphere_crs
        )
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
        # Rotation to pole at (0.0, 90.0).
        # Rotated geodesic by convention defines the new pole 180 degrees.
        # from passed longitude.

        true_lats = np.array([90, 45, 0, -45, -90])
        true_lons = np.array([np.nan, -180.0, -180.0, -180.0, -180.0])
        expected_rotation = np.array([true_lons, true_lats]).T

        # We cannot check the longitude at the pole (any longitude is valid).
        check_mask = ~np.isnan(expected_rotation)

        rotated_coords = _transform_coordinates(
            self.sphere_identity_target_lsm, self.sphere_source, self.vary_latitudes
        )
        self.assertArrayAlmostEqual(
            expected_rotation[check_mask], rotated_coords[check_mask]
        )

    def test_longitudinal_rotation(self):
        # Rotation to pole (90.0, 90.0).
        # The new pole is located at 270.0 after a 90.0 rotation.

        points = np.array([[0.0, 45.0, 90.0, 135.0], [0.0, 0.0, 0.0, 0.0]]).T
        true_lats = np.array([0.0, 0.0, np.nan, 0.0])
        true_lons = np.array([90.0, 135.0, -180.0, -135.0])
        expected_rotation = np.array([true_lons, true_lats]).T

        check_mask = ~np.isnan(expected_rotation)

        rotated_coords = _transform_coordinates(
            self.sphere_rotate_lon, self.sphere_source, points
        )

        self.assertArrayAlmostEqual(
            expected_rotation[check_mask], rotated_coords[check_mask]
        )

    def test_rotation_to_equator_sphere(self):
        # Rotation to pole at (0.0, 0.0).
        # Latitudes become longitudes and vice versa.

        true_lats = np.array([-45.0, 0.0, 45.0, 90.0, 45.0, 0.0, -45.0])
        true_lons = np.array([90.0, 90.0, 90.0, np.nan, -90.0, -90.0, -90.0])
        expected_rotation = np.array([true_lons, true_lats]).T
        check_mask = ~np.isnan(expected_rotation)
        rotated_coords = _transform_coordinates(
            self.sphere_equator_target_lsm, self.sphere_source, self.vary_longitudes
        )
        self.assertArrayAlmostEqual(
            expected_rotation[check_mask], rotated_coords[check_mask]
        )


class Test__validate_args(ants.tests.TestCase):

    def test_error_raised(self):
        args = argparse.Namespace(
            json_file="json/path",
            output="output/path",
            target_lsm=None,
            source_cube="source/path",
        )
        error_msg = "If --source-cube is passed then --target-lsm must also be given."
        with self.assertRaisesRegex(ValueError, error_msg):
            _validate_args(args.target_lsm, args.source_cube)


class Test__transform_if_required(ants.tests.TestCase):
    def setUp(self):
        self.points = np.array([[1, 2], [3, 4], [5, 6], [7, 8]])
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_source = geodetic((2, 2), crs=self.sphere_crs)
        self.sphere_equator_target_lsm = geodetic(
            (2, 2), north_pole_lat=0.0, north_pole_lon=0.0, crs=self.sphere_crs
        )
        self.sphere_identity_crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, ellipsoid=self.sphere_crs
        )
        self.sphere_identity_target_lsm = CubeBuilder(
            self.sphere_identity_crs, (2, 2)
        )._cube

    @mock.patch("ants.cli.ancil_create_shapefile._validate_orientation")
    @mock.patch("ants.cli.ancil_create_shapefile._transform_coordinates")
    @mock.patch("ants.cli.ancil_create_shapefile.CubeBuilder")
    @mock.patch("ants.cli.ancil_create_shapefile.load_landsea_mask")
    def test_transform_coords_not_called(
        self, mock_lsm, mock_source, mock_transform_coord, mock_validate
    ):

        mock_lsm.return_value = self.sphere_identity_target_lsm
        mock_validate.return_value = False

        rotated_points = _transform_if_required("lsm/path", None, self.points)

        mock_lsm.assert_called_once()
        mock_source.assert_called_once()
        mock_transform_coord.assert_not_called()
        self.assertArrayEqual(rotated_points, self.points)

    @mock.patch("ants.cli.ancil_create_shapefile._transform_coordinates")
    @mock.patch("ants.cli.ancil_create_shapefile.CubeBuilder")
    @mock.patch("ants.cli.ancil_create_shapefile.load_landsea_mask")
    def test_transform_called(self, mock_lsm, mock_source, mock_transform_coord):

        mock_lsm.return_value = self.sphere_equator_target_lsm

        _ = _transform_if_required("lsm/path", None, self.points)

        mock_lsm.assert_called_once()
        mock_source.assert_called_once()
        mock_transform_coord.assert_called_once()

    @mock.patch("ants.cli.ancil_create_shapefile.load_cube")
    @mock.patch("ants.cli.ancil_create_shapefile._transform_coordinates")
    @mock.patch("ants.cli.ancil_create_shapefile.CubeBuilder")
    @mock.patch("ants.cli.ancil_create_shapefile.load_landsea_mask")
    def test_source_cube_loaded(
        self, mock_lsm, mock_source, mock_transform_coord, mock_load_cube
    ):

        mock_lsm.return_value = self.sphere_equator_target_lsm

        _ = _transform_if_required("lsm/path", "source/path", self.points)

        mock_lsm.assert_called_once()
        mock_source.assert_not_called()
        mock_load_cube.assert_called_once()
        mock_transform_coord.assert_called_once()


class Test__load_polygon_from_json(ants.tests.TestCase):
    def setUp(self):
        self.json_values = [[1, 2], [3, 4], [5, 6], [7, 8]]

    @mock.patch("ants.cli.ancil_create_shapefile._transform_if_required")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("ants.cli.ancil_create_shapefile.json.load")
    def test_json_load(self, mock_json, mock_open, mock_transform):

        mock_json.return_value = self.json_values

        _ = _load_polygon_from_json("json/path", None, None)

        mock_json.assert_called_once()
        mock_transform.assert_not_called()

    @mock.patch("ants.cli.ancil_create_shapefile._transform_if_required")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("ants.cli.ancil_create_shapefile.json.load")
    def test_transform_called(self, mock_json, mock_open, mock_transform):

        mock_json.return_value = self.json_values

        _ = _load_polygon_from_json("json/path", "lsm/path", None)

        target_path, source_path, points = mock_transform.call_args.args
        mock_json.assert_called_once()
        mock_transform.assert_called_once()
        self.assertArrayEqual(points, self.json_values)
        self.assertEqual("lsm/path", target_path)
        self.assertEqual(None, source_path)

    @mock.patch("ants.cli.ancil_create_shapefile._transform_if_required")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("ants.cli.ancil_create_shapefile.json.load")
    def test_transform_called_with_source(self, mock_json, mock_open, mock_transform):

        mock_json.return_value = self.json_values

        _ = _load_polygon_from_json("json/path", "lsm/path", "source/path")

        target_path, source_path, points = mock_transform.call_args.args
        mock_json.assert_called_once()
        mock_transform.assert_called_once()
        self.assertArrayEqual(points, self.json_values)
        self.assertEqual("lsm/path", target_path)
        self.assertEqual("source/path", source_path)

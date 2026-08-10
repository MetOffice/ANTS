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
    _load_cubes,
    _load_points_from_json,
    _transform_coordinates,
    _transform_if_required,
    _validate_args,
    _validate_orientation,
)
from ants.tests.stock import geodetic
from ants.utils.cube import CubeBuilder


class Test__check_coord_system_type(ants.tests.TestCase):

    def test_unrotated_target_lsm(self):
        """Test that an error message is raised if the coordinate system in
        target_lsm is not a rotated pole."""

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
        """Test that a warning is raised with a coordinate system at latitude=90.0,
        longitude=0.0 is passed. Check the function returns False."""

        with self.assertWarnsRegex(UserWarning, self.warning_msg):
            valid_crs = _validate_orientation(self.sphere_identity_target_lsm)
        self.assertFalse(valid_crs)

    def test_true_returned(self):
        """Test that True is returned when target_lsm has a valid rotated pole."""

        self.assertTrue(_validate_orientation(self.sphere_rotate_lon))

    def test_no_warning_raised_rotated(self):
        """Test that passing a non-zero central rotated longitude is still
        accounted for when checking if the coordinate system is rotated."""

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
        self.sphere_source = CubeBuilder(self.sphere_crs, (2, 2))._cube
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
        """Test that rotation to a pole at latitude=90.0, longitude=0.0
        returns the same points, except a 180.0 degree rotation in longitude. By
        convention the new pole is defined 180.0 rotated from the provided
        longitude."""

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
        """Test rotation to a new pole at latitude=90.0, longitude=90.0.
        The new pole is located at latitude=90.0, longitude=270.0 in the rotated
        pole coordinate system."""

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
        """Test rotation to a new pole at latitude=0.0, longitude=0.0."""

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
        """Test that an error is raised if only --source-cube is passed."""

        args = argparse.Namespace(
            json_file="json/path",
            output="output/path",
            target_lsm=None,
            source_cube="source/path",
        )
        error_msg = "If --source-cube is passed then --target-lsm must also be given."
        with self.assertRaisesRegex(ValueError, error_msg):
            _validate_args(args.target_lsm, args.source_cube)


class Test__load_cubes(ants.tests.TestCase):
    def test_load_lsm_called(self):
        """Test that loading the landsea mask is successfully called."""

        with mock.patch(
            "ants.cli.ancil_create_shapefile.load_landsea_mask"
        ) as mock_lsm:
            _ = _load_cubes("target/path", None)

        mock_lsm.assert_called_once_with("target/path")

    @mock.patch("ants.cli.ancil_create_shapefile.load_landsea_mask")
    def test_cubebuilder_called(self, *args):
        """Test source cube created if no path given."""

        with mock.patch(
            "ants.cli.ancil_create_shapefile.CubeBuilder"
        ) as mock_build_cube:
            _ = _load_cubes("target/path", None)

        mock_build_cube.assert_called_once()

    @mock.patch("ants.cli.ancil_create_shapefile.load_landsea_mask")
    def test_load_cube_called(self, *args):
        """Test load cube called if source path given."""

        with mock.patch("ants.cli.ancil_create_shapefile.load_cube") as mock_load_cube:
            _ = _load_cubes("target/path", "source/cube")

        mock_load_cube.assert_called_once()


class Test__transform_if_required(ants.tests.TestCase):
    def setUp(self):
        self.points = np.array([[1, 2], [3, 4], [5, 6], [7, 8]])
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_source = CubeBuilder(self.sphere_crs, (2, 2))._cube
        self.sphere_equator_target_lsm = geodetic(
            (2, 2), north_pole_lat=0.0, north_pole_lon=0.0, crs=self.sphere_crs
        )
        self.sphere_identity_crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, ellipsoid=self.sphere_crs
        )
        self.sphere_identity_target_lsm = CubeBuilder(
            self.sphere_identity_crs, (2, 2)
        )._cube

    def test_non_rotated_returned(self):
        """Test that the input points are returned if a non-rotated pole is
        provided as the target_lsm."""

        with self.assertWarns(UserWarning):
            rotated_points = _transform_if_required(
                self.sphere_identity_target_lsm, self.sphere_source, self.points
            )

        self.assertArrayEqual(rotated_points, self.points)

    def test_transform_called(self):
        """Test that transform coordinates is called with the correct arguments
        when a valid target_lsm is given."""

        with mock.patch(
            "ants.cli.ancil_create_shapefile._transform_coordinates"
        ) as mock_transform:
            _ = _transform_if_required(
                self.sphere_equator_target_lsm, self.sphere_source, self.points
            )

        target_lsm, source_cube, points = mock_transform.call_args.args
        mock_transform.assert_called_once()
        self.assertEqual(target_lsm, self.sphere_equator_target_lsm)
        self.assertEqual(source_cube, self.sphere_source)
        self.assertArrayEqual(points, self.points)


@mock.patch("builtins.open", new_callable=mock.mock_open)
class Test__load_points_from_json(ants.tests.TestCase):
    def setUp(self):
        self.json_values = [[1, 2], [3, 4], [5, 6], [7, 8]]

    def test_json_load(self, *args):
        """Test that a json file is loaded."""

        with mock.patch("ants.cli.ancil_create_shapefile.json.load") as mock_json:
            _ = _load_points_from_json("json/path")

        mock_json.assert_called_once()

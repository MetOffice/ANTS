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
    _check_polygon_validity,
    _load_cubes,
    _transform_coordinates,
    _transform_if_required,
    _validate_args,
    _validate_orientation,
)
from ants.tests.stock import geodetic
from ants.utils.cube import CubeBuilder
from shapely.geometry import Polygon


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


class Test__check_polygon_validity(ants.tests.TestCase):
    def test_invalid_polygon(self):
        """Test that an invalid polygon with intersecting boundaries
        raises an error."""

        invalid_points = np.array([[1, 1], [-1, -1], [1, -1], [-1, 1]])
        invalid_poly = Polygon(invalid_points)
        is_ccw = False

        error_msg = "Polygon is invalid: "

        with self.assertRaisesRegex(ValueError, error_msg):
            _check_polygon_validity(invalid_poly, is_ccw)

    def test_changed_orientation(self):
        """Test that a change in polygon orientation raises an error."""

        ccw_points = np.array([[1, 1], [-1, 1], [-1, -1], [1, -1]])
        ccw_poly = Polygon(ccw_points)
        is_ccw = False

        error_msg = (
            "Polygon orientation has changed. Expected is_ccw=False, "
            "current polygon has is_ccw=True."
        )

        with self.assertRaisesRegex(ValueError, error_msg):
            _check_polygon_validity(ccw_poly, is_ccw)


class Test__validate_orientation(ants.tests.TestCase):
    def setUp(self):
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_identity_crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, ellipsoid=self.sphere_crs
        )

    def test_warning_raised(self):
        """Test that a warning is raised with a coordinate system at latitude=90.0,
        longitude=0.0 is passed. Check the function returns False."""

        target_lsm = CubeBuilder(self.sphere_identity_crs, (2, 2))._cube

        warning_msg = (
            "target_lsm has a geodetic coordinate system with pole located"
            " at grid_longitude=0.0, grid_latitude=90.0."
            " No transformation will be carried out."
        )

        with self.assertWarnsRegex(UserWarning, warning_msg):
            valid_crs = _validate_orientation(target_lsm)
        self.assertFalse(valid_crs)

    def test_true_returned(self):
        """Test that True is returned when target_lsm has a valid rotated pole."""

        target_lsm = geodetic(
            (2, 2), north_pole_lat=90.0, north_pole_lon=90.0, crs=self.sphere_crs
        )

        self.assertTrue(_validate_orientation(target_lsm))

    def test_no_warning_raised_rotated(self):
        """Test that passing a non-zero central rotated longitude is still
        accounted for when checking if the coordinate system is rotated."""

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        self.assertTrue(_validate_orientation(target_lsm))


class Test__transform_coordinates(ants.tests.TestCase):
    def setUp(self):
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_source = CubeBuilder(self.sphere_crs, (2, 2))._cube

    def test_identity_rotation_sphere(self):
        """Test that rotation to a pole at latitude=90.0, longitude=0.0
        returns the same points.

        By convention, rotated pole co-ordinate systems will set the prime
        meridian rotated 180.0 from the specified longitude. To place the
        prime meridian at 0.0, we apply a further rotation of 180.0, following
        rotation to the new pole.
        """

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        points = np.array([[10, 10], [10, -10], [-10, -10], [-10, 10]])

        expected_points = np.copy(points)

        rotated_coords = _transform_coordinates(target_lsm, self.sphere_source, points)
        self.assertArrayAlmostEqual(expected_points, rotated_coords)

    def test_longitudinal_rotation(self):
        """Test rotation to a new pole at latitude=90.0, longitude=90.0."""

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 90.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        points = np.array([[10, 10], [10, -10], [-10, -10], [-10, 10]])
        expected_points = np.array(
            [[-80.0, 10.0], [-80.0, -10.0], [-100.0, -10.0], [-100.0, 10]]
        )

        rotated_coords = _transform_coordinates(target_lsm, self.sphere_source, points)

        self.assertArrayAlmostEqual(expected_points, rotated_coords)

    def test_antimeridian_rotation(self):
        """Test rotation to a new pole at latitude=90.0, longitude=180.0."""

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 180.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        points = np.array([[10, 10], [10, -10], [-10, -10], [-10, 10]])
        expected_points = np.array(
            [[190.0, 10.0], [190.0, -10.0], [170.0, -10.0], [170.0, 10]]
        )

        warning_msg = re.escape(
            "The transformed points are assumed to cross the antimeridian. "
            "The longitudinal points will instead be defined in the interval"
            " [0, 360.0] degrees."
        )
        with self.assertWarnsRegex(UserWarning, warning_msg):
            rotated_coords = _transform_coordinates(
                target_lsm, self.sphere_source, points
            )

        self.assertArrayAlmostEqual(expected_points, rotated_coords)


class Test__validate_args(ants.tests.TestCase):

    def test_error_raised(self):
        """Test that an error is raised if only --source is passed."""

        args = argparse.Namespace(
            json_file="json/path",
            output="output/path",
            target_lsm=None,
            source="source/path",
        )
        error_msg = "If --source is passed then --target-lsm must also be given."
        with self.assertRaisesRegex(ValueError, error_msg):
            _validate_args(args.target_lsm, args.source)


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

    def test_non_rotated_returned(self):
        """Test that the input points are returned if a non-rotated pole is
        provided as the target_lsm."""

        crs = iris.coord_systems.RotatedGeogCS(90.0, 0.0, ellipsoid=self.sphere_crs)
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        with self.assertWarns(UserWarning):
            rotated_points = _transform_if_required(
                target_lsm, self.sphere_source, self.points
            )

        self.assertArrayEqual(rotated_points, self.points)

    def test_transform_called(self):
        """Test that transform coordinates is called with the correct arguments
        when a valid target_lsm is given."""

        crs = iris.coord_systems.RotatedGeogCS(0.0, 0.0, ellipsoid=self.sphere_crs)
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        with mock.patch(
            "ants.cli.ancil_create_shapefile._transform_coordinates"
        ) as mock_transform:
            _ = _transform_if_required(target_lsm, self.sphere_source, self.points)

        received_lsm, received_source, received_points = mock_transform.call_args.args
        mock_transform.assert_called_once()
        self.assertEqual(target_lsm, received_lsm)
        self.assertEqual(received_source, self.sphere_source)
        self.assertArrayEqual(received_points, self.points)


class Test_ite_transform(ants.tests.TestCase):

    def test_uk_pole_rotation(self):
        """
        Test the unrotated polygon enclosing regions of valid data from ITE
        expressed in true longitude and latitude is rotated correctly. The target
        pole is lon=177.5, lat=37.5.

        The points have been obtained by unrotating the coordinates in
        $UMDIR/ancil/data/shapefiles/ite_ukv_polygon/runme.py
        """
        points = np.array(
            [
                [1.63160953, 51.09703216],
                [-0.29556461, 50.36332573],
                [-5.37076475, 49.91322904],
                [-6.01981579, 50.15822986],
                [-5.16157337, 53.5014088],
                [-3.80608343, 53.99550534],
                [-4.04624456, 54.56480733],
                [-5.10119435, 54.47567927],
                [-5.95760936, 55.29939785],
                [-6.998891, 55.85406809],
                [-7.98467448, 56.73347598],
                [-7.65168129, 58.36692001],
                [-3.71924355, 61.09496898],
                [0.11346329, 61.0768747],
                [2.0703864, 52.72809453],
                [1.7594481, 51.23560201],
            ]
        )

        expected_points = np.array(
            [
                [362.594, -1.32876],
                [361.407, -2.1152],
                [358.15, -2.55],
                [357.744, -2.28679],
                [358.417, 1.03058],
                [359.232, 1.50245],
                [359.103, 2.07441],
                [358.488, 2.00291],
                [358.03, 2.84656],
                [357.472, 3.43282],
                [356.986, 4.34795],
                [357.286, 5.96374],
                [359.404, 8.6],
                [361.278, 8.6],
                [362.766, 0.315629],
                [362.666, -1.18577],
            ]
        )
        sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        source = CubeBuilder(sphere_crs, (2, 2))._cube
        crs = iris.coord_systems.RotatedGeogCS(37.5, 177.5, ellipsoid=sphere_crs)
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        rotated_points = _transform_if_required(target_lsm, source, points)

        # Adding 360.0 to longitude to compare to the expected points
        rotated_points[:, 0] += 360.0

        self.assertArrayAlmostEqual(rotated_points, expected_points)

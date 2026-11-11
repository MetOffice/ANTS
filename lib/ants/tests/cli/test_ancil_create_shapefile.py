# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
#
# Parts of this file have been created with the assistance of MetOffice
# Enterprise Copilot.

import re
import unittest
import warnings
from unittest import mock

import ants.tests
import iris
import numpy as np
from ants.cli.ancil_create_shapefile import (
    _check_coord_system_type,
    _check_polygon_validity,
    _check_within_domain,
    _load_cubes,
    _load_points_from_json,
    _make_contiguous,
    _transform_coordinates,
    _transform_if_required,
    _translate_lons_to_minimum,
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
        """Test that a warning is raised when a coordinate system at latitude=90.0,
        longitude=0.0 is passed. Check the function returns False."""

        target_lsm = CubeBuilder(self.sphere_identity_crs, (2, 2))._cube

        warning_msg = re.escape(
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

    def test_central_rotated_longitude(self):
        """Test that passing a non-zero central rotated longitude is still
        accounted for when checking if the coordinate system is rotated."""

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        self.assertTrue(_validate_orientation(target_lsm))


class Test__check_within_domain(ants.tests.TestCase):
    def setUp(self):
        self.rotated_points = np.array([[0, 10], [0, -10], [-20, -10], [-20, 10]])
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.crs = iris.coord_systems.RotatedGeogCS(
            90.0, 10.0, 180.0, ellipsoid=self.sphere_crs
        )
        self.warning_msg = re.escape(
            "The transformed points lie outside the target lsm domain."
        )

    def test_local_target_no_warning(self):
        """Test that no warning is emitted if the transformed polygon
        lies inside the target domain."""

        target_lsm = CubeBuilder(
            self.crs, (2, 2), xlim=(-25.0, 5.0), ylim=(-12, 12)
        )._cube

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            _check_within_domain(target_lsm, self.rotated_points)

    def test_local_target_no_warning_no_bounds(self):
        """Test that no warning is emitted when the target is passed
        without bounds."""

        target_lsm = CubeBuilder(
            self.crs,
            (2, 2),
            xlim=(-25.0, 5.0),
            ylim=(-12, 12),
            with_bounds=False,
        )._cube
        self.assertFalse(target_lsm.coord("grid_longitude").has_bounds())
        self.assertFalse(target_lsm.coord("grid_latitude").has_bounds())
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            _check_within_domain(target_lsm, self.rotated_points)

        # check that the bounds of the target lsm remain unchanged
        self.assertFalse(target_lsm.coord("grid_longitude").has_bounds())
        self.assertFalse(target_lsm.coord("grid_latitude").has_bounds())

    def test_local_target_longitude_warning(self):
        """Test that a warning is emitted if the transformed polygon
        lies at least partially outside of the valid target domain
        in longitude."""

        target_lsm = CubeBuilder(
            self.crs, (2, 2), xlim=(-10.0, 5.0), ylim=(-12, 12)
        )._cube

        with self.assertWarnsRegex(UserWarning, self.warning_msg):
            _check_within_domain(target_lsm, self.rotated_points)

    def test_local_target_latitude_warning(self):
        """Test that a warning is emitted if the transformed polygon
        lies at least partially outside of the valid target domain
        in latitude."""

        target_lsm = CubeBuilder(
            self.crs, (2, 2), xlim=(-25.0, 5.0), ylim=(-8, 12)
        )._cube

        with self.assertWarnsRegex(UserWarning, self.warning_msg):
            _check_within_domain(target_lsm, self.rotated_points)

    def test_global_target_warning(self):
        """Test that a warning is emitted if the transformed points lie
        outside the global target domain.

        The function makes no assumption about a global domain including
        all points and the comparisons are cartesian in nature.
        """

        target_lsm = CubeBuilder(self.crs, (2, 2), xlim=(0, 360.0))._cube

        with self.assertWarnsRegex(UserWarning, self.warning_msg):
            _check_within_domain(target_lsm, self.rotated_points)


class Test__translate_lons_to_minimum(ants.tests.TestCase):
    def test_translate_up(self):
        """Test translating longitudes to a specified minimum."""
        lons = np.array([-5, 0, 5])
        minimum_lon = 355
        expected_lons = np.array([355, 360, 365])
        translate_lons = _translate_lons_to_minimum(lons, minimum_lon)

        self.assertArrayEqual(translate_lons, expected_lons)

    def test_no_translation_above_minimum(self):
        """Test that no translation occurs if the minimum longitude
        already lies within [minimum_lon, minimum_lon + 360)."""
        lons = np.array([5, 20, 40])
        minimum_lon = 0
        expected_lons = np.array([5, 20, 40])
        translated_lons = _translate_lons_to_minimum(lons, minimum_lon)

        self.assertArrayEqual(translated_lons, expected_lons)

    def test_no_translation_at_minimum(self):
        """Test that no translation occurs if the longitudes are at the minimum."""
        lons = np.array([5, 20, 40])
        minimum_lon = 5
        expected_lons = np.array([5, 20, 40])
        translated_lons = _translate_lons_to_minimum(lons, minimum_lon)

        self.assertArrayEqual(translated_lons, expected_lons)

    def test_negative_minimum(self):
        """Test that no translation occurs with a negative minimum when
        the points already lie in range."""
        lons = np.array([-5, 0, 5])
        minimum_lon = -180.0
        expected_lons = np.array([-5, 0, 5])
        translated_lons = _translate_lons_to_minimum(lons, minimum_lon)

        self.assertArrayEqual(translated_lons, expected_lons)

    @unittest.skip("TODO: tolerance")
    def test_tolerance(self):
        # tolerance may need to be investigated
        pass


class Test__make_contiguous(ants.tests.TestCase):
    def test_points_made_contiguous(self):
        """Test that a set of points with longitude difference greater than
        180 emits a warning and large step differences are changed to the shorter
        complement.
        """
        rotated_points = np.array([[170, 10], [-170, 10], [-170, -10], [170, -10]])
        expected_points = np.array([[170, 10], [190, 10], [190, -10], [170, -10]])
        warning_msg = re.escape(
            "The transformed points are assumed to cross the antimeridian. "
            "The points will instead be defined so that a contiguous polygon "
            "can be made."
        )
        with self.assertWarnsRegex(UserWarning, warning_msg):
            rotated_points = _make_contiguous(rotated_points)
        self.assertArrayEqual(rotated_points, expected_points)

    def test_points_made_contiguous_positive(self):
        """Test that a set of points with longitude difference greater than
        180 emits a warning and that the longitudes are not unwrapped below -180
        degrees.
        """
        rotated_points = np.array([[-170, 10], [170, 10], [170, -10], [-170, -10]])
        expected_points = np.array([[190, 10], [170, 10], [170, -10], [190, -10]])
        warning_msg = re.escape(
            "The transformed points are assumed to cross the antimeridian. "
            "The points will instead be defined so that a contiguous polygon "
            "can be made."
        )
        with self.assertWarnsRegex(UserWarning, warning_msg):
            rotated_points = _make_contiguous(rotated_points)
        self.assertArrayEqual(rotated_points, expected_points)

    def test_points_not_changed(self):
        """Test that a set of valid points are not changed."""

        rotated_points = np.array([[100, 10], [110, 10], [110, -10], [100, -10]])
        expected_points = np.array([[100, 10], [110, 10], [110, -10], [100, -10]])

        rotated_points = _make_contiguous(rotated_points)
        self.assertArrayEqual(rotated_points, expected_points)

    def test_pole_encirclement(self):
        """Test a set of points that encircle the pole raise an error."""

        rotated_points = np.array(
            [[-170, 80], [-100, 70], [-20, 75], [40, 80], [100, 80], [150, 70]]
        )
        msg = "Points encircling a pole are not supported."
        with self.assertRaisesRegex(ValueError, msg):
            _ = _make_contiguous(rotated_points)

    def test_pole_encirclement_reverse_order(self):
        """Test a set of points encirlcing the pole in the opposite direction
        the pole raises an error."""

        rotated_points = np.array(
            [[150, 70], [100, 80], [40, 80], [-20, 75], [-100, 70], [-170, 80]]
        )
        msg = "Points encircling a pole are not supported."
        with self.assertRaisesRegex(ValueError, msg):
            _ = _make_contiguous(rotated_points)


class Test__transform_coordinates(ants.tests.TestCase):
    def setUp(self):
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_source = CubeBuilder(self.sphere_crs, (2, 2))._cube
        self.points = np.array([[10, 10], [10, -10], [-10, -10], [-10, 10]])

    def test_identity_rotation_sphere(self):
        """Test that rotation to a pole at latitude=90.0, longitude=0.0
        returns the same points.

        By convention, rotated pole coordinate systems will set the prime
        meridian rotated 180.0 from the specified longitude. To place the
        prime meridian at 0.0, we apply a further rotation of 180.0, following
        rotation to the new pole.
        """

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 0.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube
        expected_points = np.copy(self.points)
        rotated_coords = _transform_coordinates(
            target_lsm, self.sphere_source, self.points
        )

        self.assertArrayAlmostEqual(rotated_coords, expected_points)

    def test_longitudinal_rotation(self):
        """Test rotation to a new pole at latitude=90.0, longitude=90.0."""

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 90.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube
        expected_points = np.array(
            [[-80.0, 10.0], [-80.0, -10.0], [-100.0, -10.0], [-100.0, 10]]
        )

        rotated_coords = _transform_coordinates(
            target_lsm, self.sphere_source, self.points
        )

        self.assertArrayAlmostEqual(rotated_coords, expected_points)

    def test_no_antimeridian_correction(self):
        """Test that the rotated points are not corrected by
        _transform_coordinates."""

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 180.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube
        expected_points = np.array(
            [[-170, 10.0], [-170, -10.0], [170, -10.0], [170, 10]]
        )

        rotated_coords = _transform_coordinates(
            target_lsm, self.sphere_source, self.points
        )

        self.assertArrayAlmostEqual(rotated_coords, expected_points)


class Test__load_points_from_json(ants.tests.TestCase):
    def test_improperly_shaped_input(self):
        """Test that a json file with the incorrect shape will raise
        an error.
        """
        json_data = "[[1,2,3], [4,5,6], [7,8,9]]"
        mock_open = mock.mock_open(read_data=json_data)
        with mock.patch("builtins.open", mock_open):
            msg = re.escape(
                "The input longitude-latitude pairs must have shape (n, 2)."
            )

            with self.assertRaisesRegex(ValueError, msg):
                _load_points_from_json("json/path")


class Test__validate_args(ants.tests.TestCase):
    def test_source_without_target_lsm(self):
        """Test that an error is raised if --source is passed without
        --target-lsm."""
        error_msg = re.escape(
            "If --source is passed then --target-lsm must also be given."
        )
        with self.assertRaisesRegex(ValueError, error_msg):
            _validate_args(None, "source/path", None)

    def test_minimum_lon_without_target_lsm(self):
        """Test that an error is raised if --minimum-lon is passed without
        --target-lsm."""
        error_msg = re.escape(
            "If --minimum-lon is passed then --target-lsm must also be given."
        )
        with self.assertRaisesRegex(ValueError, error_msg):
            _validate_args(None, None, 0.0)

    def test_valid_args(self):
        """Test that no error is raised for valid arguments."""
        _validate_args(None, None, None)
        _validate_args("target/path", None, None)
        _validate_args("target/path", "source/path", 0.0)


class Test__load_cubes(ants.tests.TestCase):
    def test_load_lsm_called(self):
        """Test that loading the landsea mask is successfully called."""

        with mock.patch("ants.cli.ancil_create_shapefile.load_cube") as mock_load:
            _ = _load_cubes("target/path", None)

        mock_load.assert_called_once_with("target/path")

    @mock.patch("ants.cli.ancil_create_shapefile.load_cube")
    def test_cubebuilder_called(self, *args):
        """Test source cube created if no path given."""
        crs = iris.coord_systems.GeogCS(6371229.0)
        with mock.patch(
            "ants.cli.ancil_create_shapefile.CubeBuilder"
        ) as mock_build_cube:
            _ = _load_cubes("target/path", None)

        mock_build_cube.assert_called_once_with(crs, (2, 2))

    def test_load_cube_called(self):
        """Test load cube called if source path given."""

        with mock.patch("ants.cli.ancil_create_shapefile.load_cube") as mock_load:
            _ = _load_cubes("target/path", "source/cube")

        self.assertEqual(2, mock_load.call_count)


class Test__transform_if_required(ants.tests.TestCase):
    def setUp(self):
        self.points = np.array([[10, 10], [10, -10], [-10, -10], [-10, 10]])
        self.sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        self.sphere_source = CubeBuilder(self.sphere_crs, (2, 2))._cube
        self.minimum_lon = None

    @mock.patch("ants.cli.ancil_create_shapefile._transform_coordinates")
    def test_non_rotated_returned(self, mock_transform):
        """Test that the input points are returned if a non-rotated pole is
        provided as the target_lsm."""

        crs = iris.coord_systems.RotatedGeogCS(90.0, 0.0, ellipsoid=self.sphere_crs)
        target_lsm = CubeBuilder(crs, (2, 2))._cube
        warning_msg = re.escape(
            "target_lsm has a geodetic coordinate system with pole located"
            " at grid_longitude=0.0, grid_latitude=90.0."
            " No transformation will be carried out."
        )
        with self.assertWarnsRegex(UserWarning, warning_msg):
            rotated_points = _transform_if_required(
                target_lsm, self.sphere_source, self.points, self.minimum_lon
            )

        mock_transform.assert_not_called()
        self.assertArrayEqual(rotated_points, self.points)

    def test_transform_called(self):
        """Test that transform coordinates is called with the correct arguments
        when a valid target_lsm is given."""

        crs = iris.coord_systems.RotatedGeogCS(90.0, 80.0, ellipsoid=self.sphere_crs)
        target_lsm = CubeBuilder(crs, (2, 2))._cube

        with mock.patch(
            "ants.cli.ancil_create_shapefile._transform_coordinates"
        ) as mock_transform:
            mock_transform.return_value = self.points
            _ = _transform_if_required(
                target_lsm, self.sphere_source, self.points, self.minimum_lon
            )

        mock_transform.assert_called_once()
        received_lsm, received_source, received_points = mock_transform.call_args.args

        self.assertEqual(target_lsm, received_lsm)
        self.assertEqual(received_source, self.sphere_source)
        self.assertArrayEqual(received_points, self.points)

    def test_minimum_lon_call(self):
        """Test that _translate_lons_to_minimum is called when minimum_lon is
        not None."""

        crs = iris.coord_systems.RotatedGeogCS(90.0, 150.0, ellipsoid=self.sphere_crs)
        target_lsm = CubeBuilder(crs, (2, 2))._cube
        lons = np.array([40, 40, 20, 20])

        minimum_lon = 0.0
        with mock.patch(
            "ants.cli.ancil_create_shapefile._translate_lons_to_minimum"
        ) as mock_translate:
            mock_translate.return_value = lons
            _ = _transform_if_required(
                target_lsm, self.sphere_source, self.points, minimum_lon
            )

        mock_translate.assert_called_once()
        received_lons, received_minimum_lon = mock_translate.call_args.args
        self.assertArrayEqual(received_lons, lons)
        self.assertEqual(received_minimum_lon, minimum_lon)

    def test_antimeridian_rotation(self):
        """Test rotation to a new pole at latitude=90.0, longitude=180.0.
        In this case, the points are assumed to cross the antimeridian
        and so the negative longitudes are instead translated by +360.0
        degrees."""

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 180.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube
        expected_points = np.array(
            [[190.0, 10.0], [190.0, -10.0], [170.0, -10.0], [170.0, 10]]
        )
        warning_msg = re.escape(
            "The transformed points are assumed to cross the antimeridian. "
            "The points will instead be defined so that a contiguous polygon "
            "can be made."
        )

        with self.assertWarnsRegex(UserWarning, warning_msg):
            rotated_coords = _transform_if_required(
                target_lsm, self.sphere_source, self.points, self.minimum_lon
            )
        self.assertArrayAlmostEqual(rotated_coords, expected_points)

    def test_longitudinal_rotation_minimum_lon(self):
        """Test rotation to a new pole at latitude=90.0, longitude=90.0.
        We also pass the minimum_lon which is 0 and should translate the
        longitudes by +360.0 degrees.

        The intermediate array after rotation is
            [[-80, 10], [-80, -10], [-100, -10], [-100, 10]]
        """

        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 90.0, 180.0, ellipsoid=self.sphere_crs
        )
        # define the target lsm with a positive domain.
        target_lsm = CubeBuilder(crs, (2, 2), xlim=(0, 360.0))._cube
        expected_points = np.array(
            [[280.0, 10.0], [280.0, -10.0], [260.0, -10.0], [260.0, 10.0]]
        )
        minimum_lon = 0

        rotated_coords = _transform_if_required(
            target_lsm, self.sphere_source, self.points, minimum_lon
        )

        self.assertArrayAlmostEqual(rotated_coords, expected_points)

    def test_multiple_seam_crossings(self):
        """Test a valid set of points that would define a polygon crossing the
        antimeridian multiple times.

        In this specific example we must represent the unwrapped longitudes in
        a range wider than 360 degrees to preserve the topology of the polygon.
        """
        complex_points = np.array(
            [
                [-10, 20],
                [10, 20],
                [170, 10],
                [190, 10],
                [300, 3],
                [365, 0],
                [300, -3],
                [190, -10],
                [170, -10],
                [10, -20],
                [-10, -20],
                [10, 0],
            ]
        )
        expected_points = np.array(
            [
                [170, 20],
                [190, 20],
                [350, 10],
                [370, 10],
                [480, 3],
                [545, 0],
                [480, -3],
                [370, -10],
                [350, -10],
                [190, -20],
                [170, -20],
                [190, 0],
            ]
        )
        crs = iris.coord_systems.RotatedGeogCS(
            90.0, 180.0, 180.0, ellipsoid=self.sphere_crs
        )
        target_lsm = CubeBuilder(crs, (2, 2))._cube
        warning_msg = re.escape(
            "The transformed points are assumed to cross the antimeridian. "
            "The points will instead be defined so that a contiguous polygon "
            "can be made."
        )
        with self.assertWarnsRegex(UserWarning, warning_msg):
            rotated_coords = _transform_if_required(
                target_lsm, self.sphere_source, complex_points, None
            )

        self.assertArrayAlmostEqual(rotated_coords, expected_points)


class Test_ite_transform(ants.tests.TestCase):

    def test_uk_pole_rotation(self):
        """
        The following test uses points that define a validity polygon over the UK.

        The input points are specified in an unrotated geodetic coordinate system
        as (lon, lat) pairs. They are then rotated to a pole at lon=177.5,
        lat=37.5. Note that PROJ applies an additional 180.0 degree rotation
        to the specified pole location.

        The points have been obtained by unrotating the coordinates under
        $UMDIR/ancil/data/shapefiles/ite_ukv_polygon/runme.py, which can
        also be found as part of the ANTS rose-stem test suite under
        /data/users/ants/sources/ANTS/developer/core/ancil_create_shapefile/
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

        # Use the lower bound of the target lsm
        minimum_lon = 352.8725
        sphere_crs = iris.coord_systems.GeogCS(6371229.0)
        source = CubeBuilder(sphere_crs, (2, 2))._cube

        # Create a target lsm which is similar to the rose-stem source for
        # fill_n_merge.
        crs = iris.coord_systems.RotatedGeogCS(37.5, 177.5, ellipsoid=sphere_crs)
        target_lsm = CubeBuilder(crs, (93, 75), xlim=(352.8725, 365.261))._cube

        rotated_points = _transform_if_required(target_lsm, source, points, minimum_lon)
        self.assertArrayAlmostEqual(rotated_points, expected_points)

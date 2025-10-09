# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.fileformats.namelist import CAPGridRegular as CAPGrid


class Test___init__(ants.tests.TestCase):
    def setUp(self):
        self.defaults = {
            "grid": {
                "points_lambda_targ": None,
                "points_phi_targ": None,
                "lambda_origin_targ": 0.0,
                "phi_origin_targ": 90.0,
                "delta_lambda_targ": None,
                "delta_phi_targ": None,
                "phi_pole": 90.0,
                "lambda_pole": 0.0,
                "rotated": False,
                "global": True,
                "igrid_targ": 6,
                "inwsw": 0,
                "rotated_interp": None,
            }
        }

    def _check_defaults(self, object):
        for group in object._raw:
            for subkey in object._raw[group]:
                self.assertEqual(
                    object._raw[group][subkey], self.defaults[group][subkey]
                )

    def test_default_parameters(self):
        grid = CAPGrid({"grid": {}})
        self._check_defaults(grid)

    def test_unsupported_parameters(self):
        msg = ".*not currently being interpreted"
        with self.assertRaisesRegex(RuntimeError, msg):
            CAPGrid({"grid": {"rotated_interp": True}})


class Test__start_yx(ants.tests.TestCase):
    def test_all(self):
        targ_x = mock.sentinel.lambda_origin_targ
        targ_y = mock.sentinel.phi_origin_targ

        grid = CAPGrid(
            {"grid": {"lambda_origin_targ": targ_x, "phi_origin_targ": targ_y}}
        )
        (res_y, res_x) = grid._start_yx
        self.assertIs(res_x, targ_x)
        self.assertIs(res_y, targ_y)


class Test_shape(ants.tests.TestCase):
    def test_number_of_points_defined(self):
        # Shape determined directly
        sample = {"grid": {"points_lambda_targ": 30, "points_phi_targ": 30}}
        grid = CAPGrid(sample)
        (res_y, res_x) = grid.shape

        self.assertEqual(res_x, 30)
        self.assertEqual(res_y, 30)

    def test_inferred_global_grid_newdynamics(self):
        sample = {
            "grid": {
                "global": True,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 30,
                "igrid_targ": 3,
            }
        }
        grid = CAPGrid(sample)
        (res_y, res_x) = grid.shape
        self.assertIs(res_x, 12)
        self.assertIs(res_y, 7)

    def test_inferred_global_grid_endgame(self):
        sample = {
            "grid": {
                "global": True,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 30,
                "igrid_targ": 6,
            }
        }
        grid = CAPGrid(sample)
        (res_y, res_x) = grid.shape
        self.assertIs(res_x, 12)
        self.assertIs(res_y, 6)

    def test_inadequate_definition(self):
        sample = {"grid": {}}
        grid = CAPGrid(sample)
        msg = "Grid definition underspecified, cannot deduce x step size"
        with self.assertRaisesRegex(RuntimeError, msg):
            grid.shape

    def test_inadequate_global_definition(self):
        sample = {"grid": {"global": True}}
        grid = CAPGrid(sample)
        msg = "Grid definition underspecified, cannot deduce x step size"
        with self.assertRaisesRegex(RuntimeError, msg):
            grid.shape


class Test__step_yx(ants.tests.TestCase):
    def test_explicit_definition(self):
        sample = {"grid": {"delta_phi_targ": 30, "delta_lambda_targ": 30}}
        grid = CAPGrid(sample)
        (res_y, res_x) = grid._step_yx

        self.assertEqual(res_x, 30)
        self.assertEqual(res_y, -30)

    def test_implicit_global_definition_newdynamics(self):
        # Determining the step size by the fact that it is global and we know
        # the number of points.
        sample = {
            "grid": {
                "global": True,
                "points_lambda_targ": 30,
                "points_phi_targ": 73,
                "igrid_targ": 3,
            }
        }
        grid = CAPGrid(sample)
        (res_y, res_x) = grid._step_yx
        self.assertEqual(res_x, 12)
        self.assertEqual(res_y, -2.5)

    def test_implicit_global_definition_endgame(self):
        # Determining the step size by the fact that it is global and we know
        # the number of points.
        sample = {
            "grid": {
                "global": True,
                "points_lambda_targ": 30,
                "points_phi_targ": 72,
                "igrid_targ": 6,
            }
        }
        grid = CAPGrid(sample)
        (res_y, res_x) = grid._step_yx
        self.assertEqual(res_x, 12)
        self.assertEqual(res_y, -2.5)

    def test_underspecified(self):
        sample = {"grid": {}}
        grid = CAPGrid(sample)
        msg = "Grid definition underspecified, cannot deduce x step size"
        with self.assertRaisesRegex(RuntimeError, msg):
            grid._step_yx

    def test_contradictory_overspecified_lambda(self):
        sample = {
            "grid": {
                "global": True,
                "points_lambda_targ": 30,
                "delta_lambda_targ": 15,
                "points_phi_targ": 30,
            }
        }
        grid = CAPGrid(sample)
        msg = "Grid over specified. Contradictory longitude step size"
        with self.assertRaisesRegex(RuntimeError, msg):
            grid._step_yx

    def test_consistent_overspecified_lambda(self):
        sample = {
            "grid": {
                "global": True,
                "points_lambda_targ": 30,
                "delta_lambda_targ": 12,
                "points_phi_targ": 30,
            }
        }
        grid = CAPGrid(sample)
        (res_y, res_x) = grid._step_yx
        self.assertEqual(res_x, 12)

    def test_contradictory_overspecified_phi_endgame(self):
        sample = {
            "grid": {
                "global": True,
                "points_phi_targ": 72,
                "delta_phi_targ": 3,
                "igrid_targ": 6,
                "points_lambda_targ": 30,
            }
        }
        grid = CAPGrid(sample)
        msg = "Grid over specified. Contradictory latitude step size"
        with self.assertRaisesRegex(RuntimeError, msg):
            grid._step_yx

    def test_consistent_overspecified_phi_endgame(self):
        sample = {
            "grid": {
                "global": True,
                "points_phi_targ": 72,
                "delta_phi_targ": 2.5,
                "igrid_targ": 6,
                "points_lambda_targ": 30,
            }
        }
        grid = CAPGrid(sample)
        (res_y, res_x) = grid._step_yx
        self.assertEqual(res_y, -2.5)

    def test_contradictory_overspecified_phi_newdynamics(self):
        sample = {
            "grid": {
                "global": True,
                "points_phi_targ": 73,
                "delta_phi_targ": 3,
                "igrid_targ": 3,
                "points_lambda_targ": 30,
            }
        }
        grid = CAPGrid(sample)
        msg = "Grid over specified. Contradictory latitude step size"
        with self.assertRaisesRegex(RuntimeError, msg):
            grid._step_yx

    def test_consistent_overspecified_phi_newdynamics(self):
        sample = {
            "grid": {
                "global": True,
                "points_phi_targ": 73,
                "delta_phi_targ": 2.5,
                "igrid_targ": 3,
                "points_lambda_targ": 30,
            }
        }
        grid = CAPGrid(sample)
        (res_y, res_x) = grid._step_yx
        self.assertEqual(res_y, -2.5)


class Test_get_cube(ants.tests.TestCase):
    def test_x_values_extending_beyond_base_plus_period(self):
        # Ensure that we raise an exception for the case where our grid would
        # otherwise define cells which would overlap.
        sample = {
            "grid": {
                "global": False,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 200,
                "points_lambda_targ": 3,
                "lambda_origin_targ": 60.0,
                "phi_origin_targ": 60.0,
                "points_phi_targ": 10,
            }
        }
        grid = CAPGrid(sample)
        msg = r"x values overlap, points range: \(60.0, 460.0\)."
        with self.assertRaisesRegex(RuntimeError, msg):
            with mock.patch("warnings.warn"):
                grid.get_cube()

    def test_y_values_extending_beyond_expected_range_endgame(self):
        # Here we ensure that latitudes do not extend beyond [-90, 90].
        sample = {
            "grid": {
                "global": True,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 200,
                "lambda_origin_targ": 60.0,
                "phi_origin_targ": 30.0,
            }
        }
        grid = CAPGrid(sample)
        msg = (
            r"y value range \(-120.0, 30.0\) extends beyond the " r"\(-90, 90\) range."
        )
        with self.assertRaisesRegex(RuntimeError, msg):
            grid.get_cube()

    def test_y_values_extending_beyond_expected_range_newdynamics(self):
        # Here we ensure that latitudes do not extend beyond [-90, 90].
        sample = {
            "grid": {
                "global": True,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 200,
                "lambda_origin_targ": 60.0,
                "phi_origin_targ": 30.0,
                "igrid_targ": 3,
            }
        }
        grid = CAPGrid(sample)
        msg = (
            r"y value range \(-150.0, 30.0\) extends beyond the " r"\(-90, 90\) range."
        )
        with self.assertRaisesRegex(RuntimeError, msg):
            grid.get_cube()

    def test_global_geodetic_newdynamics(self):
        expected = ants.tests.stock.geodetic((7, 12), xlim=(-15, 345))
        # Need to manually set up latitude for New Dynamics.
        latitude = iris.coords.DimCoord(
            points=[90.0, 60.0, 30.0, 0.0, -30.0, -60.0, -90.0],
            bounds=[
                [90.0, 75.0],
                [75.0, 45.0],
                [45.0, 15.0],
                [15.0, -15.0],
                [-15.0, -45.0],
                [-45.0, -75.0],
                [-75.0, -90.0],
            ],
            standard_name="latitude",
            units="degrees",
            coord_system=expected.coord(axis="y").coord_system,
        )
        expected.remove_coord("latitude")
        expected.add_dim_coord(latitude, 0)
        expected.attributes["grid_staggering"] = 3
        expected.data = np.zeros_like(expected.data, dtype=np.float64)
        expected.rename("Model Grid")

        sample = {
            "grid": {
                "global": True,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 30,
                "igrid_targ": 3,
            }
        }
        grid = CAPGrid(sample)
        actual = grid.get_cube()

        self.assertEqual(actual, expected)

    def test_global_geodetic_endgame(self):
        expected = ants.tests.stock.geodetic((6, 12), xlim=(-15, 345), ylim=(90, -90))
        expected.attributes["grid_staggering"] = 6
        expected.data = np.zeros_like(expected.data, dtype=np.float64)
        expected.rename("Model Grid")

        sample = {
            "grid": {
                "global": True,
                "phi_origin_targ": 75,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 30,
                "lamda_origin_targ": -165,
                "igrid_targ": 6,
            }
        }
        grid = CAPGrid(sample)
        actual = grid.get_cube()

        self.assertEqual(actual, expected)

    def test_regional_geodetic_SN(self):
        # Ensure that the result remains North-south (i.e. the UM convention to
        # apply this inversion takes place within apply_um_conventions).
        expected = ants.tests.stock.geodetic((3, 3), xlim=(10, 40), ylim=(30, 0))
        expected.attributes["grid_staggering"] = 6
        expected.data = np.zeros_like(expected.data, dtype=np.float64)
        expected.rename("Model Grid")

        sample = {
            "grid": {
                "global": False,
                "points_phi_targ": 3,
                "points_lambda_targ": 3,
                "delta_phi_targ": 10,
                "delta_lambda_targ": 10,
                "lambda_origin_targ": 15.0,
                "phi_origin_targ": 25.0,
                "inwsw": 0,
            }
        }
        grid = CAPGrid(sample)
        actual = grid.get_cube()

        self.assertEqual(actual, expected)

    def test_regional_geodetic_NS(self):
        expected = ants.tests.stock.geodetic((3, 3), xlim=(10, 40), ylim=(20, 50))
        expected.attributes["grid_staggering"] = 6
        expected.data = np.zeros_like(expected.data, dtype=np.float64)
        expected.rename("Model Grid")

        sample = {
            "grid": {
                "global": False,
                "points_phi_targ": 3,
                "points_lambda_targ": 3,
                "delta_phi_targ": 10,
                "delta_lambda_targ": 10,
                "lambda_origin_targ": 15.0,
                "phi_origin_targ": 25.0,
                "inwsw": 1,
            }
        }
        grid = CAPGrid(sample)
        actual = grid.get_cube()

        self.assertEqual(actual, expected)

    def test_attributes_gridtype(self):
        # Ensure that the grid type is recorded onto the resulting cube.
        sample = {
            "grid": {
                "global": True,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 30,
                "igrid_targ": 6,
            }
        }
        grid = CAPGrid(sample)
        cube = grid.get_cube()
        self.assertTrue("grid_staggering" in cube.attributes)
        self.assertEqual(cube.attributes["grid_staggering"], 6)


class Test_attributes(ants.tests.TestCase):
    def test_gridtype(self):
        sample = {
            "grid": {
                "global": True,
                "delta_phi_targ": 30,
                "delta_lambda_targ": 30,
                "igrid_targ": 6,
            }
        }
        grid = CAPGrid(sample)
        target = {"grid_staggering": 6}
        self.assertEqual(grid.attributes, target)


class Test_x(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("warnings.warn")
        self.mock_warnings = patch.start()
        self.addCleanup(patch.stop)

    def test_newdynamics_n48(self):
        sample = {
            "grid": {
                "points_lambda_targ": 96,
                "points_phi_targ": 73,
                "lambda_origin_targ": 0.0,
                "phi_origin_targ": 90.0,
                "phi_pole": 90.0,
                "lambda_pole": 0.0,
                "rotated": False,
                "igrid_targ": 3,
            }
        }
        grid = CAPGrid(sample)
        target = np.linspace(0.0, 356.25, 96, endpoint=True)
        self.assertArrayAlmostEqual(grid.x.points, target)

    def test_endgame_n48(self):
        sample = {
            "grid": {
                "points_lambda_targ": 96,
                "points_phi_targ": 72,
                "lambda_origin_targ": 1.875,
                "phi_origin_targ": 88.75,
                "phi_pole": 90.0,
                "lambda_pole": 0.0,
                "rotated": False,
                "delta_lambda_targ": 3.75,
                "delta_phi_targ": 2.5,
                "igrid_targ": 6,
            }
        }
        grid = CAPGrid(sample)
        target = np.linspace(1.875, 358.125, 96, endpoint=True)
        self.assertArrayAlmostEqual(grid.x.points, target)


class Test_y(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("warnings.warn")
        self.mock_warnings = patch.start()
        self.addCleanup(patch.stop)

    def test_newdynamics_n48(self):
        sample = {
            "grid": {
                "points_lambda_targ": 96,
                "points_phi_targ": 73,
                "lambda_origin_targ": 0.0,
                "phi_origin_targ": 90.0,
                "phi_pole": 90.0,
                "lambda_pole": 0.0,
                "rotated": False,
                "igrid_targ": 3,
            }
        }
        grid = CAPGrid(sample)
        target = np.linspace(90.0, -90.0, 73, endpoint=True)
        self.assertArrayAlmostEqual(grid.y.points, target)

    def test_endgame_n48(self):
        sample = {
            "grid": {
                "points_lambda_targ": 96,
                "points_phi_targ": 72,
                "lambda_origin_targ": 1.875,
                "phi_origin_targ": 88.75,
                "phi_pole": 90.0,
                "lambda_pole": 0.0,
                "rotated": False,
                "delta_lambda_targ": 3.75,
                "delta_phi_targ": 2.5,
                "igrid_targ": 6,
            }
        }
        grid = CAPGrid(sample)
        target = np.linspace(88.75, -88.75, 72, endpoint=True)
        self.assertArrayAlmostEqual(grid.y.points, target)


class Test_is_endgame(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("warnings.warn")
        self.mock_warnings = patch.start()
        self.addCleanup(patch.stop)

    def test_newdynamics(self):
        sample = {
            "grid": {
                "points_lambda_targ": 96,
                "points_phi_targ": 73,
                "lambda_origin_targ": 0.0,
                "phi_origin_targ": 90.0,
                "phi_pole": 90.0,
                "lambda_pole": 0.0,
                "rotated": False,
                "igrid_targ": 3,
            }
        }
        grid = CAPGrid(sample)
        self.assertFalse(grid.is_endgame)

    def test_endgame(self):
        sample = {
            "grid": {
                "points_lambda_targ": 96,
                "points_phi_targ": 72,
                "lambda_origin_targ": 1.875,
                "phi_origin_targ": 88.75,
                "phi_pole": 90.0,
                "lambda_pole": 0.0,
                "rotated": False,
                "delta_lambda_targ": 3.75,
                "delta_phi_targ": 2.5,
                "igrid_targ": 6,
            }
        }
        grid = CAPGrid(sample)
        self.assertTrue(grid.is_endgame)


if __name__ == "__main__":
    ants.tests.main()

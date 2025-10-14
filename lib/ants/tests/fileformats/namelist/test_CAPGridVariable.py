# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.fileformats.namelist import CAPGridVariable as CAPGrid


class Test___init__(ants.tests.TestCase):
    def setUp(self):
        self.defaults = {
            "grid": {"lambda_pole": 0.0, "phi_pole": 90.0},
            "horizgrid": {
                "lambda_input_p": None,
                "lambda_input_u": None,
                "phi_input_p": None,
                "phi_input_v": None,
            },
        }

    def _check_defaults(self, object):
        for group in object._raw:
            for subkey in object._raw[group]:
                self.assertEqual(
                    object._raw[group][subkey], self.defaults[group][subkey]
                )

    def test_default_parameters(self):
        grid = CAPGrid({"grid": {}, "horizgrid": {}})
        self._check_defaults(grid)


class Test_shape(ants.tests.TestCase):
    def test_value(self):
        sample = {
            "horizgrid": {"lambda_input_p": [1, 2, 3], "phi_input_p": [1, 2, 3, 4]},
            "grid": {},
        }
        grid = CAPGrid(sample)
        self.assertEqual(grid.shape, (4, 3))

    def test_ignored_disagreeing_metadata(self):
        # Ensure that the metadata is ignored when a variable resolution grid.
        sample = {
            "horizgrid": {"lambda_input_p": [1, 2, 3], "phi_input_p": [1, 2, 3, 4]},
            "grid": {"points_lambda_targ": 30, "points_phi_targ": 30},
        }
        grid = CAPGrid(sample)
        self.assertEqual(grid.shape, (4, 3))


class Test_get_cube(ants.tests.TestCase):
    def test_endgame(self):
        # Ensure that the grid type is recorded onto the resulting cube.
        sample = {
            "horizgrid": {
                "lambda_input_p": [1, 2, 3],
                "lambda_input_u": [1.5, 2.5, 3.5],
                "phi_input_p": [1, 2, 3],
                "phi_input_v": [0.5, 1.5, 2.5],
            },
            "grid": {},
        }
        grid = CAPGrid(sample)
        cube = grid.get_cube()
        self.assertTrue("grid_staggering" in cube.attributes)
        self.assertEqual(cube.attributes["grid_staggering"], 3)

    def test_newdynamics(self):
        sample = {
            "horizgrid": {
                "lambda_input_p": [1, 2, 3],
                "lambda_input_u": [0.5, 1.5, 2.5],
                "phi_input_p": [1, 2, 3],
                "phi_input_v": [0.5, 1.5, 2.5],
            },
            "grid": {},
        }
        grid = CAPGrid(sample)
        cube = grid.get_cube()
        for axis in ["x", "y"]:
            self.assertArrayEqual(cube.coord(axis=axis).points, [1, 2, 3])
            self.assertArrayEqual(
                cube.coord(axis="x").bounds, [[0.5, 1.5], [1.5, 2.5], [2.5, 3.5]]
            )
        self.assertTrue("grid_staggering" in cube.attributes)
        self.assertEqual(cube.attributes["grid_staggering"], 6)


class Test_attributes(ants.tests.TestCase):
    # Variable resolution grids are defined explicitly and so we ignore
    # igrid_targ and instead derive its state.
    def test_gridtype(self):
        sample = {
            "grid": {"igrid_targ": 6},
            "horizgrid": {
                "lambda_input_p": [1, 2, 3],
                "lambda_input_u": [1.5, 2.5, 3.5],
            },
        }
        grid = CAPGrid(sample)
        target = {"grid_staggering": 3}
        self.assertEqual(grid.attributes, target)

    def test_gridtype_newdynamics(self):
        sample = {
            "grid": {"igrid_targ": 3},
            "horizgrid": {
                "lambda_input_p": [1, 2, 3],
                "lambda_input_u": [0.5, 1.5, 2.5],
            },
        }
        grid = CAPGrid(sample)
        target = {"grid_staggering": 6}
        self.assertEqual(grid.attributes, target)


class Test_x(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("warnings.warn")
        self.mock_warnings = patch.start()
        self.addCleanup(patch.stop)

    def test_disagree_meta(self):
        # Ensure that the metadata is ignored when a variable resolution grid.
        sample = {
            "horizgrid": {
                "lambda_input_p": [1, 2, 3],
                "lambda_input_u": [1.5, 2.5, 3.5],
            }
        }
        sample.update(
            {
                "grid": {
                    "points_lambda_targ": 96,
                    "points_phi_targ": 73,
                    "lambda_origin_targ": 0.0,
                    "phi_origin_targ": 90.0,
                    "phi_pole": 90.0,
                    "lambda_pole": 0.0,
                    "rotated": False,
                }
            }
        )
        grid = CAPGrid(sample)
        self.assertArrayEqual(grid.x.points, [1, 2, 3])
        self.assertArrayEqual(grid.x.bounds, [[0.5, 1.5], [1.5, 2.5], [2.5, 3.5]])

    def assert_x(self, sample):
        grid = CAPGrid(sample)
        target = [1, 2, 3]
        self.assertArrayAlmostEqual(grid.x.points, target)

        target = [[0.5, 1.5], [1.5, 2.5], [2.5, 3.5]]
        self.assertArrayAlmostEqual(grid.x.bounds, target)

    def test_u_below(self):
        sample = {
            "horizgrid": {
                "lambda_input_p": [1, 2, 3],
                "lambda_input_u": [0.5, 1.5, 2.5],
            },
            "grid": {},
        }
        self.assert_x(sample)

    def test_u_above(self):
        sample = {
            "horizgrid": {
                "lambda_input_p": [1, 2, 3],
                "lambda_input_u": [1.5, 2.5, 3.5],
            },
            "grid": {},
        }
        self.assert_x(sample)

    def test_u_above_and_below(self):
        sample = {
            "horizgrid": {
                "lambda_input_p": [1, 2, 3],
                "lambda_input_u": [0.5, 1.5, 2.5, 3.5],
            },
            "grid": {},
        }
        self.assert_x(sample)

    def test_u_neither_above_or_below(self):
        sample = {
            "horizgrid": {"lambda_input_p": [1, 2, 3], "lambda_input_u": [1.5, 2.5]},
            "grid": {},
        }
        self.assert_x(sample)


class Test_y(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("warnings.warn")
        self.mock_warnings = patch.start()
        self.addCleanup(patch.stop)

    def test_disagree_meta(self):
        # Ensure that the metadata is ignored when a variable resolution grid.
        sample = {
            "horizgrid": {"phi_input_p": [1, 2, 3], "phi_input_v": [0.5, 1.5, 2.5]}
        }
        sample.update(
            {
                "grid": {
                    "points_lambda_targ": 96,
                    "points_phi_targ": 73,
                    "lambda_origin_targ": 0.0,
                    "phi_origin_targ": 90.0,
                    "phi_pole": 90.0,
                    "lambda_pole": 0.0,
                    "rotated": False,
                }
            }
        )
        grid = CAPGrid(sample)
        self.assertArrayEqual(grid.y.points, [1, 2, 3])
        self.assertArrayEqual(grid.y.bounds, [[0.5, 1.5], [1.5, 2.5], [2.5, 3.5]])

    def assert_y(self, sample):
        grid = CAPGrid(sample)
        target = [1, 2, 3]
        self.assertArrayAlmostEqual(grid.y.points, target)

        target = [[0.5, 1.5], [1.5, 2.5], [2.5, 3.5]]
        self.assertArrayAlmostEqual(grid.y.bounds, target)

    def test_v_below(self):
        sample = {
            "horizgrid": {"phi_input_p": [1, 2, 3], "phi_input_v": [0.5, 1.5, 2.5]},
            "grid": {},
        }
        self.assert_y(sample)

    def test_v_above(self):
        sample = {
            "horizgrid": {"phi_input_p": [1, 2, 3], "phi_input_v": [1.5, 2.5, 3.5]},
            "grid": {},
        }
        self.assert_y(sample)

    def test_v_above_and_below(self):
        sample = {
            "horizgrid": {
                "phi_input_p": [1, 2, 3],
                "phi_input_v": [0.5, 1.5, 2.5, 3.5],
            },
            "grid": {},
        }
        self.assert_y(sample)

    def test_v_neither_above_or_below(self):
        sample = {
            "horizgrid": {"phi_input_p": [1, 2, 3], "phi_input_v": [1.5, 2.5]},
            "grid": {},
        }
        self.assert_y(sample)

    def test_variable_resolution_newdynamics(self):
        sample = {
            "horizgrid": {"phi_input_p": [1, 2, 3], "phi_input_v": [1.5, 2.5, 3.5]},
            "grid": {},
        }
        grid = CAPGrid(sample)
        self.assertArrayEqual(grid.y.points, [1, 2, 3])
        self.assertArrayEqual(grid.y.bounds, [[0.5, 1.5], [1.5, 2.5], [2.5, 3.5]])

    def test_points_bounds_inversion(self):
        # Ensure that the points and bounds is not inverted - this should be
        # done as part of apply_um_conventions.
        sample = {
            "horizgrid": {"phi_input_p": [3, 2, 1], "phi_input_v": [2.5, 1.5, 0.5]},
            "grid": {},
        }
        grid = CAPGrid(sample)
        self.assertArrayEqual(grid.y.points, [3, 2, 1])
        self.assertArrayEqual(grid.y.bounds, [[3.5, 2.5], [2.5, 1.5], [1.5, 0.5]])


if __name__ == "__main__":
    ants.tests.main()

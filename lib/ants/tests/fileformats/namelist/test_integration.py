# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock
from io import StringIO

import ants.tests
import iris
import numpy as np
from ants.fileformats.namelist import (
    load_cap_horizontal,
    load_lfric_vertical,
    load_um_vertical,
)


@ants.tests.skip_f90nml
class TestHorizontal(ants.tests.TestCase):

    def run_regular(self, callback=None):
        data = """&GRID
 POINTS_LAMBDA_TARG=2,POINTS_PHI_TARG=2,PHI_ORIGIN_TARG=45
/
"""
        file1 = StringIO(data)
        filename = "dummy_filename"
        patch_open = mock.patch("f90nml.parser.open", create=True, return_value=file1)
        with patch_open:
            cube = next(load_cap_horizontal(filename, callback=callback))
        return cube

    def test_regular(self):
        expected = ants.tests.stock.geodetic((2, 2), xlim=(-90, 270))
        expected.attributes["grid_staggering"] = 6
        expected.data = np.zeros_like(expected.data, dtype=np.float64)
        expected.rename("Model Grid")

        actual = self.run_regular()

        self.assertEqual(actual, expected)

    def test_callback(self):
        def my_callback(cube, groups, filename):
            cube.attributes["dummy_change"] = "flop"

        cube = self.run_regular(callback=my_callback)
        self.assertEqual(cube.attributes["dummy_change"], "flop")

    def test_variable_resolution(self):
        expected = ants.tests.stock.geodetic((3, 3), xlim=(0.5, 3.5), ylim=(0.5, 3.5))
        expected.attributes["grid_staggering"] = 3
        expected.data = np.zeros_like(expected.data, dtype=np.float64)
        expected.rename("Model Grid")

        data = """&GRID
 POINTS_LAMBDA_TARG=2,POINTS_PHI_TARG=2
/
"""
        file1 = StringIO(data)

        data = """&HORIZGRID
 LAMBDA_INPUT_P=1., 2., 3.
 LAMBDA_INPUT_U=1.5, 2.5, 3.5
 PHI_INPUT_P=1., 2., 3.
 PHI_INPUT_V=0.5, 1.5, 2.5
/
"""
        file2 = StringIO(data)

        filenames = ["filename1", "filename2"]
        patch_open = mock.patch(
            "f90nml.parser.open", create=True, side_effect=[file1, file2]
        )
        with patch_open:
            actual = next(load_cap_horizontal(filenames))

        self.assertEqual(actual, expected)


@ants.tests.skip_f90nml
class TestVertical(ants.tests.TestCase):
    def setUp(self, callback=None):
        data = """&VERTLEVS
z_top_of_model = 5.0
first_constant_r_rho_level = 3
eta_theta = 0.0, 0.1, 0.225, 0.4, 0.6, 1.0
eta_rho = 0.05, 0.1625, 0.3125, 0.5, 0.8
/
"""
        self.file1 = StringIO(data)
        self.filename = "filename"

    def _run_um_vertical(self, callback=None):
        patch_open = mock.patch(
            "f90nml.parser.open", create=True, return_value=self.file1
        )
        with patch_open:
            cube = next(load_um_vertical(self.filename, callback=callback))
        return cube

    def _run_lfric_vertical(self, callback=None):
        patch_open = mock.patch(
            "f90nml.parser.open", create=True, return_value=self.file1
        )
        with patch_open:
            cube = next(load_lfric_vertical(self.filename, callback=callback))
        return cube

    def test_um_vertical_model_level_number(self):
        expected = iris.coords.DimCoord(
            range(1, 6),
            standard_name="model_level_number",
            attributes={"positive": "up"},
            units=1,
        )

        cube = self._run_um_vertical()
        actual = cube.coord("model_level_number")

        self.assertEqual(actual, expected)

    def test_um_vertical_sigma(self):
        expected = iris.coords.AuxCoord(
            points=[0.4624, 0.0784, 0.0, 0.0, 0.0],
            bounds=[[1.0, 0.2304], [0.2304, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
            long_name="sigma",
            units=1,
        )

        cube = self._run_um_vertical()
        actual = cube.coord("sigma")

        # Expected points have rounding differences to the actual points.  So
        # we'll use three asserts here rather than just cube equality, to let
        # us use assertArrayAlmostEqual in point calculations.  Can use
        # `np.set_printoptions(precision=20)` and print the points array to see
        # the difference.
        self.assertArrayAlmostEqual(actual.points, expected.points)
        self.assertEqual(actual.metadata, expected.metadata)
        self.assertArrayEqual(actual.bounds, expected.bounds)

    def test_um_vertical_level_height(self):
        expected = iris.coords.AuxCoord(
            points=[0.5, 1.125, 2.0, 3.0, 5.0],
            bounds=[
                [0.0, 0.8125],
                [0.8125, 1.5625],
                [1.5625, 2.5],
                [2.5, 4.0],
                [4.0, 6.0],
            ],
            attributes={"positive": "up"},
            var_name="level_height",
            units="m",
        )

        cube = self._run_um_vertical()
        actual = cube.coord("level_height")

        self.assertEqual(actual, expected)

    def test_lfric_vertical_model_level_number(self):
        expected = iris.coords.DimCoord(
            range(6),
            standard_name="model_level_number",
            attributes={"positive": "up"},
            units=1,
        )

        cube = self._run_lfric_vertical()
        actual = cube.coord("model_level_number")

        self.assertEqual(actual, expected)

    def test_lfric_vertical_sigma(self):
        expected = iris.coords.AuxCoord(
            points=[1.0, 0.4624, 0.0784, 0.0, 0.0, 0.0],
            bounds=[
                [1.0, 0.7056],
                [0.7056, 0.2304],
                [0.2304, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
            ],
            long_name="sigma",
            units=1,
        )

        cube = self._run_lfric_vertical()
        actual = cube.coord("sigma")
        # Expected points and bounds have rounding differences to the actual
        # values.  So we'll use three asserts here rather than just cube
        # equality, to let us use assertArrayAlmostEqual in the calculations.
        # Can use `np.set_printoptions(precision=20)` and print the array to
        # see the difference.
        self.assertArrayAlmostEqual(actual.points, expected.points)
        self.assertEqual(actual.metadata, expected.metadata)
        self.assertArrayAlmostEqual(actual.bounds, expected.bounds)

    def test_lfric_vertical_level_height(self):
        expected = iris.coords.AuxCoord(
            points=[0.0, 0.5, 1.125, 2.0, 3.0, 5.0],
            bounds=[
                [0.0, 0.25],
                [0.25, 0.8125],
                [0.8125, 1.5625],
                [1.5625, 2.5],
                [2.5, 4.0],
                [4.0, 6.0],
            ],
            attributes={"positive": "up"},
            var_name="level_height",
            units="m",
        )

        cube = self._run_lfric_vertical()
        actual = cube.coord("level_height")

        self.assertEqual(actual, expected)

    def test_callback(self):
        def my_callback(cube, groups, filename):
            cube.attributes["dummy_change"] = "flop"

        cube = self._run_um_vertical(callback=my_callback)
        self.assertEqual(cube.attributes["dummy_change"], "flop")


if __name__ == "__main__":
    ants.tests.main()

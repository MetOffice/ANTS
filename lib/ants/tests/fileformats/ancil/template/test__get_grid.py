# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
import numpy
from ants.fileformats.ancil.template import (
    _check_non_vertical_coords_f03_compatible,
    _get_grid,
)


class TestNonVerticalCoordinates(ants.tests.TestCase):
    def test_check_non_vertical_coords_f03_compatible(self):
        cube = ants.tests.stock.geodetic((2, 2, 2))
        cube.attributes["STASH"] = "m01s01i001"
        self.assertEqual(None, _check_non_vertical_coords_f03_compatible([cube]))

    def test_check_non_vertical_coords_f03_compatible_invalid_coordinates(self):
        # <U3 is 3 characters of little endian unicode:
        # https://numpy.org/doc/stable/reference/arrays.dtypes.html
        broken_coordinate = iris.coords.AuxCoord(
            numpy.array([1, 2], dtype="<U3"), long_name="month_number"
        )

        cube = ants.tests.stock.geodetic((2, 2, 2))
        cube.add_aux_coord(broken_coordinate, data_dims=[0])
        cube.attributes["STASH"] = "m01s01i001"
        with self.assertRaisesRegex(
            RuntimeError, "Invalid values found in month_number coordinate."
        ):
            _check_non_vertical_coords_f03_compatible([cube])


class TestGetGrid(ants.tests.TestCase):
    def test_get_grid(self):
        cube = ants.tests.stock.geodetic((2, 2, 2))
        cube.attributes["STASH"] = "m01s01i001"
        self.assertEqual(_get_grid([cube]), 6)

    def test_get_grid_one_cube_with_invalid_coordinates(self):
        # <U3 is 3 characters of little endian unicode:
        # https://numpy.org/doc/stable/reference/arrays.dtypes.html
        broken_coordinate = iris.coords.AuxCoord(
            numpy.array([1, 2], dtype="<U3"), long_name="month_number"
        )

        cube = ants.tests.stock.geodetic((2, 2, 2))
        cube.add_aux_coord(broken_coordinate, data_dims=[0])
        cube.attributes["STASH"] = "m01s01i001"

        msg = "Invalid values found in month_number coordinate."
        with self.assertRaisesRegex(RuntimeError, msg):
            _get_grid([cube])

    def test_get_grid_three_cubes_and_two_have_invalid_coordinates(self):
        # <U3 is 3 characters of little endian unicode:
        # https://numpy.org/doc/stable/reference/arrays.dtypes.html
        broken_coordinate = iris.coords.AuxCoord(
            numpy.array([1, 2], dtype="<U3"), long_name="month_number"
        )

        my_cubes = []

        cube1 = ants.tests.stock.geodetic((2, 2, 2))
        cube1.add_aux_coord(broken_coordinate, data_dims=[0])
        cube1.attributes["STASH"] = "m01s01i001"

        cube2 = ants.tests.stock.geodetic((2, 2, 2))
        cube2.attributes["STASH"] = "m01s01i001"

        cube3 = ants.tests.stock.geodetic((2, 2, 2))
        cube3.add_aux_coord(broken_coordinate, data_dims=[0])
        cube3.attributes["STASH"] = "m01s01i001"

        my_cubes.append(cube1)
        my_cubes.append(cube2)
        my_cubes.append(cube3)

        msg = "Invalid values found in month_number coordinate."
        with self.assertRaisesRegex(RuntimeError, msg):
            _get_grid(my_cubes)


if __name__ == "__main__":
    ants.tests.main()

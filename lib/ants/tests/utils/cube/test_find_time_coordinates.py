# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import ants.tests
import ants.tests.stock as stock
import cf_units
import iris
import numpy as np
from ants.utils.cube import find_time_coordinates


class TestAll(ants.tests.TestCase):
    def setUp(self):
        time_units = cf_units.Unit(
            "days since 2000-01-01 00:00:00", calendar="gregorian"
        )
        time = iris.coords.DimCoord(
            np.arange(12), standard_name="time", units=time_units
        )
        cube = stock.geodetic((12, 4, 4), data=np.zeros((12, 4, 4)))
        cube.add_dim_coord(time, 0)
        self.cube = cube

    def test_correct_coordinate(self):
        result = find_time_coordinates(self.cube)
        self.assertEqual(self.cube.coord("time"), result[0])

    def test_coordinate_with_incorrect_units(self):
        incorrect_units = cf_units.Unit("kilometers")
        time_with_incorrect_units = iris.coords.DimCoord(
            np.arange(12), standard_name="time", units=incorrect_units
        )
        cube = stock.geodetic((12, 4, 4), data=np.zeros((12, 4, 4)))
        cube.add_dim_coord(time_with_incorrect_units, 0)
        msg = (
            "Coordinate has the standard name of 'time' but does "
            "not have the units of a time coordinate as per CF "
            "conventions: "
            r"\(time\)"
        )
        with self.assertRaisesRegex(ValueError, msg):
            find_time_coordinates(cube)

    def test_coordinate_with_incorrect_name(self):
        time_units = cf_units.Unit(
            "days since 2000-01-01 00:00:00", calendar="gregorian"
        )
        time_with_incorrect_name = iris.coords.DimCoord(
            np.arange(12), standard_name="distance_from_sun", units=time_units
        )
        cube = stock.geodetic((12, 4, 4), data=np.zeros((12, 4, 4)))
        cube.add_dim_coord(time_with_incorrect_name, 0)
        msg = (
            "Coordinate has the units of a time coordinate but "
            "does not have the standard name of 'time' as per "
            "CF conventions: "
            r"\(distance_from_sun\)"
        )
        with self.assertRaisesRegex(ValueError, msg):
            find_time_coordinates(cube)


if __name__ == "__main__":
    ants.tests.main()

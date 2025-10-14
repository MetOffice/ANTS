# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
from datetime import datetime

import ants.tests
import cf_units
import iris
import numpy as np
from ants.utils.coord import guess_bounds


class TestAll(ants.tests.TestCase):
    @staticmethod
    def latitude_coord(with_bounds=False):
        coord = iris.coords.AuxCoord([-90, 0, 90], standard_name="latitude")
        if with_bounds:
            coord.bounds = [[-90.0, -45.0], [-45.0, 45.0], [45.0, 90.0]]
        return coord

    def test_latitude_beyond(self):
        # Ensure that iris guess bounds is corrected so that we don't have
        # bounds beyond -90, 90
        coord = self.latitude_coord()
        guess_bounds(coord)

        target = [[-90.0, -45.0], [-45.0, 45.0], [45.0, 90.0]]
        self.assertArrayEqual(coord.bounds, target)

    def test_strict_keyword_true_existing_coord(self):
        # Ensure that guessing the bounds when there is existing bounds retains
        # the behaviour from the iris guess bounds.
        coord = self.latitude_coord(with_bounds=True)
        with self.assertRaisesRegex(ValueError, "Coord already has bounds"):
            guess_bounds(coord, strict=True)

    def test_strict_keyword_default(self):
        # Ensure that the default strict keyword is with value True.
        coord = self.latitude_coord(with_bounds=True)
        with self.assertRaisesRegex(ValueError, "Coord already has bounds"):
            guess_bounds(coord)

    def test_strict_keyword_false_existing_coord(self):
        # Ensure that when strict keyword is False, that no exception is
        # raised.
        coord = self.latitude_coord(with_bounds=True)
        guess_bounds(coord, strict=False)

    def test_strict_keyword_true_single_coord_points(self):
        # Ensure that an exception is raised when strict if False and there is
        # only one coordinate point.
        coord = self.latitude_coord(with_bounds=False)[0]
        msg = "Cannot guess bounds for a coordinate of length 1."
        with self.assertRaisesRegex(ValueError, msg):
            guess_bounds(coord, strict=True)

    def test_strict_keyword_false_single_coord_points(self):
        # Ensure that we ignore the case when the coordinate has only 1 point
        # when the strict keyword is False.
        coord = self.latitude_coord(with_bounds=False)[0]
        guess_bounds(coord, strict=False)

    def test_coord_metadata(self):
        # Ensure that coordinate remains unchanged including metadata
        coord = self.latitude_coord(with_bounds=False)
        tcoord = coord.copy()
        guess_bounds(coord, strict=True)
        coord.bounds = None
        self.assertEqual(coord, tcoord)


class Test_time_coordinate(ants.tests.TestCase):
    def test_360_day(self):
        coord = iris.coords.AuxCoord(
            points=np.arange(15, 346, 30),
            units=cf_units.Unit("days since epoch", calendar="360_day"),
            standard_name="time",
        )
        expected = np.array(
            [
                [0.0, 30.0],
                [30.0, 60.0],
                [60.0, 90.0],
                [90.0, 120.0],
                [120.0, 150.0],
                [150.0, 180.0],
                [180.0, 210.0],
                [210.0, 240.0],
                [240.0, 270.0],
                [270.0, 300.0],
                [300.0, 330.0],
                [330.0, 360.0],
            ]
        )

        ants.utils.coord.guess_bounds(coord)
        self.assertArrayEqual(expected, coord.bounds)

    def test_gregorian(self):
        units = cf_units.Unit("days since epoch", calendar="gregorian")
        expected = [
            [datetime(1990, 1, 1), datetime(1990, 2, 1)],
            [datetime(1990, 2, 1), datetime(1990, 3, 1)],
            [datetime(1990, 3, 1), datetime(1990, 4, 1)],
        ]
        expected = units.date2num(expected)
        points = expected.mean(axis=1)
        coord = iris.coords.AuxCoord(points=points, units=units, standard_name="time")
        ants.utils.coord.guess_bounds(coord)
        self.assertArrayEqual(expected, coord.bounds)

    def test_unsupported1(self):
        coord = iris.coords.AuxCoord(
            points=[15, 30, 41],
            units=cf_units.Unit("days since epoch", calendar="360_day"),
            standard_name="time",
        )
        with self.assertRaisesRegex(ValueError, "Unsupported time"):
            ants.utils.coord.guess_bounds(coord)

    def test_unsupported2(self):
        points = [-17011800, -17003880]
        unit = cf_units.Unit("hours since 1970-01-01 00:00:00", calendar="360_day")
        coord = iris.coords.AuxCoord(points, standard_name="time", units=unit)
        with self.assertRaisesRegex(ValueError, "Unsupported time"):
            ants.utils.coord.guess_bounds(coord)


if __name__ == "__main__":
    ants.tests.main()

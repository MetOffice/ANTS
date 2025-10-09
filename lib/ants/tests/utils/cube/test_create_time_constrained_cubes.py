# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
import numpy as np
from ants.exceptions import (
    DateRangeNotFullyAvailableException,
    TimeConstraintOutOfBoundsException,
)
from ants.utils.cube import (
    _get_cube_end_year,
    _get_cube_start_year,
    create_time_constrained_cubes,
)


class TestTimeConstraintErrors(ants.tests.TestCase):
    def setUp(self):
        self.test_cubes = []
        test_cube = ants.tests.stock.simple_3d_time_varying()
        time_coord = test_cube.coord(axis="t")
        time_coord.bounds = np.array([[0, 365], [365, 730], [730, 1096]]) * 24
        time_coord.points = np.mean(time_coord.bounds, axis=1)
        self.test_cubes.append(test_cube)
        return self.test_cubes

    def test_out_of_range_constraint(self):
        # test out-of-bounds request returns the correct error
        begin_time = 1990
        end_time = 1992
        with self.assertRaises(TimeConstraintOutOfBoundsException):
            create_time_constrained_cubes(self.test_cubes, begin_time, end_time)

    def test_overlapping_range_constraint(self):
        # test a request that asks for some but not all the
        # available data returns the correct error
        begin_time = 1971
        end_time = 1975
        with self.assertRaises(DateRangeNotFullyAvailableException):
            create_time_constrained_cubes(self.test_cubes, begin_time, end_time)

    def test_under_lapping_range_constraint(self):
        # test a request that asks for some but not all the
        # available data returns the correct error
        begin_time = 1961
        end_time = 1971
        with self.assertRaises(DateRangeNotFullyAvailableException):
            create_time_constrained_cubes(self.test_cubes, begin_time, end_time)

    def test_wrap_around_range_constraint(self):
        begin_time = 1961
        end_time = 1981
        with self.assertRaises(DateRangeNotFullyAvailableException):
            create_time_constrained_cubes(self.test_cubes, begin_time, end_time)


class TestTimeConstraints(ants.tests.TestCase):
    def setUp(self):
        self.test_cubes = []
        test_cube = ants.tests.stock.simple_3d_time_varying(times=6)
        time_coord = test_cube.coord(axis="t")
        time_coord.bounds = (
            np.array(
                [
                    [0, 365],
                    [365, 730],
                    [730, 1096],
                    [1096, 1461],
                    [1461, 1826],
                    [1826, 2191],
                ]
            )
            * 24
        )
        time_coord.points = np.mean(time_coord.bounds, axis=1)
        self.test_cubes.append(test_cube)
        return self.test_cubes

    def test_same_end_time_constraint(self):
        # test getting a single year slice - this tests that a single time is returned
        # by testing for a tuple of (5, 6) rather than None. A time value of
        # 1 is not returned, it is implied by the fact that the relevant single items
        # exist.
        begin_time = 1971
        end_time = 1971
        results = create_time_constrained_cubes(self.test_cubes, begin_time, end_time)
        expected = (5, 6)
        for result in results:
            assert expected == result.shape

    def test_create_time_constrained_cubes(self):
        # test for a full dataset constraint
        begin_time = 1970
        end_time = 1975
        results = create_time_constrained_cubes(self.test_cubes, begin_time, end_time)
        for result in results:
            shape = result.shape[0]
            assert shape == 6

    def test_create_subset_of_time_constrained_cubes(self):
        # test for a subset of the available dataset
        begin_time = 1972
        end_time = 1974
        results = create_time_constrained_cubes(self.test_cubes, begin_time, end_time)
        for result in results:
            shape = result.shape[0]
            assert shape == 3

    def test_accepts_cube(self):
        cube = self.test_cubes[0]
        begin_time = 1970
        end_time = 1972
        self.assertIsNotNone(create_time_constrained_cubes(cube, begin_time, end_time))


class TestLimits(ants.tests.TestCase):
    def setUp(self):
        points = [182.5, 547.5, 912.5, 1278.0]
        bounds = [[0, 365], [365, 730], [730, 1095], [1095, 1461]]
        units = "days since 1985-01-01"
        tc = iris.coords.DimCoord(
            points=points, bounds=bounds, units=units, standard_name="time"
        )
        self.cube = iris.cube.Cube([1, 2, 3, 4])
        self.cube.add_dim_coord(tc, 0)

    def test__get_cube_start_year(self):
        expected = 1985
        actual = _get_cube_start_year(self.cube)
        self.assertEqual(actual, expected)

    def test__get_cube_end_year(self):
        expected = 1989
        actual = _get_cube_end_year(self.cube)
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    ants.tests.main()

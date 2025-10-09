# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import cf_units
import iris
import numpy as np
from ants.fileformats.ancil.time_headers import set_headers_time_information


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.headers = {"fixed_length_header": {}, "integer_constants": {}}
        self.daily_time_series = {
            "fixed_length_header": {
                "time_type": 1,
                "t1_year": 1970,
                "t1_month": 1,
                "t1_day": 1,
                "t1_hour": 12,
                "t1_minute": 0,
                "t1_second": 0,
                "t2_year": 1970,
                "t2_month": 2,
                "t2_day": 5,
                "t2_hour": 12,
                "t2_minute": 0,
                "t2_second": 0,
                "t3_year": 0,
                "t3_month": 0,
                "t3_day": 1,
                "t3_hour": 0,
                "t3_minute": 0,
                "t3_second": 0,
            },
            "integer_constants": {"num_times": 36},
        }
        self.monthly_periodic = {
            "fixed_length_header": {
                "time_type": 2,
                "t1_year": 1970,
                "t1_month": 1,
                "t1_day": 16,
                "t1_hour": 12,
                "t1_minute": 0,
                "t1_second": 0,
                "t2_year": 1970,
                "t2_month": 12,
                "t2_day": 16,
                "t2_hour": 12,
                "t2_minute": 0,
                "t2_second": 0,
                "t3_year": 0,
                "t3_month": 1,
                "t3_day": 0,
                "t3_hour": 0,
                "t3_minute": 0,
                "t3_second": 0,
            },
            "integer_constants": {"num_times": 12},
        }

    def test_single_time(self):
        expected = {
            "fixed_length_header": {"time_type": 0},
            "integer_constants": {"num_times": 1},
        }
        cube = ants.tests.stock.geodetic((1, 2, 2))
        time_unit = cf_units.Unit("days since epoch", calendar="gregorian")
        time_coordinate = iris.coords.DimCoord(
            [0], standard_name="time", units=time_unit
        )
        cube.add_dim_coord(time_coordinate, 0)
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    def test_exception_for_invalid_calendar_writing(self):
        cube = ants.tests.stock.geodetic((366, 2, 2))
        time_unit = cf_units.Unit("days since epoch", calendar="366_day")
        bounds = np.array([np.arange(0, 366), np.arange(1, 367)]).T
        time_coordinate = iris.coords.DimCoord(
            np.arange(366) + 0.5, bounds=bounds, standard_name="time", units=time_unit
        )
        cube.add_dim_coord(time_coordinate, 0)
        with self.assertRaisesRegex(ValueError, "366_day is not a suitable"):
            set_headers_time_information(cube, self.headers)

    def test_timeseries_without_calendar_writing(self):
        expected = self.monthly_periodic
        expected["fixed_length_header"]["time_type"] = 1
        expected["fixed_length_header"]["t2_hour"] = 0
        expected["fixed_length_header"]["t2_month"] = 11
        expected["integer_constants"]["num_times"] = 11
        bounds = np.array(
            [
                [0.0, 31.0],
                [31.0, 59.0],
                [59.0, 90.0],
                [90.0, 120.0],
                [120.0, 151.0],
                [151.0, 181.0],
                [181.0, 212.0],
                [212.0, 243.0],
                [243.0, 273.0],
                [273.0, 304.0],
                [304.0, 334.0],
            ]
        )
        cube = self._build_cube(bounds, "gregorian")
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    def test_timeseries_with_gregorian_calendar_writing(self):
        expected = self.daily_time_series
        expected["fixed_length_header"]["calendar"] = 1
        bounds = np.array([np.arange(0, 36), np.arange(1, 37)]).T
        cube = self._build_cube(bounds, "gregorian")
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    def test_timeseries_with_360_calendar_writing(self):
        expected = self.daily_time_series
        expected["fixed_length_header"]["calendar"] = 2
        # 30 day January => 36th day is 6th Feb, not 5th:
        expected["fixed_length_header"]["t2_day"] = 6
        bounds = np.array([np.arange(0, 36), np.arange(1, 37)]).T
        cube = self._build_cube(bounds, "360_day")
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    def test_timeseries_with_365_calendar_writing(self):
        expected = self.daily_time_series
        expected["fixed_length_header"]["calendar"] = 3
        bounds = np.array([np.arange(0, 36), np.arange(1, 37)]).T
        cube = self._build_cube(bounds, "365_day")
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    def test_periodic_without_calendar_writing(self):
        expected = self.monthly_periodic
        bounds = np.array(
            [
                [0.0, 31.0],
                [31.0, 59.0],
                [59.0, 90.0],
                [90.0, 120.0],
                [120.0, 151.0],
                [151.0, 181.0],
                [181.0, 212.0],
                [212.0, 243.0],
                [243.0, 273.0],
                [273.0, 304.0],
                [304.0, 334.0],
                [334.0, 365.0],
            ]
        )
        cube = self._build_cube(bounds, "gregorian")
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    def test_periodic_with_gregorian_calendar_writing(self):
        expected = self.monthly_periodic
        expected["fixed_length_header"]["calendar"] = 1
        expected["fixed_length_header"]["t1_day"] = 1
        expected["fixed_length_header"]["t2_day"] = 31
        expected["fixed_length_header"]["t3_day"] = 1
        expected["fixed_length_header"]["t3_month"] = 0
        expected["integer_constants"]["num_times"] = 365
        bounds = np.array([np.arange(0, 365), np.arange(1, 366)]).T
        cube = self._build_cube(bounds, "gregorian")
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    def test_periodic_with_360_calendar_writing(self):
        expected = self.monthly_periodic
        expected["fixed_length_header"]["calendar"] = 2
        expected["fixed_length_header"]["t1_day"] = 1
        expected["fixed_length_header"]["t2_day"] = 30
        expected["fixed_length_header"]["t3_day"] = 1
        expected["fixed_length_header"]["t3_month"] = 0
        expected["integer_constants"]["num_times"] = 360
        bounds = np.array([np.arange(0, 360), np.arange(1, 361)]).T
        cube = self._build_cube(bounds, "360_day")
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    def test_periodic_with_365_calendar_writing(self):
        expected = self.monthly_periodic
        expected["fixed_length_header"]["calendar"] = 3
        expected["fixed_length_header"]["t1_day"] = 1
        expected["fixed_length_header"]["t2_day"] = 31
        expected["fixed_length_header"]["t3_day"] = 1
        expected["fixed_length_header"]["t3_month"] = 0
        expected["integer_constants"]["num_times"] = 365
        bounds = np.array([np.arange(0, 365), np.arange(1, 366)]).T
        cube = self._build_cube(bounds, "365_day")
        set_headers_time_information(cube, self.headers)
        self._assert_expected_headers(expected)

    @classmethod
    def _build_cube(cls, time_bounds, calendar):
        time_unit = cf_units.Unit("days since epoch", calendar=calendar)
        time_points = [start + (end - start) / 2.0 for (start, end) in time_bounds]
        time_coordinate = iris.coords.DimCoord(
            points=time_points,
            bounds=time_bounds,
            standard_name="time",
            units=time_unit,
        )
        cube = ants.tests.stock.geodetic((len(time_coordinate.points), 2, 2))
        cube.add_dim_coord(time_coordinate, 0)
        return cube

    def _assert_expected_headers(self, actual):
        self.assertEqual(
            sorted(actual.keys()), ["fixed_length_header", "integer_constants"]
        )
        self.assertEqual(
            self.headers["fixed_length_header"], actual["fixed_length_header"]
        )
        self.assertEqual(self.headers["integer_constants"], actual["integer_constants"])


if __name__ == "__main__":
    ants.tests.main()

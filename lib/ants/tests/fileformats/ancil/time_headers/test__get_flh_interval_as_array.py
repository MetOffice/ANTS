# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import cf_units
import iris
import numpy as np
from ants.fileformats.ancil.time_headers import _get_flh_interval_as_array


class TestGetFlhIntervalAsArray(ants.tests.TestCase):
    def setUp(self):
        self.time_unit = cf_units.Unit(
            "days since 0001-01-01 00:00:00", calendar="gregorian"
        )
        self.tc = iris.coords.DimCoord(
            np.array(
                [
                    15.5,
                    45.0,
                    74.5,
                    105.0,
                    135.5,
                    166.0,
                    196.5,
                    227.5,
                    258.0,
                    288.5,
                    319.0,
                    349.5,
                ]
            ),
            bounds=np.array(
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
            ),
            standard_name="time",
            units=self.time_unit,
        )

    def test_daily_interval(self):
        expected = np.array([0, 0, 1, 0, 0, 0])
        tc = iris.coords.DimCoord(
            np.array([40907.5, 40908.5, 40909.5]),
            bounds=np.array(
                [[40907.0, 40908.0], [40908.0, 40909.0], [40909.0, 40910.0]]
            ),
            standard_name="time",
            units=cf_units.Unit("days since 1850-1-1 0:0:0", calendar="gregorian"),
        )
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_daily_interval_with_rollover(self):
        expected = np.array([0, 0, 1, 0, 0, 0])
        tc = iris.coords.DimCoord(
            np.array([364.5, 365.5, 366.5]),
            bounds=np.array([[364.0, 365.0], [365.0, 366.0], [366.0, 367.0]]),
            standard_name="time",
            units=self.time_unit,
        )
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_daily_interval_as_hours_since(self):
        expected = np.array([0, 0, 1, 0, 0, 0])
        tc = iris.coords.DimCoord(
            np.array([36, 60, 84]),
            bounds=np.array([[24.0, 48.0], [48.0, 72.0], [72.0, 96.0]]),
            standard_name="time",
            units=cf_units.Unit(
                "hours since 0001-01-01 00:00:00", calendar="gregorian"
            ),
        )
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_daily_interval_360_day_calendar(self):
        expected = np.array([0, 0, 1, 0, 0, 0])
        tc = iris.coords.DimCoord(
            np.array([358.5, 359.5, 360.5]),
            bounds=np.array([[358.0, 359.0], [359.0, 360.0], [360.0, 361.0]]),
            standard_name="time",
            units=cf_units.Unit("days since 0001-01-01 00:00:00", calendar="360_day"),
        )
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_multiple_daily_interval(self):
        expected = np.array([0, 0, 2, 0, 0, 0])
        tc = iris.coords.DimCoord(
            np.array([1.0, 3.0]),
            bounds=np.array([[0.0, 2.0], [2.0, 4.0]]),
            standard_name="time",
            units=self.time_unit,
        )
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_noncontiguous_daily_interval(self):
        tc = iris.coords.DimCoord(
            np.array([1.5, 4.5]),
            bounds=np.array([[1.0, 2.0], [4.0, 5.0]]),
            standard_name="time",
            units=self.time_unit,
        )
        with self.assertRaisesRegex(
            ValueError, "F03 ancillaries with time bounds are required "
        ):
            _get_flh_interval_as_array(tc)

    def test_hourly_interval(self):
        expected = np.array([0, 0, 0, 1, 0, 0])
        tc = iris.coords.DimCoord(
            np.array([0.5, 1.5]) / 24.0,
            bounds=np.array([[0.0, 1.0], [1.0, 2.0]]) / 24.0,
            standard_name="time",
            units=self.time_unit,
        )
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_multiple_hourly_interval(self):
        expected = np.array([0, 0, 0, 12, 0, 0])
        tc = iris.coords.DimCoord(
            np.array([0.5, 1.0]),
            bounds=np.array([[0.25, 0.75], [0.75, 1.25]]),
            standard_name="time",
            units=self.time_unit,
        )
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_monthly_interval(self):
        expected = np.array([0, 1, 0, 0, 0, 0])
        actual = _get_flh_interval_as_array(self.tc)
        self.assertArrayEqual(expected, actual)

    def test_monthly_interval_with_rollover(self):
        # Ensures that we handle the rollover for time series longer than 2
        # years (i.e. multiple rollovers, rather than just one).
        points = np.array(
            [
                15.5,
                45.0,
                74.5,
                105.0,
                135.5,
                166.0,
                196.5,
                227.5,
                258.0,
                288.5,
                319.0,
                349.5,
                380.5,
                410.0,
                439.5,
                470.0,
                500.5,
                531.0,
                561.5,
                592.5,
                623.0,
                653.5,
                684.0,
                714.5,
                745.5,
                775.0,
                804.5,
                835.0,
                865.5,
                896.0,
                926.5,
                957.5,
                988.0,
                1018.5,
                1049.0,
                1079.5,
            ]
        )
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
                [365.0, 396.0],
                [396.0, 424.0],
                [424.0, 455.0],
                [455.0, 485.0],
                [485.0, 516.0],
                [516.0, 546.0],
                [546.0, 577.0],
                [577.0, 608.0],
                [608.0, 638.0],
                [638.0, 669.0],
                [669.0, 699.0],
                [699.0, 730.0],
                [730.0, 761.0],
                [761.0, 789.0],
                [789.0, 820.0],
                [820.0, 850.0],
                [850.0, 881.0],
                [881.0, 911.0],
                [911.0, 942.0],
                [942.0, 973.0],
                [973.0, 1003.0],
                [1003.0, 1034.0],
                [1034.0, 1064.0],
                [1064.0, 1095.0],
            ]
        )
        tc = iris.coords.DimCoord(
            points, bounds=bounds, standard_name="time", units=self.time_unit
        )
        expected = np.array([0, 1, 0, 0, 0, 0])
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_multiple_monthly_interval(self):
        tc = self.tc[::2]
        with self.assertRaises(ValueError):
            _get_flh_interval_as_array(tc)

    def test_monthly_interval_without_bounds(self):
        tc = self.tc
        tc.bounds = None
        actual = _get_flh_interval_as_array(tc)
        expected = np.array([0, 1, 0, 0, 0, 0])
        self.assertArrayEqual(expected, actual)

    def test_annual_interval(self):
        expected = np.array([1, 0, 0, 0, 0, 0])
        tc = iris.coords.DimCoord(
            np.array([182.5, 547.5]),
            bounds=np.array([[0.0, 365.0], [365.0, 730.0]]),
            standard_name="time",
            units=self.time_unit,
        )
        actual = _get_flh_interval_as_array(tc)
        self.assertArrayEqual(expected, actual)

    def test_no_interval(self):
        tc = iris.coords.DimCoord(
            np.array([15.5, 145.0]),
            bounds=np.array([[0.0, 30.0], [134.0, 164.0]]),
            standard_name="time",
            units=self.time_unit,
        )
        with self.assertRaises(ValueError):
            _get_flh_interval_as_array(tc)


if __name__ == "__main__":
    ants.tests.main()

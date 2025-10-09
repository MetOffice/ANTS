# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import cf_units
import iris
import numpy as np
from ants.fileformats.ancil.time_headers import is_periodic


class TestIsPeriodic(ants.tests.TestCase):
    def _set_times(self, calendar, bounds):
        """
        Set up time coordinates for calendar using bounds.
        """
        self.time_unit = cf_units.Unit(
            "days since 0001-01-01 00:00:00", calendar=calendar
        )
        self.tc = iris.coords.DimCoord(
            np.mean(bounds, axis=1),
            bounds=np.array(bounds),
            standard_name="time",
            units=self.time_unit,
        )

    def test_gregorian_periodic(self):
        # As used in UM output with bounds from midnight on the 1st of the
        # month to midnight on the 1st of the next month - i.e. midnight for
        # the first of each month is specified twice.  Only include Jan and
        # Dec in this test though
        bounds = np.array([[0.0, 31.0], [334.0, 365]])
        self._set_times("gregorian", bounds)
        self.assertTrue(is_periodic(self.tc))

    def test_gregorian_non_periodic(self):
        # Similar to UM output, but with the upper bound brought forward to
        # 0001-12-31 23:58:51.
        bounds = np.array([[0.0, 31.0], [334.0, 364.992]])
        self._set_times("gregorian", bounds)
        self.assertFalse(is_periodic(self.tc))

    def test_365_periodic(self):
        bounds = np.array([[0.0, 31.0], [334.0, 365]])
        self._set_times("365_day", bounds)
        self.assertTrue(is_periodic(self.tc))

    def test_365_non_periodic(self):
        bounds = np.array([[0.0, 31.0], [334.0, 364.992]])
        self._set_times("365_day", bounds)
        self.assertFalse(is_periodic(self.tc))

    def test_360_periodic(self):
        bounds = np.array([[0.0, 31.0], [330.0, 360]])
        self._set_times("360_day", bounds)
        self.assertTrue(is_periodic(self.tc))

    def test_360_non_periodic(self):
        bounds = np.array([[0.0, 31.0], [330.0, 359.9992]])
        self._set_times("360_day", bounds)
        self.assertFalse(is_periodic(self.tc))

    def test_single_point_non_periodic(self):
        bounds = np.array([[0.0, 360]])
        self._set_times("360_day", bounds)
        self.assertFalse(is_periodic(self.tc))

    def test_exception_for_non_time(self):
        not_time = iris.coords.DimCoord(
            [0.0, 1.0],
            var_name="foo",
        )
        with self.assertRaisesRegex(
            ValueError,
            "Can only test time coordinates for periodicity.  foo",
        ):
            is_periodic(not_time)


if __name__ == "__main__":
    ants.tests.main()

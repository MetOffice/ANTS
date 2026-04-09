# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
from ants.utils.cube import update_history


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.cube = iris.cube.Cube(0)
        self.cube2 = iris.cube.Cube(0)
        self.cubelist = iris.cube.CubeList([self.cube, self.cube2])
        self.isodate_pattern = r"\d{4,4}-\d{2,2}-\d{2,2}T\d{2,2}:\d{2,2}:" r"\d{2,2}: "

    def test_no_existing_history(self):
        # No existing history attribute on the cube
        msg = "some test string"
        pattern = self.isodate_pattern + msg
        update_history(self.cube, msg)
        self.assertRegex(self.cube.attributes["history"], pattern)

    def test_existing_history(self):
        # Existing history attribute on the cube
        self.cube.attributes["history"] = "some existing string"

        msg = "some test string"
        pattern = self.isodate_pattern + "{}\n{}".format(
            msg, self.cube.attributes["history"]
        )
        update_history(self.cube, msg)
        self.assertRegex(self.cube.attributes["history"], pattern)

    def test_not_adding_date(self):
        # Use argument to stop the date being prepended to the history attribute.
        msg = "some test string"
        pattern = msg
        update_history(self.cube, msg, add_date=False)
        self.assertRegex(self.cube.attributes["history"], pattern)

    def test_update_cubelist(self):
        # Pass a cubelist to all be updated
        msg = "some test string"
        pattern = self.isodate_pattern + msg
        update_history(self.cubelist, msg)
        for cube in self.cubelist:
            self.assertRegex(cube.attributes["history"], pattern)

    def test_deprecation_warning(self):
        # Use date argument to specify a date. A warning
        # should be raised as this argument is deprecated.
        date = "2000-01-01"
        msg = "some test string"
        error_msg = (
            "The date option in ants.utils.cube.update_history has been deprecated."
            "If add_date is true then the current date and time will be used. "
            "Cubelists can be passed directly to update_history to be updated with an "
            "identical history attribute."
        )
        with self.assertRaisesRegex(FutureWarning, error_msg):
            update_history(self.cube, msg, date=date)

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

    def test_not_adding_date_and_providing_date(self):
        # Use both the argument to stop the date being prepended to the history
        # attribute and the argument to specify the date to add. A warning
        # should be raised as these two arguments are incompatible.
        date = "2000-01-01"
        msg = "some test string"
        error_msg = (
            "Incompatible arguments provided: the date argument is set to "
            f"{date} and the add_date argument is set to False."
        )
        with self.assertRaisesRegex(RuntimeError, error_msg):
            update_history(self.cube, msg, date=date, add_date=False)


if __name__ == "__main__":
    ants.tests.main()

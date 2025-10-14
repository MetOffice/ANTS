# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
from ants.config import formatted_time
from ants.exceptions import TimeConstraintFormatException


class TestConfigForBeingAndEndFormatting(ants.tests.TestCase):
    def test_formatted_time(self):
        test_items = ["1999", "2002", "2004"]
        for item in test_items:
            result = formatted_time(item)
            self.assertIsInstance(result, int)

    def test_dodgy_strings(self):
        test_items = ["76, 7, 10", "1982, 04", "2000, 01, 01", "some time"]
        for item in test_items:
            with self.assertRaises(TimeConstraintFormatException):
                formatted_time(item)


if __name__ == "__main__":
    ants.tests.main()

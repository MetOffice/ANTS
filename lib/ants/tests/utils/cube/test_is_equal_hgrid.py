# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
from ants.utils.cube import is_equal_hgrid


class TestRegular(ants.tests.TestCase):
    def test_equal(self):
        cube1 = ants.tests.stock.geodetic((1, 1))
        cube2 = ants.tests.stock.geodetic((1, 1))
        self.assertTrue(is_equal_hgrid([cube1, cube2]))

    def test_not_equal(self):
        cube1 = ants.tests.stock.geodetic((1, 1))
        cube2 = ants.tests.stock.geodetic((1, 1), ylim=(-80, 80))
        self.assertFalse(is_equal_hgrid([cube1, cube2]))


class TestErrorsRaised(ants.tests.TestCase):
    def test_error_raised_for_reference(self):
        """Tests that the first cube in the cubelist that is used as a reference
        for the others, will raise a ValueError if it is ugrid."""
        cube1 = ants.tests.stock.geodetic((1, 1))
        cube1.attributes["Conventions"] = "UGRID"
        cube2 = ants.tests.stock.geodetic((1, 1))
        with self.assertRaisesRegex(
            ValueError, "ANTS doesn't support ugrid data. Please use UG-ANTS instead."
        ):
            is_equal_hgrid([cube1, cube2])

    def test_error_raised_for_cubes(self):
        """Tests that a cube that is not used as a reference for the other cubes
        in the list, will raise a ValueError if it is ugrid."""
        cube1 = ants.tests.stock.geodetic((1, 1))
        cube2 = ants.tests.stock.geodetic((1, 1))
        cube2.attributes["Conventions"] = "UGRID"
        with self.assertRaisesRegex(
            ValueError, "ANTS doesn't support ugrid data. Please use UG-ANTS instead."
        ):
            is_equal_hgrid([cube1, cube2])

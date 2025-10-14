# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import ants.tests
from ants.utils.cube import is_global


class TestAll(ants.tests.TestCase):
    def test_x_global_y_limited(self):
        cube = ants.tests.stock.geodetic((1, 1), ylim=(-80, 80))
        result = is_global(cube)
        target = False
        self.assertEqual(result, target)

    def test_x_limited_x_global(self):
        cube = ants.tests.stock.geodetic((1, 1), xlim=(-80, 80))
        result = is_global(cube)
        target = False
        self.assertEqual(result, target)

    def test_x_limited_y_limited(self):
        cube = ants.tests.stock.geodetic((1, 1), ylim=(-80, 80), xlim=(-80, 80))
        result = is_global(cube)
        target = False
        self.assertEqual(result, target)

    def test_non_modulus(self):
        cube = ants.tests.stock.osgb((1, 1))
        result = is_global(cube)
        target = False
        self.assertEqual(result, target)

    def test_global_true(self):
        cube = ants.tests.stock.geodetic((1, 1))
        result = is_global(cube)
        target = True
        self.assertEqual(result, target)


if __name__ == "__main__":
    ants.tests.main()

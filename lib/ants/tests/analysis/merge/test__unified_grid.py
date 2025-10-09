# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
from unittest import mock

import ants.tests
from ants.analysis._merge import _unified_grid


class TestGridUnification(ants.tests.TestCase):
    def test_identical_grid_coords_unchanged(self):
        cubeshape = (2, 2)
        cube1 = ants.tests.stock.geodetic(cubeshape)
        cube2 = ants.tests.stock.geodetic(cubeshape)
        unified = _unified_grid(cube1, cube2)
        self.assertEqual(unified.coord("latitude"), cube1.coord("latitude"))
        self.assertEqual(unified.coord("longitude"), cube1.coord("longitude"))

    def test_tolerance_coords_not_rounded(self):
        cubeshape = (2, 2)
        cube1 = ants.tests.stock.geodetic(cubeshape)
        offsetme = cube1.coord("latitude").points.copy()
        cube1.coord("latitude").points = offsetme + 1e-2
        cube2 = cube1.copy()

        with mock.patch("ants.config.TOLERANCE", 1e-1):
            unified = _unified_grid(cube1, cube2)

        self.assertEqual(unified.coord("latitude"), cube1.coord("latitude"))
        self.assertEqual(unified.coord("longitude"), cube1.coord("longitude"))

    def test_tolerance_offset_coords_rounded(self):
        cubeshape = (2, 2)
        cube1 = ants.tests.stock.geodetic(cubeshape)
        cube2 = ants.tests.stock.geodetic(cubeshape)
        offsetme = cube2.coord("latitude").points.copy()
        cube2.coord("latitude").points = offsetme + 1e-2

        with mock.patch("ants.config.TOLERANCE", 1e-1):
            unified = _unified_grid(cube1, cube2)

        self.assertEqual(unified.coord("latitude"), cube1.coord("latitude"))
        self.assertEqual(unified.coord("longitude"), cube1.coord("longitude"))

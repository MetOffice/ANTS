# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
from ants.fileformats.namelist import apply_um_conventions


class TestRegionalRotation(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic((1, 1))

    def assert_coord(self, x_coord, y_coord):
        self.assertEqual(self.cube.coord(axis="x"), x_coord)
        self.assertEqual(self.cube.coord(axis="y"), y_coord)

    def test_enforce_sn_direction(self):
        self.cube = ants.tests.stock.geodetic((2, 2))
        x = self.cube.coord(axis="x")
        y = self.cube.coord(axis="y")

        tar_x = x.copy()
        tar_y = y.copy()
        y_points = y.points.copy()[::-1]
        y_bounds = y.bounds.copy()[::-1, ::-1]
        y.points = y_points
        y.bounds = y_bounds
        apply_um_conventions(self.cube)
        self.assert_coord(tar_x, tar_y)


if __name__ == "__main__":
    ants.tests.main()

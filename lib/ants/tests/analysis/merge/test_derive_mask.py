# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.analysis._merge import derive_mask
from iris.coord_systems import GeogCS, RotatedGeogCS
from shapely.geometry import Polygon


class TestAll(ants.tests.TestCase):
    def setUp(self):
        poly = np.array(
            [
                [362.594, -1.32876],
                [361.407, -2.11520],
                [358.150, -2.5500],
                [357.744, -2.28679],
                [358.417, 1.03058],
                [359.232, 1.50245],
                [359.103, 2.07441],
                [358.488, 2.00291],
                [358.030, 2.84656],
                [357.472, 3.43282],
                [356.986, 4.34795],
                [357.286, 5.96374],
                [359.404, 8.6],
                [361.278, 8.6],
                [362.766, 0.315629],
                [362.666, -1.18577],
            ]
        )
        poly[:, 0] -= 360
        self.poly = Polygon(poly)

    def test_same_crs(self):
        geom_crs = RotatedGeogCS(37.5, 177.5, ellipsoid=GeogCS(6371229.0))
        source = ants.tests.stock.geodetic((6, 6), xlim=(-5, 5), ylim=(-5, 10))
        x, y = ants.utils.cube.horizontal_grid(source)
        x.coord_system = y.coord_system = geom_crs
        mask = derive_mask(source, [self.poly])

        target = np.array(
            [
                [False, True, True, False, False, False],
                [False, True, True, True, True, False],
                [False, True, True, True, True, False],
                [False, True, True, True, True, False],
                [False, True, True, True, True, False],
                [False, False, True, True, False, False],
            ]
        )
        self.assertArrayEqual(mask, target)

    def test_diff_crs(self):
        source = ants.tests.stock.geodetic((6, 6), xlim=(-10, 10), ylim=(50, 60))
        geom_crs = RotatedGeogCS(37.5, 177.5, ellipsoid=GeogCS(6371229.0))
        mask = derive_mask(source, [self.poly], geom_crs)

        target = np.array(
            [
                [False, True, True, True, False, False],
                [False, True, True, True, False, False],
                [False, True, True, True, False, False],
                [True, True, True, True, False, False],
                [True, True, True, True, False, False],
                [True, True, True, True, False, False],
            ]
        )
        self.assertArrayEqual(mask, target)


if __name__ == "__main__":
    ants.tests.main()

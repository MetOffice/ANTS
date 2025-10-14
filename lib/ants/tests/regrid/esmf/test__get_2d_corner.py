# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
import numpy as np
from ants.regrid.esmf import _LatLonExtractor


class TestAll(ants.tests.TestCase):
    def setUp(self):
        # 2D longitudes for 1 degree square cells from 0 to 2 degrees lon and
        # 0 to 2 degrees lat.  Bound starting position is bottom left.
        self.points = np.array([[0.5, 1.5], [0.5, 1.5]])
        self.bl_bounds_ccw = np.array(
            [[[0, 1, 1, 0], [1, 2, 2, 1]], [[0, 1, 1, 0], [1, 2, 2, 1]]]
        )
        self.extractor = _LatLonExtractor(ants.tests.stock.geodetic((2, 2)))
        # See comment in _LatLonExtractor._get_2d_corner to understand
        # expected array.
        self.expected = np.array([[0, 1, 2], [0, 1, 2], [0, 1, 2]])

        bounds = self.bl_bounds_ccw.copy()
        bounds[..., 0] = self.bl_bounds_ccw[..., 0]
        bounds[..., 3] = self.bl_bounds_ccw[..., 1]
        bounds[..., 2] = self.bl_bounds_ccw[..., 2]
        bounds[..., 1] = self.bl_bounds_ccw[..., 3]
        self.bl_bounds_cw = bounds

    def assert_corners(self, bounds, clockwise):
        coord = iris.coords.AuxCoord(self.points, bounds=bounds)
        actual = self.extractor._get_2d_corner(coord, clockwise)
        self.assertArrayEqual(self.expected, actual)

    def test_bl_start_ccw(self):
        self.assert_corners(self.bl_bounds_ccw, False)

    def test_br_start_ccw(self):
        br_bounds = np.roll(self.bl_bounds_ccw, -1, axis=2)
        self.assert_corners(br_bounds, False)

    def test_tr_start_ccw(self):
        tr_bounds = np.roll(self.bl_bounds_ccw, -2, axis=2)
        self.assert_corners(tr_bounds, False)

    def test_tl_start_ccw(self):
        tl_bounds = np.roll(self.bl_bounds_ccw, -3, axis=2)
        self.assert_corners(tl_bounds, False)

    def test_bl_start_cw(self):
        self.assert_corners(self.bl_bounds_cw, True)

    def test_br_start_cw(self):
        br_bounds = np.roll(self.bl_bounds_cw, -1, axis=2)
        self.assert_corners(br_bounds, True)

    def test_tr_start_cw(self):
        tr_bounds = np.roll(self.bl_bounds_cw, -2, axis=2)
        self.assert_corners(tr_bounds, True)

    def test_tl_start_cw(self):
        tl_bounds = np.roll(self.bl_bounds_cw, -3, axis=2)
        self.assert_corners(tl_bounds, True)


if __name__ == "__main__":
    ants.tests.main()

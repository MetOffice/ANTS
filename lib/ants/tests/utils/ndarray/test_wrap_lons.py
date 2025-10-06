# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.utils.ndarray import wrap_lons


class TestAll(ants.tests.TestCase):
    def test_gt_base_plus_period(self):
        # Ensure we wrap points when > base+period
        points = np.array([0, 180, 361])
        tar = np.array([0, 180, 1])
        res = wrap_lons(points, 0, 360, endpoint=True)
        self.assertArrayEqual(res, tar)

    def test_base_plus_period(self):
        # Ensure we do not wrap points at base+period
        points = np.array([0, 180, 360])
        tar = points.copy()
        res = wrap_lons(points, 0, 360, endpoint=True)
        self.assertArrayEqual(res, tar)

    def test_base_plus_period_endpoint_false(self):
        # Ensure we wrap points at base+period
        points = np.array([0, 180, 360])
        tar = np.array([0, 180, 0])
        res = wrap_lons(points, 0, 360, endpoint=False)
        self.assertArrayEqual(res, tar)


if __name__ == "__main__":
    ants.tests.main()

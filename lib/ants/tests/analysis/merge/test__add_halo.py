# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.analysis._merge import _add_halo as add_halo


class TestAll(ants.tests.TestCase):
    def test_circular(self):
        cube = ants.tests.stock.geodetic((5, 5), with_bounds=True)
        res = add_halo(cube, fill_value=100, halo_width=[2, 1])

        tar = np.array(
            [
                [100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100],
                [4, 0, 1, 2, 3, 4, 0],
                [9, 5, 6, 7, 8, 9, 5],
                [14, 10, 11, 12, 13, 14, 10],
                [19, 15, 16, 17, 18, 19, 15],
                [24, 20, 21, 22, 23, 24, 20],
                [100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100],
            ]
        )
        self.assertArrayEqual(res, tar)

    def test_non_circular(self):
        cube = ants.tests.stock.geodetic((5, 5), with_bounds=True)
        cube.coord(axis="x").circular = False
        res = add_halo(cube, fill_value=100, halo_width=[2, 1])

        tar = np.array(
            [
                [100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100],
                [100, 0, 1, 2, 3, 4, 100],
                [100, 5, 6, 7, 8, 9, 100],
                [100, 10, 11, 12, 13, 14, 100],
                [100, 15, 16, 17, 18, 19, 100],
                [100, 20, 21, 22, 23, 24, 100],
                [100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100],
            ]
        )
        self.assertArrayEqual(res, tar)

    def test_circular_masked(self):
        data = np.ma.arange(36, fill_value=100).reshape(6, 6).astype("float")
        data[0:4] = np.ma.masked
        cube = ants.tests.stock.geodetic(data=data)
        res = add_halo(cube, fill_value=100, halo_width=[1, 1])

        tar = np.array(
            [
                [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
                [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
                [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
                [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
                [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
                [29.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 24.0],
                [35.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 30.0],
                [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
            ]
        )
        self.assertArrayEqual(res, tar)


if __name__ == "__main__":
    ants.tests.main()

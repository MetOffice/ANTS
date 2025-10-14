# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import ants.tests
import ants.tests.stock as stock
import cf_units
import iris
import numpy as np
from ants.utils.cube import set_month_mean_for_year


class TestAll(ants.tests.TestCase):
    def setUp(self):
        time = self.time_coord(np.arange(12))
        cube = stock.geodetic((12, 4, 4), data=np.zeros((12, 4, 4)))
        cube.add_dim_coord(time, 0)
        self.cube = cube

    @staticmethod
    def time_coord(points, bounds=None):
        coord = iris.coords.DimCoord(
            points,
            bounds=bounds,
            standard_name="time",
            units=cf_units.Unit("days since 2000-01-01 00:00:00", calendar="gregorian"),
        )
        return coord

    def assert_cube_climatology(self, cube):
        # Check cube cell methods.
        tar_cell_methods = [iris.coords.CellMethod("mean", coords="time")]
        for res_cell_method, tar_cell_method in zip(
            cube.cell_methods, tar_cell_methods
        ):
            self.assertEqual(res_cell_method, tar_cell_method)

        # Check time coordinate.
        target_pnts = [
            15.5,
            45.5,
            75.5,
            106.0,
            136.5,
            167.0,
            197.5,
            228.5,
            259.0,
            289.5,
            320.0,
            350.5,
        ]
        target_bnds = [
            [0.0, 31.0],
            [31.0, 60.0],
            [60.0, 91.0],
            [91.0, 121.0],
            [121.0, 152.0],
            [152.0, 182.0],
            [182.0, 213.0],
            [213.0, 244.0],
            [244.0, 274.0],
            [274.0, 305.0],
            [305.0, 335.0],
            [335.0, 366.0],
        ]
        target_coord = self.time_coord(target_pnts, target_bnds)
        self.assertEqual(cube.coord("time"), target_coord)

    def test_value(self):
        set_month_mean_for_year(self.cube, 2000)
        self.assert_cube_climatology(self.cube)

    def test_pre_existing_time_cell_method(self):
        self.cube.add_cell_method(iris.coords.CellMethod("mean", coords="time"))
        set_month_mean_for_year(self.cube, 2000)
        self.assertEqual(len(self.cube.cell_methods), 1)

    def test_pre_existing_incompatible_time_cell_method(self):
        self.cube.add_cell_method(iris.coords.CellMethod("max", coords="time"))
        msg = "Pre-existing unexpected methods"
        with self.assertRaisesRegex(RuntimeError, msg):
            set_month_mean_for_year(self.cube, 2000)

    def test_other_time_based_coords(self):
        extra_time_coord = iris.coords.DimCoord(
            np.arange(12),
            bounds=None,
            standard_name="time",
            long_name="extra_time_coord",
            units=cf_units.Unit("days since 2000-01-01 00:00:00", calendar="gregorian"),
        )
        self.cube.add_aux_coord(extra_time_coord, 0)
        msg = "More than one time based coordinate"
        with self.assertRaisesRegex(RuntimeError, msg):
            set_month_mean_for_year(self.cube, 2000)

    def test_no_time_coord(self):
        cube = stock.geodetic((4, 4), data=np.zeros((4, 4)))
        msg = "No time based coordinates"
        with self.assertRaisesRegex(RuntimeError, msg):
            set_month_mean_for_year(cube, 2000)


if __name__ == "__main__":
    ants.tests.main()

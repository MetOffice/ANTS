# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import warnings

import ants.tests
import ants.tests.stock as stock
import iris
import numpy as np
from ants.regrid.rectilinear import _gen_regular_target as gen_regular_target


class Common(object):
    def _check_coordinates(self, result, expected_x, expected_y):
        # A 'nearly' equal between coordinates should be put into iris.
        res_x = result.coord(axis="x")
        res_y = result.coord(axis="y")

        # Ensure that the metadata is the same by creating temporary
        # coordinates which replace the points data.
        int_x = expected_x.copy(res_x.points, bounds=res_x.bounds)
        int_y = expected_y.copy(res_y.points, bounds=res_y.bounds)
        self.assertEqual(res_x, int_x)
        self.assertEqual(res_y, int_y)

        # Ensure that the points are equal
        self.assertArrayAlmostEqual(res_x.points, expected_x.points)
        self.assertArrayAlmostEqual(res_y.points, expected_y.points)
        self.assertArrayAlmostEqual(res_x.bounds, expected_x.bounds)
        self.assertArrayAlmostEqual(res_y.bounds, expected_y.bounds)


class Test1D(Common, ants.tests.TestCase):
    def test_same_crs(self):
        # Ensure that when asking to regularise an already regular cube with
        # identical coordinates, that we return a target with identical
        # coordinates.
        source = stock.geodetic((4, 4))
        target = stock.geodetic((4, 4))
        target.coord(axis="x").circular = True
        result = gen_regular_target(source, target)
        self._check_coordinates(target, result.coord(axis="x"), result.coord(axis="y"))

    def test_diff_crs_with_bounds(self):
        source = stock.osgb((4, 4), xlim=(0, 7e5), ylim=(0, 13e5))
        target = stock.geodetic((4, 4), xlim=(-15, 10), ylim=(45, 65), with_bounds=True)
        result = gen_regular_target(source, target)

        tar_x = target.coord(axis="x").copy()
        tar_y = target.coord(axis="y").copy()
        self._check_coordinates(result, tar_x, tar_y)

    def test_diff_crs_no_bounds(self):
        # Ensure that the intermediate target has bounds even though the bounds
        # are not present on the final target.
        source = stock.osgb((4, 4), xlim=(0, 7e5), ylim=(0, 13e5))
        target = stock.geodetic(
            (4, 4), xlim=(-15, 10), ylim=(45, 65), with_bounds=False
        )
        tar_x = target.coord(axis="x").copy()
        tar_x.guess_bounds()
        tar_y = target.coord(axis="y").copy()
        tar_y.guess_bounds()

        result = gen_regular_target(source, target)
        self._check_coordinates(result, tar_x, tar_y)

    def test_source_partial_coverage(self):
        # The shape of the intermediate grid should correspond to the shape of
        # the overlap source, not the original source.
        source = stock.geodetic((4, 4))
        source.coord(axis="x").circular = False
        target = stock.geodetic((4, 4), xlim=(10, 170))
        with warnings.catch_warnings():
            # Suppress the warning about regridding from lower resolution to
            # higher i.e. (4, 3) to (4, 4)
            warnings.simplefilter("ignore", UserWarning)
            result = gen_regular_target(source, target)

        # X is determined as having three overlapping cells with the target and
        # so the intermediate grid has 3 x points.
        tx = target.coord(axis="x")
        bnd_x = np.linspace(tx.bounds.min(), tx.bounds.max(), num=4)
        bnd_x = np.array([bnd_x[:-1], bnd_x[1:]]).T
        pnt_x = bnd_x.mean(axis=1)
        tar_x = target.coord(axis="x").copy(pnt_x, bounds=bnd_x)
        tar_y = target.coord(axis="y").copy()
        self._check_coordinates(result, tar_x, tar_y)


class TestND(Common, ants.tests.TestCase):
    def setUp(self):
        source = stock.geodetic((4, 4), xlim=(-10, 10), ylim=(45, 65))
        source2 = source.copy()
        source.add_aux_coord(iris.coords.AuxCoord(1, long_name="tmp"), None)
        source2.add_aux_coord(iris.coords.AuxCoord(2, long_name="tmp"), None)
        self.sources = iris.cube.CubeList([source, source2]).merge_cube()

    def test_multidim_z_y_x(self):
        # Ensure that intermediate grids properly support multidimensional
        # source cubes.
        target = self.sources[0].copy()
        result = gen_regular_target(self.sources, target)

        tar_x = self.sources.coord(axis="x")
        tar_y = self.sources.coord(axis="y")
        self._check_coordinates(result, tar_x, tar_y)

        self.assertEqual(result.coord_dims(tar_x), (1,))
        self.assertEqual(result.coord_dims(tar_y), (0,))

    def test_multidim_x_z_y(self):
        # Ensure that intermediate grids properly support multidimensional
        # source cubes with non-standard mapping.
        self.sources.transpose((2, 0, 1))
        target = self.sources[:, 1].copy()
        result = gen_regular_target(self.sources, target)

        tar_x = self.sources.coord(axis="x")
        tar_y = self.sources.coord(axis="y")
        self._check_coordinates(result, tar_x, tar_y)

        self.assertEqual(result.coord_dims(tar_x), (0,))
        self.assertEqual(result.coord_dims(tar_y), (1,))


if __name__ == "__main__":
    ants.tests.main()

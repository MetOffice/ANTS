# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
import numpy as np
from ants.regrid.rectilinear import _fill_outside_bounds, fill_range


class Common(object):
    def setUp(self):
        self.source = ants.tests.stock.geodetic((5, 5), ylim=(-90, 30), xlim=(-160, 80))
        self.target = ants.tests.stock.geodetic((5, 5))
        self.target.data = self.target.data.astype("float32")

        self.result = np.array(
            [
                [np.nan, 1, 2, np.nan, np.nan],
                [np.nan, 6, 7, np.nan, np.nan],
                [np.nan, 11, 12, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
            ],
            dtype=np.float32,
        )


class Test2D(Common, ants.tests.TestCase):
    def test_increasing(self):
        actual = _fill_outside_bounds(self.source, self.target, np.nan)
        self.assertArrayEqual(actual.data, self.result)

    @staticmethod
    def _invert_coord(coord):
        coord.points = coord.points[::-1]
        coord.bounds = coord.bounds[::-1, ::-1]

    def test_decreasing_source(self):
        sx = self.source.coord(axis="x")
        self._invert_coord(sx)
        sy = self.source.coord(axis="y")
        self._invert_coord(sy)

        actual = _fill_outside_bounds(self.source, self.target, np.NaN)
        self.assertArrayEqual(actual.data, self.result)

    def test_decreasing_target(self):
        # We copy the data here due to a numpy bug
        # https://github.com/numpy/numpy/issues/8264
        self.target.data = self.target.data[::-1, ::-1].copy()

        tx = self.target.coord(axis="x")
        self._invert_coord(tx)
        ty = self.target.coord(axis="y")
        self._invert_coord(ty)

        actual = _fill_outside_bounds(self.source, self.target, np.NaN)
        self.assertArrayEqual(actual.data, self.result[::-1, ::-1])

    def test_masked(self):
        # Ensure that masked elements outside the source extent become nan and
        # unmasked while masked elements inside the extent remain masked.
        self.target.data = np.ma.array(self.target.data)
        self.target.data[0, :] = np.ma.masked
        actual = _fill_outside_bounds(self.source, self.target, np.NaN)

        expected = np.ma.array(self.result)
        expected[0, 1:3] = np.ma.masked
        self.assertMaskedArrayEqual(actual.data, expected)


class TestND(Common, ants.tests.TestCase):
    def test_zyx_source(self):
        # Ensure no sensitivity to source dimension mapping
        cube1 = self.source
        cube2 = self.source.copy()

        coord = iris.coords.DimCoord(0, long_name="bla")
        cube1.add_aux_coord(coord, None)
        coord = iris.coords.DimCoord(1, long_name="bla")
        cube2.add_aux_coord(coord, None)

        self.source = iris.cube.CubeList([cube1, cube2]).merge_cube()

        actual = _fill_outside_bounds(self.source, self.target, np.NaN)
        self.assertArrayEqual(actual.data, self.result)

    def test_xzy(self):
        # Ensure no sensitivity to target dimension mapping
        cube1 = self.target
        cube2 = self.target.copy()

        coord = iris.coords.DimCoord(0, long_name="bla")
        cube1.add_aux_coord(coord, None)
        coord = iris.coords.DimCoord(1, long_name="bla")
        cube2.add_aux_coord(coord, None)

        self.target = iris.cube.CubeList([cube1, cube2]).merge_cube()

        self.result = np.vstack([self.result[None, ...], self.result[None, ...]])
        self.target.transpose((2, 0, 1))
        self.result = self.result.transpose((2, 0, 1))

        actual = _fill_outside_bounds(self.source, self.target, np.NaN)
        self.assertArrayEqual(actual.data, self.result)


class TestFillRange(Common, ants.tests.TestCase):
    def test_fill_range_with_indicies(self):
        source_cube = self.source
        coord = self.source.coord(axis="x")
        x_outside_bounds = np.array([True, False, True, True, True])
        value = np.nan

        expected = np.array(
            [
                [np.nan, 1, np.nan, np.nan, np.nan],
                [np.nan, 6, np.nan, np.nan, np.nan],
                [np.nan, 11, np.nan, np.nan, np.nan],
                [np.nan, 16, np.nan, np.nan, np.nan],
                [np.nan, 21, np.nan, np.nan, np.nan],
            ],
            dtype=np.float32,
        )
        result = fill_range(source_cube, x_outside_bounds, value, coord)
        self.assertEqual(expected.all(), result.data.all())

    def test_fill_range_without_indicies(self):
        x_outside_bounds = np.array([False, False, False, False, False])
        source_cube = self.source
        coord = iris.coords.DimCoord(0, long_name="bla")
        source_cube.add_aux_coord(coord, None)
        value = np.nan

        expected = source_cube.data
        result = fill_range(source_cube, x_outside_bounds, value, coord)
        self.assertEqual(expected.all(), result.data.all())


if __name__ == "__main__":
    ants.tests.main()

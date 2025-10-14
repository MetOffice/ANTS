# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.analysis._merge import MooreNeighbourhood

_UNITS = dict(longitude="degrees_east", latitude="degrees_north")


class Test___init__(ants.tests.TestCase):
    def _cube_with_shape(self, shape):
        alen = np.prod(np.array(shape))
        data = np.arange(alen).reshape(shape)
        cube = iris.cube.Cube(data)
        return cube

    def _add_horizontal_dimcoords(self, cube, x_coord, y_coord, idim):
        cube.add_dim_coord(y_coord, idim[0])
        cube.add_dim_coord(x_coord, idim[1])

    def _make_axis(self, xlen, name, bounds=None):
        axis_vals = np.arange(xlen)
        x_coord = iris.coords.DimCoord(
            axis_vals, standard_name=name, units=_UNITS[name], bounds=bounds
        )
        if bounds is None:
            x_coord.guess_bounds()
        return x_coord

    def test_raises_error_when_3d_cube(self):
        cube = self._cube_with_shape((1, 3, 3))
        x_coord = self._make_axis(3, "longitude")
        y_coord = self._make_axis(3, "latitude")
        self._add_horizontal_dimcoords(cube, x_coord, y_coord, (1, 2))

        with self.assertRaisesRegex(ValueError, "supports only 2d cubes"):
            MooreNeighbourhood(cube)

    def test_raises_error_when_non_contiguous_longitude(self):
        cube = self._cube_with_shape((3, 3))
        x_coord = self._make_axis(
            3, "longitude", bounds=np.array([[-0.5, 0.25], [0.5, 1.5], [1.5, 2.5]])
        )
        y_coord = self._make_axis(3, "latitude")
        self._add_horizontal_dimcoords(cube, x_coord, y_coord, (0, 1))

        with self.assertRaisesRegex(ValueError, "axes must be contiguous"):
            MooreNeighbourhood(cube)

    def test_raises_error_when_non_contiguous_latitude(self):
        cube = self._cube_with_shape((3, 3))
        x_coord = self._make_axis(3, "longitude")
        y_coord = self._make_axis(
            3, "latitude", bounds=np.array([[-0.5, 0.25], [0.5, 1.5], [1.5, 2.5]])
        )
        self._add_horizontal_dimcoords(cube, x_coord, y_coord, (0, 1))

        with self.assertRaisesRegex(ValueError, "axes must be contiguous"):
            MooreNeighbourhood(cube)

    def test_error_on_even_shape_mask(self):
        cube = self._cube_with_shape((3, 3))
        x_coord = self._make_axis(3, "longitude")
        y_coord = self._make_axis(3, "latitude")
        self._add_horizontal_dimcoords(cube, x_coord, y_coord, (0, 1))
        mask = np.zeros((4, 4))

        msg = "Expecting the provided mask"
        with self.assertRaisesRegex(ValueError, msg):
            MooreNeighbourhood(cube, window_mask=mask)

    def test_check_add_halo_call(self):
        # Ensure that add_halo is called with the expected halo width.
        cube = self._cube_with_shape((3, 3))
        x_coord = self._make_axis(3, "longitude")
        y_coord = self._make_axis(3, "latitude")
        self._add_horizontal_dimcoords(cube, x_coord, y_coord, (0, 1))
        mask = np.zeros((5, 3))

        with mock.patch("ants.analysis._merge._add_halo") as patch:
            patch.return_value = np.zeros((7, 5))
            MooreNeighbourhood(cube, window_mask=mask)
        self.assertArrayEqual(patch.call_args[-1]["halo_width"], np.array([2, 1]))

    def test_large_mask(self):
        # Check that we are using strides tricks properly for arbitrary window
        # sizes.
        self.cube = ants.tests.stock.geodetic((6, 6), with_bounds=True)
        self.cube.coord(axis="x").circular = False
        window_mask = np.ones((5, 5))
        nn = MooreNeighbourhood(self.cube, window_mask=window_mask)

        self.assertEqual(nn._views.shape, self.cube.shape + window_mask.shape)
        self.assertArrayEqual(nn._views[..., 2, 2], self.cube.data)


class Test_all_equal_value(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic((4, 4), with_bounds=True)
        self.cube.coord(axis="x").circular = False

    def test_unmasked(self):
        self.cube.data = np.array(
            [[1, 2, 3, 3], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 2]]
        )
        nn = MooreNeighbourhood(self.cube)
        tar = np.array(
            [
                [False, False, False, False],
                [False, False, False, False],
                [True, True, False, False],
                [True, True, False, True],
            ]
        )
        res = nn.all_equal_value(1)
        self.assertArrayEqual(res, tar)

    def test_masked(self):
        self.cube.data = np.ma.array(
            [[1, 2, 3, 3], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 2]]
        )
        mask = np.zeros((4, 4))
        mask[0, 1] = True
        self.cube.data.mask = mask
        nn = MooreNeighbourhood(self.cube)
        tar = np.array(
            [
                [True, False, False, False],
                [True, False, False, False],
                [True, True, False, False],
                [True, True, False, True],
            ]
        )
        res = nn.all_equal_value(1)
        self.assertArrayEqual(res, tar)

    def test_large_mask(self):
        self.cube = ants.tests.stock.geodetic((6, 6), with_bounds=True)
        self.cube.coord(axis="x").circular = False
        self.cube.data = np.array(
            [
                [1, 1, 1, 1, 1, 0],
                [1, 1, 1, 1, 1, 0],
                [1, 1, 1, 1, 1, 0],
                [1, 1, 1, 1, 1, 0],
                [1, 1, 1, 1, 1, 0],
                [0, 0, 0, 0, 0, 1],
            ]
        )
        target = np.zeros((6, 6), dtype=bool)
        target[:3, :3] = True
        nn = MooreNeighbourhood(self.cube, window_mask=np.ones((5, 5)))
        res = nn.all_equal_value(1)
        self.assertArrayEqual(res, target)


class Test__count_missing(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic((4, 4), with_bounds=True)
        self.cube.coord(axis="x").circular = False
        self.cube.data = np.ma.array(
            [[1, 2, 3, 3], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 2]]
        )

    def test_unmasked(self):
        nn = MooreNeighbourhood(self.cube)
        tar = np.array([[5, 3, 3, 5], [3, 0, 0, 3], [3, 0, 0, 3], [5, 3, 3, 5]])
        res = nn._count_missing()
        self.assertArrayEqual(res, tar)

    def _test_mask_comparison(self):
        tar = np.array([[5, 4, 3, 6], [3, 1, 1, 4], [3, 0, 0, 3], [5, 3, 3, 5]])
        nn = MooreNeighbourhood(self.cube)
        res = nn._count_missing()
        self.assertArrayEqual(res, tar)

    def test_masked(self):
        mask = np.zeros((4, 4))
        mask[0, 2] = True
        self.cube.data.mask = mask
        self._test_mask_comparison()

    def test_filled_no_explicit_mask(self):
        # Ensure that the behaviour is equivelent for the case where the array
        # has populated fill values rather an explicit mask array.
        self.cube.data[0, 2] = 10
        self.cube.data.set_fill_value(10)
        self._test_mask_comparison()


class Test_all_missing(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic((4, 4), with_bounds=True)
        self.cube.coord(axis="x").circular = False
        self.cube.data = np.ma.array(
            [[1, 2, 3, 3], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 2]], fill_value=1
        )
        nn = MooreNeighbourhood(self.cube)
        tar = np.array(
            [
                [False, False, False, False],
                [False, False, False, False],
                [True, True, False, False],
                [True, True, False, True],
            ]
        )
        res = nn.all_missing()
        self.assertArrayEqual(res, tar)


class Test_any_non_missing(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic((4, 4), with_bounds=True)
        self.cube.coord(axis="x").circular = False
        self.cube.data = np.ma.array(
            [[1, 2, 3, 3], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 2]], fill_value=1
        )
        nn = MooreNeighbourhood(self.cube)
        tar = np.array(
            [
                [True, True, True, True],
                [True, True, True, True],
                [False, False, True, True],
                [False, False, True, False],
            ]
        )
        res = nn.any_non_missing()
        self.assertArrayEqual(res, tar)


class Test_any_equal_value(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic((4, 4), with_bounds=True)
        self.cube.coord(axis="x").circular = False

    def test_unmasked(self):
        self.cube.data = np.array(
            [[0, 2, 3, 3], [0, 1, 1, 1], [1, 1, 0, 0], [1, 1, 0, 2]]
        )
        nn = MooreNeighbourhood(self.cube)
        tar = np.ones((4, 4))
        tar[-1, -1] = False
        res = nn.any_equal_value(1)
        self.assertArrayEqual(res, tar)

    def test_masked(self):
        self.cube.data = np.ma.array(
            [[0, 2, 3, 3], [0, 1, 1, 1], [1, 1, 0, 0], [1, 1, 0, 2]]
        )
        mask = np.zeros((4, 4))
        mask[1, 1] = True
        self.cube.data.mask = mask
        nn = MooreNeighbourhood(self.cube)
        tar = np.ones((4, 4))
        tar[-1, -1] = tar[0, 0] = False
        res = nn.any_equal_value(1)
        self.assertArrayEqual(res, tar)

    def test_array_value(self):
        self.cube.data = np.array(
            [[1, 1, 1, 1], [2, 1, 1, 1], [1, 1, 3, 1], [1, 2, 3, 1]]
        )
        value = np.array([[0, 0, 0], [0, 0, 0], [0, 2, 3]])
        tar = np.array(
            [
                [True, False, False, False],
                [False, True, False, False],
                [False, True, False, False],
                [False, False, False, False],
            ]
        )

        nn = MooreNeighbourhood(self.cube)
        res = nn.any_equal_value(value)
        self.assertArrayEqual(res, tar)


class Test_neighbourhood_mean(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic((4, 4), with_bounds=True)
        self.cube.coord(axis="x").circular = False

    def test_unmasked(self):
        self.cube.data = np.array(
            [[0, 2, 2, 2], [0, 1, 1, 1], [1, 1, 0, 0], [1, 1, 0, 2]]
        )
        nn = MooreNeighbourhood(self.cube)

        tar = np.array(
            [
                [1.0, 0.8, 1.4, 1.33333333],
                [1.0, 0.875, 1.125, 1.0],
                [0.8, 0.625, 0.875, 0.8],
                [1.0, 0.6, 0.8, 0.0],
            ]
        )
        res = nn.neighbourhood_mean()
        self.assertArrayAlmostEqual(res, tar)

    def test_masked(self):
        self.cube.data = np.ma.array(
            [[0, 2, 2, 2], [0, 1, 1, 1], [1, 1, 0, 0], [1, 1, 0, 2]]
        )
        mask = np.zeros((4, 4))
        mask[0, 0] = True
        self.cube.data.mask = mask
        nn = MooreNeighbourhood(self.cube)

        tar = np.array(
            [
                [1.0, 1.0, 1.4, 1.33333333],
                [1.25, 1.0, 1.125, 1.0],
                [0.8, 0.625, 0.875, 0.8],
                [1.0, 0.6, 0.8, 0.0],
            ]
        )
        res = nn.neighbourhood_mean()
        self.assertArrayAlmostEqual(res, tar)


if __name__ == "__main__":
    ants.tests.main()

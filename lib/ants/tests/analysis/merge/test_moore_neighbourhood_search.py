# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
import numpy as np
from ants.analysis._merge import moore_neighbourhood_search


class _MaskApplication(object):
    def get_cube(self, data):
        # Return a global cube with -1 values the assumed masked values
        cube = ants.tests.stock.geodetic(data.shape, with_bounds=True)
        cube.coord(axis="x").circular = False
        data = np.ma.masked_values(data, -1, copy=False)
        cube.data = data
        return cube

    def _assert_expected(self, cube, target, land_binary_mask):
        self.assertArrayEqual(cube.data.data, target)
        self.assertArrayEqual(cube.data.mask, land_binary_mask.data == 0)


class Test_inappropriate_input(_MaskApplication, ants.tests.TestCase):
    def test_not_2d_source(self):
        cube = iris.cube.Cube(np.arange(8).reshape(2, 2, 2))
        land_binary_mask = iris.cube.Cube(np.arange(8).reshape(2, 2, 2))
        msg = (
            "Currently, only mask application to 2D grids are supported "
            "and with no broadcasting."
        )
        with self.assertRaisesRegex(RuntimeError, msg):
            moore_neighbourhood_search(cube, land_binary_mask)

    def test_different_grids(self):
        data = np.arange(4).reshape(2, 2)
        cube = self.get_cube(data)
        land_binary_mask = self.get_cube(data)
        land_binary_mask.coord(axis="x").points = cube.coord(axis="x").points - 10
        msg = "Both source and land_binary_mask must be defined on identical " "grids"
        with self.assertRaisesRegex(RuntimeError, msg):
            moore_neighbourhood_search(cube, land_binary_mask)

    def test_alternate_orientation(self):
        # Currently we do not support automatically transposing the data where
        # coordinates are mapped to alternate dimensions.  Make sure we catch
        # this case.
        data = np.arange(4).reshape(2, 2)
        cube = self.get_cube(data)
        land_binary_mask = self.get_cube(data)
        lx = land_binary_mask.coord(axis="x")
        ly = land_binary_mask.coord(axis="y")
        land_binary_mask.remove_coord(lx)
        land_binary_mask.remove_coord(ly)
        land_binary_mask.add_dim_coord(lx, 0)
        land_binary_mask.add_dim_coord(ly, 1)

        msg = (
            "Currently, the source and the land_binary_mask must be "
            "defined in the same orientation"
        )
        with self.assertRaisesRegex(RuntimeError, msg):
            moore_neighbourhood_search(cube, land_binary_mask)


class Test_missing_coastlines(_MaskApplication, ants.tests.TestCase):
    def test_no_change(self):
        data = np.ma.array([[-1, 2, 3], [4, -1, -1], [7, 8, 9]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy((data > 0).astype(int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.copy()
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_top_left_edge(self):
        data = np.ma.array([[-1, 2, 3], [2, 5, 6], [7, 8, 9]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[0, 0] = 3
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_top_centre_edge(self):
        data = np.ma.array([[4, -1, 3], [2, 5, 6], [7, 8, 9]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[0, 1] = 4
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_top_right_edge(self):
        data = np.ma.array([[4, 2, -1], [2, 5, 2], [7, 8, 9]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[0, 2] = 3
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_centre_left_edge(self):
        data = np.ma.array([[4, 2, 2], [-1, 5, 2], [3, 6, 9]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[1, 0] = 4
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_centre_centre(self):
        data = np.ma.array([[2, 4, 2], [4, -1, 4], [2, 4, 2]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[1, 1] = 3
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_centre_right_edge(self):
        data = np.ma.array([[2, 4, 2], [4, 3, -1], [2, 4, 2]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[1, 2] = 3
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_bottom_left_edge(self):
        data = np.ma.array([[2, 4, 2], [4, 3, 6], [-1, 5, 2]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[2, 0] = 4
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_bottom_centre_edge(self):
        data = np.ma.array([[2, 4, 2], [4, 3, 6], [5, -1, 2]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[2, 1] = 4
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_bottom_right_edge(self):
        data = np.ma.array([[2, 4, 2], [4, 3, 6], [5, 3, -1]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[2, 2] = 4
        self._assert_expected(cube, target, land_binary_mask)

    def test_missing_including_zero_values(self):
        # Ensure that the value 0 is included in the count for valid
        # neighbours.
        data = np.ma.array([[2, 4, 2], [4, 0, 7], [5, 3, -1]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[2, 2] = 10 / 3.0
        self._assert_expected(cube, target, land_binary_mask)

    def test_global_circular(self):
        # Ensure that we correctly handle wraparound coordinates
        data = np.ma.array([[2, 4, 2], [4, 3, 5], [5, 3, -1]], dtype=float)
        cube = self.get_cube(data)
        cube.coord(axis="x").circular = True
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[2, 2] = 4
        self._assert_expected(cube, target, land_binary_mask)

    def test_global_circular_transposed(self):
        # Ensure that we correctly handle wraparound coordinates where x and y
        # are mapped to alternative dimensions.
        data = np.ma.array([[2, 4, 2], [4, 3, 5], [5, 6, -1]], dtype=float)
        cube = self.get_cube(data)
        coord_x = cube.coord(axis="x")
        coord_x.circular = True
        coord_y = cube.coord(axis="y")
        cube.remove_coord(coord_x)
        cube.remove_coord(coord_y)
        cube.add_dim_coord(coord_x, 0)
        cube.add_dim_coord(coord_y, 1)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))

        moore_neighbourhood_search(cube, land_binary_mask, 10)

        target = data.data.copy()
        target[2, 2] = 4
        self._assert_expected(cube, target, land_binary_mask)


class Test_missing_islands(_MaskApplication, ants.tests.TestCase):
    def test_isolated_data(self):
        data = np.ma.array([[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.zeros(data.shape, dtype=int))
        land_binary_mask.data[1, 1] = 1

        moore_neighbourhood_search(cube, land_binary_mask, value=10)

        target = data.data.copy()
        target[1, 1] = 10
        self._assert_expected(cube, target, land_binary_mask)

    def test_default_fill_value_no_valid_data(self):
        # Ensure that islands stay as missing if we cannot infer a reasonable
        # fill value (i.e. no valid data present to calculate a mean).
        data = np.ma.array([[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.zeros(data.shape, dtype=int))
        land_binary_mask.data[1, 1] = 1

        moore_neighbourhood_search(cube, land_binary_mask)

        target = data.data.copy()
        target_land_binary_mask = cube.copy(np.zeros(data.shape, dtype=int))
        self._assert_expected(cube, target, target_land_binary_mask)

    def test_default_fill_value_valid_data(self):
        # Ensure that the default fill value with fill the island with the data
        # mean if there is valid data present.
        data = np.ma.array([[-1, -1, 5], [-1, -1, 4], [1, 2, 3]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy()
        land_binary_mask.data = (land_binary_mask.data > 0).astype(int)
        land_binary_mask.data[0, 0] = 1

        moore_neighbourhood_search(cube, land_binary_mask)

        target = data.data.copy()
        target[0, 0] = 3
        self._assert_expected(cube, target, land_binary_mask)


class Test_mask_prioritisation(_MaskApplication, ants.tests.TestCase):
    def test_masked_source_not_masked_target(self):
        # Ensure that we use all source data available to derive missing points
        # but modify the mask to remove these points that are masked in the
        # provided binary land mask.
        data = np.ma.array([[1, 2, 3], [4, 5, 5], [7, 8, -1]], dtype=float)
        cube = self.get_cube(data)
        land_binary_mask = cube.copy(np.ones(data.shape, dtype=int))
        land_binary_mask.data[1, 1] = 0

        moore_neighbourhood_search(cube, land_binary_mask)

        target = data.copy()
        target[2, 2] = 6.5
        self._assert_expected(cube, target, land_binary_mask)


if __name__ == "__main__":
    ants.tests.main()

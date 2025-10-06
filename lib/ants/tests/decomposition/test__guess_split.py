# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import dask.array as da
import iris
import numpy as np
from ants.decomposition import _guess_split as guess_split


class TestSourceOnly(ants.tests.TestCase):
    def test_2d_64bit(self):
        data = da.zeros((2e4, 4e4), dtype=np.float64, chunks=(2e4, 4e4))
        cube = ants.tests.stock.geodetic(data.shape, data=data)
        split = guess_split(cube)
        self.assertEqual(split, {"split_y": 2, "split_x": 4})

    def test_2d_32bit(self):
        data = da.zeros((2e4, 4e4), dtype=np.float32, chunks=(2e4, 4e4))
        cube = ants.tests.stock.geodetic(data.shape, data=data)
        split = guess_split(cube)
        self.assertEqual(split, {"split_y": 2, "split_x": 3})

    def test_3d(self):
        data = da.zeros((2e4, 4e4), dtype=np.float64, chunks=(2e4, 4e4))
        cube = ants.tests.stock.geodetic(data.shape, data=data)
        cube2 = cube.copy(data)
        cube.add_aux_coord(iris.coords.DimCoord(0, long_name="bla"), None)
        cube2.add_aux_coord(iris.coords.DimCoord(1, long_name="bla"), None)
        cube = iris.cube.CubeList([cube, cube2]).merge_cube()

        split = guess_split(cube)
        self.assertEqual(split, {"split_y": 3, "split_x": 6})


class TestTarget(ants.tests.TestCase):
    def test_2d_32bit_source_64bit_target(self):
        data = da.zeros((2e4, 4e4), dtype=np.float32, chunks=(2e4, 4e4))
        source = ants.tests.stock.geodetic(data.shape, data=data)

        data = da.zeros((1e2, 1e2), dtype=np.float64, chunks=(1e2, 1e2))
        target = ants.tests.stock.geodetic(data.shape, data=data)

        split = guess_split(source, target)
        self.assertEqual(split, {"split_y": 2, "split_x": 4})

    def test_2d_32bit_source_32bit_target(self):
        data = da.zeros((2e4, 4e4), dtype=np.float32, chunks=(2e4, 4e4))
        source = ants.tests.stock.geodetic(data.shape, data=data)

        data = da.zeros((1e2, 1e2), dtype=np.float32, chunks=(1e2, 1e2))
        target = ants.tests.stock.geodetic(data.shape, data=data)

        split = guess_split(source, target)
        self.assertEqual(split, {"split_y": 2, "split_x": 3})

    def test_2d_opposite_mapping(self):
        # Ensure that we cope with the case where target and source grids have
        # different dimension mapping.
        data = da.zeros((2e4, 4e4), dtype=np.float32, chunks=(2e4, 4e4))
        source = ants.tests.stock.geodetic(data.shape, data=data)

        nsource = iris.cube.Cube(
            da.zeros((4e4, 2e4), dtype=np.float32, chunks=(4e4, 2e4))
        )
        x, y = ants.utils.cube.horizontal_grid(source)
        nsource.add_dim_coord(x, 0)
        nsource.add_dim_coord(y, 1)

        data = da.zeros((1e2, 1e2), dtype=np.float32, chunks=(1e2, 1e2))
        target = ants.tests.stock.geodetic(data.shape, data=data)

        split = guess_split(nsource, target)
        self.assertEqual(split, {"split_y": 2, "split_x": 3})

    def test_large_targe(self):
        shape = (2e4, 4e4)
        data = da.zeros(shape, dtype=np.float32, chunks=shape)
        source = ants.tests.stock.geodetic(data.shape, data=data)

        shape = (1e6, 2e6)
        data = da.zeros(shape, dtype=np.float64, chunks=shape)
        target = ants.tests.stock.geodetic(data.shape, data=data)

        split = guess_split(source, target)
        self.assertEqual(split, {"split_y": 100, "split_x": 200})

    def test_nd(self):
        shape = (12, 470, 144, 192)
        data = da.zeros(shape, dtype=np.float32, chunks=shape)
        source = ants.tests.stock.geodetic(data.shape, data=data)

        data = da.zeros(shape, dtype=np.float64, chunks=shape)
        target = ants.tests.stock.geodetic(data.shape, data=data)

        split = guess_split(source, target)
        self.assertEqual(split, {"split_y": 2, "split_x": 2})


class TestException(ants.tests.TestCase):
    def test_multidimensional_coordinates(self):
        # We don't yet bother supporting multidimensional grid coords
        # (unstructured grids) when guessing the split for decomposition.
        data = da.zeros((3, 4), dtype=np.float32, chunks=(3, 4))
        source = ants.tests.stock.geodetic(data.shape, data=data)
        target = ants.tests.stock.geodetic(data.shape, data=data)
        target.remove_coord("longitude")
        lon_coord = iris.coords.AuxCoord(data, "longitude")
        target.add_aux_coord(lon_coord, (0, 1))
        msg = "Currently, unable to guess a suitable decomposition split"
        with self.assertRaisesRegex(RuntimeError, msg):
            guess_split(source, target)


if __name__ == "__main__":
    ants.tests.main()

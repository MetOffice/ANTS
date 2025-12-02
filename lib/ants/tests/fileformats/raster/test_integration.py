# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import pickle as pickle

import ants.fileformats.raster as raster
import ants.tests as tests
import numpy as np


class TestPickleable(tests.TestCase):
    def assertProxyEqual(self, proxy1, proxy2):
        for item in proxy1.__slots__:
            self.assertEqual(getattr(proxy1, item), getattr(proxy2, item))

    def test_all(self):
        # Ensure that the __getstate__ and __setstate__ special methods
        # provide pickleable gdal proxies.  See
        # https://docs.python.org/3.7/library/pickle.html
        proxy = raster._GdalDataProxy((2, 3), np.uint8, "some_path.bil", 0, -999)
        proxy_pickled = pickle.dumps(proxy)
        proxy_unpickled = pickle.loads(proxy_pickled)
        self.assertProxyEqual(proxy_unpickled, proxy)


@tests.skip_gdal
class TestGlobalField(tests.TestCase):
    def assertCubeEqual(self, cube1, cube2):
        self.assertArrayEqual(cube1.data, cube2.data)
        for ax in ["x", "y"]:
            c1_coord = cube1.coord(axis=ax)
            c2_coord = cube2.coord(axis=ax)
            self.assertEqual(cube1.coord_dims(c1_coord), cube2.coord_dims(c2_coord))
            self.assertArrayEqual(c1_coord.points, c2_coord.points)
            self.assertArrayEqual(c1_coord.bounds, c2_coord.bounds)

    def test_yx_increasing_coord(self):
        cube = tests.stock.geodetic((6, 3))
        res_cube = next(raster.load_cubes(tests.get_data_path("global_geodetic.tif")))
        self.assertCubeEqual(res_cube, cube)


@tests.skip_gdal
class TestDeferredLoading(tests.TestCase):
    def setUp(self):
        self.cube = tests.stock.geodetic((6, 3))
        self.res_cube = next(
            raster.load_cubes(tests.get_data_path("global_geodetic.tif"))
        )

    def test_no_touch_defer_status(self):
        self.assertTrue(self.res_cube.has_lazy_data())

    def test_touch_defer_status(self):
        self.res_cube.data
        self.assertFalse(self.res_cube.has_lazy_data())

    def test_partial_touch(self):
        res_cube = self.res_cube[3:, 1:]
        res = res_cube.data
        tar = self.cube[3:, 1:].data
        self.assertArrayEqual(res, tar)
        self.assertFalse(res_cube.has_lazy_data())
        self.assertTrue(self.res_cube.has_lazy_data())

    def test_partial_touch_alt(self):
        res_cube = self.res_cube[1:]
        res = res_cube.data
        tar = self.cube[1:].data
        self.assertArrayEqual(res, tar)
        self.assertFalse(res_cube.has_lazy_data())
        self.assertTrue(self.res_cube.has_lazy_data())

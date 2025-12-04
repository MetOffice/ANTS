# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import dask
import iris
import numpy as np
from ants.utils.cube import fix_mask


class TestAll(ants.tests.TestCase):
    def test_add_missing_mask(self):
        # Add mask of False values when none is present at all
        cubeshape = (2, 2, 2)
        acube = ants.tests.stock.geodetic(cubeshape)
        self.assertFalse(hasattr(acube.data, "mask"))

        fix_mask(acube)

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, cubeshape)
        self.assertTrue((acube.data.mask == np.zeros(cubeshape, dtype=bool)).all())

    def test_expand_single_false(self):
        cubeshape = (2, 2, 2)
        acube = ants.tests.stock.geodetic(cubeshape)
        self.assertFalse(hasattr(acube.data, "mask"))

        acube.data = np.ma.masked_array(acube.data)
        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask, False)

        fix_mask(acube)

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, cubeshape)
        self.assertTrue((acube.data.mask == np.zeros(cubeshape, dtype=bool)).all())

    def test_no_change_falses(self):
        # Do nothing - mask already ok
        cubeshape = (2, 2, 2)
        acube = ants.tests.stock.geodetic(cubeshape)
        self.assertFalse(hasattr(acube.data, "mask"))
        acube.data = np.ma.masked_array(
            acube.data, mask=np.zeros(acube.data.shape, dtype=bool)
        )
        self.assertTrue(hasattr(acube.data, "mask"))
        fix_mask(acube)

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, cubeshape)
        self.assertTrue((acube.data.mask == np.zeros(cubeshape, dtype=bool)).all())

    def test_no_change_trues(self):
        # Do nothing - mask already ok
        cubeshape = (2, 2, 2)
        acube = ants.tests.stock.geodetic(cubeshape)
        self.assertFalse(hasattr(acube.data, "mask"))
        acube.data = np.ma.masked_array(
            acube.data, mask=np.ones(acube.data.shape, dtype=bool)
        )
        self.assertTrue(hasattr(acube.data, "mask"))
        fix_mask(acube)

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, cubeshape)
        self.assertTrue((acube.data.mask == np.ones(cubeshape, dtype=bool)).all())

    def test_single_element_check(self):
        cubeshape = (1, 1)
        acube = ants.tests.stock.geodetic(cubeshape)
        self.assertFalse(hasattr(acube.data, "mask"))

        acube.data = np.ma.masked_array(acube.data)
        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask, False)

        fix_mask(acube)

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, cubeshape)
        self.assertTrue((acube.data.mask == np.zeros(cubeshape, dtype=bool)).all())

    def test_fix_mask_cubelist(self):
        # Do nothing - masks already ok
        cubeshape = (2, 2, 2)
        acube = ants.tests.stock.geodetic(cubeshape)
        bcube = ants.tests.stock.geodetic(cubeshape)
        cubes = iris.cube.CubeList([acube, bcube])
        for cube in cubes:
            self.assertFalse(hasattr(cube.data, "mask"))
            cube.data = np.ma.masked_array(
                cube.data, mask=np.ones(cube.data.shape, dtype=bool)
            )
            self.assertTrue(hasattr(cube.data, "mask"))

        fix_mask(cubes)

        for cube in cubes:
            self.assertTrue(hasattr(cube.data, "mask"))
            self.assertEqual(cube.data.mask.shape, cubeshape)
            self.assertTrue((cube.data.mask == np.ones(cubeshape, dtype=bool)).all())

    def test_add_missing_mask_cubelist(self):
        # Add masks to the cubes in a cube list when none are present at all
        cubeshape = (2, 2, 2)
        acube = ants.tests.stock.geodetic(cubeshape)
        bcube = ants.tests.stock.geodetic(cubeshape)
        cubes = iris.cube.CubeList([acube, bcube])
        for cube in cubes:
            self.assertFalse(hasattr(cube.data, "mask"))

        fix_mask(cubes)

        for cube in cubes:
            self.assertTrue(hasattr(cube.data, "mask"))
            self.assertEqual(cube.data.mask.shape, cubeshape)
            self.assertTrue((cube.data.mask == np.zeros(cubeshape, dtype=bool)).all())

    def test_cube_numpy_data_boolean_False_adds_mask(self):
        masked_array = np.ma.masked_array([1, 2, 3], mask=False)
        acube = iris.cube.Cube(masked_array)

        self.assertFalse(acube.has_lazy_data())
        fix_mask(acube)
        self.assertFalse(acube.has_lazy_data())

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, acube.data.shape)
        self.assertTrue(
            (acube.data.mask == np.zeros(acube.data.shape, dtype=bool)).all()
        )

    def test_cube_dask_data_boolean_False_adds_mask_unrealised(self):
        masked_array = dask.array.ma.masked_array([1, 2, 3], mask=False)
        acube = iris.cube.Cube(masked_array)

        self.assertTrue(acube.has_lazy_data())
        fix_mask(acube)
        self.assertTrue(acube.has_lazy_data())

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, acube.data.shape)
        self.assertTrue(
            (acube.data.mask == np.zeros(acube.data.shape, dtype=bool)).all()
        )

    def test_fix_mask_for_numpy_arrays_keeps_type(self):
        masked_array = np.ma.masked_array([1, 2, 3], mask=False)
        acube = iris.cube.Cube(masked_array)

        pre_fix_type = acube.core_data()
        self.assertIsInstance(pre_fix_type, np.ndarray)
        self.assertFalse(acube.has_lazy_data())

        fix_mask(acube)

        post_fix_type = acube.core_data()
        self.assertIsInstance(post_fix_type, np.ndarray)
        self.assertFalse(acube.has_lazy_data())

    def test_fix_mask_for_dask_arrays_keeps_type(self):
        masked_array = dask.array.ma.masked_array([1, 2, 3], mask=False)
        acube = iris.cube.Cube(masked_array)

        pre_fix_type = acube.core_data()
        self.assertIsInstance(pre_fix_type, dask.array.core.Array)
        self.assertTrue(acube.has_lazy_data())

        fix_mask(acube)

        self.assertTrue(acube.has_lazy_data())
        post_fix_type = acube.core_data()
        self.assertIsInstance(post_fix_type, dask.array.core.Array)

    def test_cube_numpy_data_mask_unmatched(self):
        error_string = "Mask and data not compatible: data size is 3, mask size is 2."
        with self.assertRaises(np.ma.core.MaskError) as e:
            np.ma.masked_array([1, 2, 3], mask=[0, 1])
            assert e.message == error_string

    def test_cube_dask_data_mask_unmatched(self):
        error_string = "Mask and data not compatible: data size is 3, mask size is 2."
        with self.assertRaises(np.ma.core.MaskError) as e:
            dask.array.ma.masked_array([1, 2, 3], mask=[0, 1])
            assert e.message == error_string

    def test_cube_numpy_data_mask_single_true(self):
        masked_array = np.ma.masked_array([1, 2, 3], mask=True)
        acube = iris.cube.Cube(masked_array)

        fix_mask(acube)

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, acube.data.shape)
        self.assertTrue(np.ma.all(np.ma.getmask(acube.core_data())))

    def test_cube_dask_data_mask_single_true(self):
        masked_array = dask.array.ma.masked_array([1, 2, 3], mask=True)
        acube = iris.cube.Cube(masked_array)

        fix_mask(acube)

        self.assertTrue(hasattr(acube.data, "mask"))
        self.assertEqual(acube.data.mask.shape, acube.data.shape)
        self.assertTrue(dask.array.all(dask.array.ma.getmaskarray(acube.core_data())))

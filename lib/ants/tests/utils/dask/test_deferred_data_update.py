# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import dask.array as da
import iris.cube
import numpy as np
from ants.utils.dask import deferred_data_update


class DummyDataProxy(object):
    def __init__(self, shape, dtype):
        self.shape = shape
        self.dtype = dtype
        self.recorded_keys = []

    @property
    def ndim(self):
        return len(self.shape)

    def __getitem__(self, keys):
        self.recorded_keys.append(keys)
        return None


class TestValues(ants.tests.TestCase):
    def test_2d_overwrite_data(self):
        expected = np.array(
            [[0, 100, 200, 3], [4, 300, 400, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
        )
        data = np.arange(16).reshape((4, 4))
        overwrite_data = np.array([[100, 200], [300, 400]])
        slices = tuple([slice(0, 2), slice(1, 3)])
        result = deferred_data_update(data, overwrite_data, slices)
        self.assertArrayEqual(expected, result)


class TestAlreadyADaskArray(ants.tests.TestCase):
    def test_deferred_data_given_a_dask_array(self):
        expected = np.array(
            [[0, 100, 200, 3], [4, 300, 400, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
        )
        cube_data = iris.cube.Cube(np.arange(16).reshape((4, 4)))
        data = cube_data.lazy_data()
        overwrite_data = np.array([[100, 200], [300, 400]])
        slices = tuple([slice(0, 2), slice(1, 3)])
        result = deferred_data_update(data, overwrite_data, slices)
        self.assertArrayEqual(expected, result)

    def test_lazy_deferred_data_remains_unrealised(self):
        # all Dask arrays are lazy, see
        # https://docs.dask.org/en/stable/array-creation.html
        expected = da.from_array(
            np.array(
                [[0, 100, 200, 3], [4, 300, 400, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
            )
        )
        cube_data = iris.cube.Cube(np.arange(16).reshape((4, 4)))
        lazy_data = cube_data.lazy_data()
        new_lazy_data = da.from_array(np.array([[100, 200], [300, 400]]))
        slices = tuple([slice(0, 2), slice(1, 3)])
        result = deferred_data_update(lazy_data, new_lazy_data, slices)
        self.assertEqual(type(result), da.Array)
        self.assertArrayEqual(expected, result)


class TestExceptions(ants.tests.TestCase):
    def test_with_strings(self):
        data = "random string one"
        overwrite_data = "random string two"
        slices = tuple([slice(0, 2), slice(1, 3)])
        with self.assertRaises(AttributeError) as error:
            deferred_data_update(data, overwrite_data, slices)
            assert error.message == "'str' object has no attribute 'ndim'"

    def test_random_object_throws_error(self):
        data = DummyDataProxy(shape=(1, 1), dtype=int)
        overwrite_data = DummyDataProxy(shape=(1, 1), dtype=int)
        slices = [slice(0, 0)]
        with self.assertRaises(IndexError) as error:
            deferred_data_update(data, overwrite_data, slices)
            assert error.message == "list index out of range"

    def test_nd_source(self):
        source = mock.Mock(name="data", ndim=1)
        target = mock.Mock(name="data", ndim=2)
        msg = "Expected 2D source data, got 1 instead"
        with self.assertRaisesRegex(ValueError, msg):
            deferred_data_update(source, target, mock.sentinel.slices)

    def test_nd_target(self):
        source = mock.Mock(name="data", ndim=2)
        target = mock.Mock(name="data", ndim=1)
        msg = "Expected 2D target data, got 1 instead"
        with self.assertRaisesRegex(ValueError, msg):
            deferred_data_update(source, target, mock.sentinel.slices)

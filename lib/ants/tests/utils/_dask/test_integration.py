# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import dask.array as da
import numpy as np


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


class TestConcatenation(ants.tests.TestCase):
    def setUp(self):
        self.proxy = DummyDataProxy((32, 20, 30), "float64")
        self.dask_array = da.from_array(self.proxy, chunks=(16, 20, 30))

    def test_native_chunking_concatenation_second_axis(self):
        expected = (32, 4, 4)
        da1 = self.dask_array[:, :4, :2]
        da2 = self.dask_array[:, :4, -2:]
        result = da.concatenate([da1, da2], axis=2).shape
        self.assertEqual(result, expected)

    def test_native_chunking_concatenation_first_axis(self):
        expected = (32, 8, 2)
        da1 = self.dask_array[:, :4, :2]
        da2 = self.dask_array[:, :4, -2:]
        result = da.concatenate([da1, da2], axis=1).shape
        self.assertEqual(result, expected)

    def test_native_chunking_concatenation_zero_axis(self):
        expected = (64, 4, 2)
        da1 = self.dask_array[:, :4, :2]
        da2 = self.dask_array[:, :4, -2:]
        result = da.concatenate([da1, da2], axis=0).shape
        self.assertEqual(result, expected)

    def test_native_shape_cube(self):
        expected = (4, 4, 4)
        da1 = da.from_array(self.proxy, chunks=(2, 5, 8))[:4, :4, :2]
        da2 = da.from_array(self.proxy, chunks=(2, 5, 8))[:4, :4, -2:]
        result = da.concatenate([da1, da2], axis=2).shape
        self.assertEqual(result, expected)

    def test_realised_data_cube(self):
        expected = np.ones((4, 4, 4), dtype="float64", order="C")
        np_data = np.ones((4, 5, 8), dtype="float64", order="C")
        dask_array1 = da.from_array(np_data, chunks=(2, 5, 8))[:, :4, :2]
        dask_array2 = da.from_array(np_data, chunks=(2, 5, 8))[:, :4, -2:]
        concatenated_dask_arrays = da.concatenate([dask_array1, dask_array2], axis=2)
        result = concatenated_dask_arrays.compute()
        self.assertEqual(expected.all(), result.all())

    def test_slice_data_realisation(self):
        # Ensure that the original array is untouched when we create a new array
        # from a slice of the original array and realise the data.
        og_dask_array = da.from_array(np.ones((4, 5, 8), dtype="float64"))
        dask_array = da.asarray(og_dask_array)[:, :4, :2]
        realised_slice = dask_array.compute()
        self.assertEqual(type(realised_slice), np.ndarray)
        self.assertEqual(type(og_dask_array), da.Array)


if __name__ == "__main__":
    ants.tests.main()

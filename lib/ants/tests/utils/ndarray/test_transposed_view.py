# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest

import ants.tests
import numpy as np
from ants.utils.ndarray import transposed_view as transpose


class Common(object):
    def assert_array_is(self, a, b):
        self.assertIsNot(a, None)
        self.assertIsNot(b, None)
        self.assertIs(a, b)


class TestArray(Common, ants.tests.TestCase):
    def setUp(self):
        self.arr = np.arange(4).reshape(2, 2)

    def transpose_array(self, axes=None):
        tar = np.transpose(self.arr, axes=axes)
        res = transpose(self.arr, axes=axes)

        self.assert_array_is(res.base, self.arr.base)
        self.assertArrayEqual(res, tar)

    def test_array_no_axes(self):
        self.transpose_array()

    def test_array_with_axes(self):
        axes = (1, 0)
        self.transpose_array(axes)


class TestMaskedArray(Common, ants.tests.TestCase):
    def setUp(self):
        self.arr = np.ma.arange(4).reshape(2, 2)
        mask = [[True, False], [False, True]]
        self.arr.mask = mask

    def transpose_array(self, axes=None):
        res = transpose(self.arr, axes=axes)

        tar_data = np.transpose(self.arr.data, axes=axes)
        tar_mask = np.transpose(np.ma.getmaskarray(self.arr), axes=axes)
        tar = np.ma.array(tar_data, mask=tar_mask)

        self.assert_array_is(res.data.base, self.arr.data.base)
        if np.ma.is_masked(self.arr):
            self.assert_array_is(res.mask.base, self.arr.mask.base)
        self.assertMaskedArrayEqual(res, tar)

    def test_no_axes(self):
        self.transpose_array()

    def test_with_axes(self):
        axes = (1, 0)
        self.transpose_array(axes)

    def test_mask_false(self):
        # Ensure that we handle case where mask=False
        self.arr = np.ma.array(self.arr.data)
        self.transpose_array()

    @unittest.expectedFailure
    def test_numpy_bug_present(self):
        # When dealing with masked arrays, a transpose returns a copy of the
        # mask rather than a view.
        # see https://github.com/numpy/numpy/issues/7483
        # When this passes, we can remove our transpose function.
        arr2 = self.arr.transpose()
        # The following modifications to the array expose the problems with
        # the relationship between array and mask.
        arr2[:] = np.ma.masked
        arr2[0, 0] = 50
        self.assertTrue(self.arr.mask.all())


if __name__ == "__main__":
    ants.tests.main()

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import ants.tests
import numpy as np
from ants.utils.ndarray import merge_array


class Test_increasing(ants.tests.TestCase):
    def setUp(self):
        self.a = np.arange(5)
        self.b = np.arange(3, 10)

    def test_overlapping_array1_lt_array2(self):
        res = merge_array(self.a, self.b)
        tar = np.arange(10)
        self.assertArrayEqual(tar, res)

    def test_overlapping_array1_gt_array2(self):
        res = merge_array(self.b, self.a)
        tar = np.arange(10)
        self.assertArrayEqual(tar, res)

    def test_non_overlapping(self):
        b = np.arange(10, 12)
        res = merge_array(b, self.a)
        tar = np.array([0, 1, 2, 3, 4, 10, 11])
        self.assertArrayEqual(tar, res)

    def test_total_overlap_array1_in_array2(self):
        b = np.arange(-3, 5)
        res = merge_array(self.a, b)
        tar = b
        self.assertArrayEqual(tar, res)

    def test_total_overlap_array2_in_array1(self):
        a = np.arange(2, 11)
        res = merge_array(a, self.b)
        tar = a
        self.assertArrayEqual(tar, res)

    def test_diff_dtype(self):
        # Ensure that differing dtypes does not prohibit the merging of
        # arrays.  Type promotion and truncation should make it insensitive.
        self.b = self.b.astype("float64")
        res = merge_array(self.a, self.b)
        tar = np.arange(10)
        self.assertArrayEqual(res, tar)
        self.assertEqual(res.dtype, np.float64)


class Test_decresing(ants.tests.TestCase):
    def setUp(self):
        self.a = np.arange(4, -1, -1)
        self.b = np.arange(9, 2, -1)

    def test_overlapping_array1_lt_array2(self):
        res = merge_array(self.a, self.b)
        tar = np.arange(9, -1, -1)
        self.assertArrayEqual(tar, res)

    def test_overlapping_array1_gt_array2(self):
        res = merge_array(self.b, self.a)
        tar = np.arange(9, -1, -1)
        self.assertArrayEqual(tar, res)

    def test_non_overlapping(self):
        b = np.arange(11, 9, -1)
        res = merge_array(b, self.a)
        tar = np.array([11, 10, 4, 3, 2, 1, 0])
        self.assertArrayEqual(tar, res)

    def test_total_overlap_array1_in_array2(self):
        b = np.arange(4, -4, -1)
        res = merge_array(self.a, b)
        tar = b
        self.assertArrayEqual(tar, res)

    def test_total_overlap_array2_in_array1(self):
        a = np.arange(10, 1, -1)
        res = merge_array(a, self.b)
        tar = a
        self.assertArrayEqual(tar, res)


class TestExceptions(ants.tests.TestCase):
    def test_opposite_direction(self):
        a = np.arange(1, 5)
        b = np.arange(10, 1, -1)
        msg = (
            "Currently, arrays must be of the same direction to be "
            "considered compatible"
        )
        with self.assertRaisesRegex(ValueError, msg):
            merge_array(a, b)

    def test_non_monatonic(self):
        a = np.array([1, 2, 3, 2])
        b = np.arange(3, 7)
        msg = (
            "Arrays must be strictly monotonically increasing or " "decreasing in value"
        )
        with self.assertRaisesRegex(ValueError, msg):
            merge_array(a, b)

    def test_incompatible_arrays(self):
        a = np.array([1, 2, 3, 4.5])
        b = np.arange(3, 10)
        msg = "Arrays are not compatible for merging"
        with self.assertRaisesRegex(ValueError, msg):
            merge_array(a, b)


if __name__ == "__main__":
    ants.tests.main()

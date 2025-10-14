# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.utils.ndarray import group_indices


class TestAll(ants.tests.TestCase):
    def test_single_slice(self):
        arr = np.array([1, 2, 3, 4])
        res = group_indices(arr)
        tar = [slice(1, 5)]
        self.assertEqual(res, tar)

    def test_multi_slice(self):
        arr = np.array([1, 2, 4, 5])
        res = group_indices(arr)
        tar = [slice(1, 3), slice(4, 6)]
        self.assertEqual(res, tar)

    def test_multi_slice_single_length(self):
        arr = np.array([1, 3, 5, 7])
        res = group_indices(arr)
        tar = [slice(1, 2), slice(3, 4), slice(5, 6), slice(7, 8)]
        self.assertEqual(res, tar)

    def test_single_slice_single_length(self):
        arr = np.array([1])
        res = group_indices(arr)
        tar = [slice(1, 2)]
        self.assertEqual(res, tar)


if __name__ == "__main__":
    ants.tests.main()

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.decomposition import MosaicBySplit


class TestAll(ants.tests.TestCase):
    def test_suitable_sliceable(self):
        arr = np.array([[1, 2], [3, 4]])
        splitter = MosaicBySplit(arr, (1, 2))
        target = [np.array([[1], [3]]), np.array([[2], [4]])]

        # Ensure that our generator factory works by calling more than once.
        for generator in range(2):
            slices = splitter()
            for slce, tar in zip(slices, target):
                self.assertTrue((slce == tar).all())

    def test_unsuitable_sliceable_noshape(self):
        # Providing an object with no shape
        arr = [[1, 2], [3, 4]]
        splitter = MosaicBySplit(arr, (1, 2))
        slices = splitter()
        msg = "'list' object has no attribute 'shape'"
        with self.assertRaisesRegex(AttributeError, msg):
            list(slices)


if __name__ == "__main__":
    ants.tests.main()

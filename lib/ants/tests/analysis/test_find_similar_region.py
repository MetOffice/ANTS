# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.analysis import find_similar_region


class TestValues(ants.tests.TestCase):
    def test_standard_neighbourhood(self):
        arr = np.array([[1, 0, 1, 0], [0, 0, 1, 1], [0, 1, 0, 0]])
        visited = find_similar_region(arr, (1, 2))
        tar = [[1, 0, 100, 0], [0, 0, 100, 100], [0, 1, 0, 0]]
        # Easier to visually check the result in this way rather than with
        # indices.
        arr[visited] = 100
        self.assertArrayEqual(arr, tar)

    def test_extended_neighbourhood(self):
        arr = np.array([[1, 0, 1, 0], [0, 0, 1, 1], [0, 1, 0, 0]])
        # Easier to visually check the result in this way rather than with
        # indices.
        visited = find_similar_region(arr, (1, 2), extended_neighbourhood=True)
        tar = [[1, 0, 100, 0], [0, 0, 100, 100], [0, 100, 0, 0]]
        arr[visited] = 100
        self.assertArrayEqual(arr, tar)

    def test_wraparound(self):
        arr = np.array([[1, 0, 1, 0], [1, 0, 1, 1], [0, 1, 0, 0]])
        visited = find_similar_region(arr, (1, 2), wraparound=True)
        tar = [[100, 0, 100, 0], [100, 0, 100, 100], [0, 1, 0, 0]]
        arr[visited] = 100
        self.assertArrayEqual(arr, tar)


if __name__ == "__main__":
    ants.tests.main()

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import warnings

import ants.tests
import numpy as np
from ants.analysis import find_small_feature_seed_points


class TestLandFiltering(ants.tests.TestCase):
    def test_size_2_no_moore_no_wrap_land(self):
        array = np.zeros((7, 7))
        array[1, 1] = 1
        array[3, 1:5] = 1
        array[6, 3] = 1
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            seeds = find_small_feature_seed_points(array, 2, True, False, False)
        reference_seeds = [[6, 3], [1, 1]]
        self.assertArrayEqual(seeds, reference_seeds)

    def test_size_2_use_moore_no_wrap_land(self):
        array = np.zeros((10, 10))
        array[1, 1] = 1
        array[2, 2] = 1
        array[5:7, 5:7] = 1
        array[4, 4] = 1
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            seeds = find_small_feature_seed_points(array, 2, True, True, False)
        reference_seeds = []
        self.assertArrayEqual(seeds, reference_seeds)

    def test_size_3_no_moore_use_wrap_land(self):
        array = np.zeros((5, 5))
        array[0, 0] = 1
        array[0, -1] = 1
        array[3:5, 3:5] = 1
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            seeds = find_small_feature_seed_points(array, 3, True, False, True)
        reference_seeds = [[0, 4]]
        self.assertArrayEqual(seeds, reference_seeds)


class TestSeaFiltering(ants.tests.TestCase):
    def test_size_2_no_moore_no_wrap_sea(self):
        array = np.ones((7, 7))
        array[1, 1] = 0
        array[3, 1:5] = 0
        array[6, 3] = 0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            seeds = find_small_feature_seed_points(array, 2, False, False, False)
        reference_seeds = [[6, 3], [1, 1]]
        self.assertArrayEqual(seeds, reference_seeds)

    def test_size_2_use_moore_no_wrap_sea(self):
        array = np.ones((10, 10))
        array[1, 1] = 0
        array[2, 2] = 0
        array[5:7, 5:7] = 0
        array[4, 4] = 0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            seeds = find_small_feature_seed_points(array, 2, False, True, False)
        reference_seeds = []
        self.assertArrayEqual(seeds, reference_seeds)

    def test_size_3_no_moore_use_wrap_sea(self):
        array = np.ones((5, 5))
        array[0, 0] = 0
        array[0, -1] = 0
        array[3:5, 3:5] = 0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            seeds = find_small_feature_seed_points(array, 3, False, False, True)
        reference_seeds = [[0, 4]]
        self.assertArrayEqual(seeds, reference_seeds)


class TestWarning(ants.tests.TestCase):
    def test_warning(self):
        message = (
            "This function does not appear to be used, and hence has been "
            r"deprecated.  Please contact miao\@metoffice\.gov\.uk if you do "
            r"require this function, and we can discuss options \(potentially "
            r"including keeping this function and removing the deprecation\)."
        )

        with self.assertRaisesRegex(FutureWarning, message):
            find_small_feature_seed_points(np.ones((2, 2)), 3, False, False, True)

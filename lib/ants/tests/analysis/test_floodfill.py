# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.analysis import flood_fill, floodfill
from ants.exceptions import FloodfillError


class TestValues(ants.tests.TestCase):
    def testall(self):
        # Ensure that the array that is returned has the flood fill applied to
        # it.
        array = np.ones((5, 4))
        array[1:3, 1:3] = 10

        target = array.copy()
        target[target == 10] = 5

        flood_fill(array, (2, 2), 5)
        self.assertArrayEqual(array, target)

    def test_nofill(self):
        # Raise a suitable exception where the starting location does not
        # appear to require filling (i.e. already has the fillvalue).
        array = np.ones((5, 4))
        array[2, 2] = 5
        message = "The value at location 2x2 already has this fill value."
        with self.assertRaisesRegex(FloodfillError, message):
            flood_fill(array, (2, 2), 5)

    def test_1Dfill_error(self):
        # Raise a suitable exception when a 1D array is passed in for filling.
        array = np.ones((5))
        message = "The provided array should be 2D but that provided is 1D"
        with self.assertRaisesRegex(ValueError, message):
            flood_fill(array, (0, 0), 5)

    def test_no_wrap(self):
        # Ensure that wraparound filling doesn't happen when it shouldn't
        array = np.ones((5, 5))
        array[:, 2] = 10

        target = array.copy()
        target[:, 0:2] = 5

        flood_fill(array, (0, 0), 5, wraparound=False)
        self.assertArrayEqual(array, target)

    def test_wraparound(self):
        # Ensure that wraparound works when it should
        array = np.ones((5, 5))
        array[:, 2] = 10

        target = np.ones((5, 5)) * 5
        target[:, 2] = 10

        flood_fill(array, (0, 0), 5, wraparound=True)
        self.assertArrayEqual(array, target)

    def test_non_extended_neighbourhood(self):
        # Protect non-extended neighbourhood behaviour
        array = np.ones((5, 4))
        array[1:3, 1:3] = 10
        array[0, 0] = 10

        target = array.copy()
        target[1:3, 1:3] = 5

        flood_fill(array, (2, 2), 5, extended_neighbourhood=False)
        self.assertArrayEqual(array, target)

    def test_extended_neighbourhood(self):
        # Ensure extended neighbourhood works
        array = np.ones((5, 4))
        array[1:3, 1:3] = 10
        array[0, 0] = 10

        target = array.copy()
        target[1:3, 1:3] = 5
        target[0, 0] = 5

        flood_fill(array, (2, 2), 5, extended_neighbourhood=True)
        self.assertArrayEqual(array, target)

    def test_wraparound_extended(self):
        # Ensure extended neighbourhood works with wraparound
        array = np.ones((5, 4))
        array[0:2, 0:2] = 10
        array[2, -1] = 10

        target = array.copy()
        target[0:2, 0:2] = 5
        target[2, -1] = 5

        flood_fill(array, (0, 0), 5, extended_neighbourhood=True, wraparound=True)
        self.assertArrayEqual(array, target)

    def test_deprecation_warning(self):
        # Test that calling the deprecated function floodfill will raise a
        # FutureWarning
        array = np.ones(5)
        message = (
            "ants.analysis.floodfill has been deprecated. Please use "
            "ants.analysis.flood_fill instead."
        )

        with self.assertRaisesRegex(FutureWarning, message):
            floodfill(array, (0, 0), 5)

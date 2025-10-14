# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.utils.coord import relaxed_equality


class TestAll(ants.tests.TestCase):
    def setUp(self):
        bounds = np.array([[-90.0, -45.0], [-45.0, 45.0], [45.0, 90.0]])
        self.coord1 = iris.coords.AuxCoord(
            [-90, 0, 90], bounds=bounds, standard_name="latitude"
        )

    def test_tolerant_bounds(self):
        coord2 = self.coord1.copy()
        bounds2 = coord2.bounds.copy()
        bounds2 = bounds2 + 1e-6
        coord2.bounds = bounds2

        self.assertTrue(relaxed_equality(self.coord1, coord2))

    def test_unequal_bounds(self):
        coord2 = self.coord1.copy()
        bounds2 = coord2.bounds.copy()
        bounds2 = bounds2 + 1e-3
        coord2.bounds = bounds2

        self.assertFalse(relaxed_equality(self.coord1, coord2))

    def test_different_attribute_values(self):
        coord2 = self.coord1.copy()
        self.coord1.attributes["A"] = "a"
        coord2.attributes["A"] = "b"
        self.assertFalse(relaxed_equality(self.coord1, coord2))

    def test_different_attribute_keys(self):
        coord2 = self.coord1.copy()
        self.coord1.attributes["A"] = "a"
        coord2.attributes["B"] = "a"
        self.assertFalse(relaxed_equality(self.coord1, coord2))

    def test_guess_missing_bounds(self):
        # Attempt to guess bounds when one is missing.
        coord2 = self.coord1.copy()
        coord2.bounds = None
        self.assertTrue(relaxed_equality(self.coord1, coord2))

    def test_missing_bounds(self):
        # Ensure we don't guess bounds when we don't need to (both missing).
        self.coord1.bounds = None
        coord2 = self.coord1.copy()
        with mock.patch("ants.utils.coord.guess_bounds") as patched_guess:
            self.assertTrue(relaxed_equality(self.coord1, coord2))
        self.assertFalse(patched_guess.called)
        self.assertFalse(self.coord1.has_bounds())

    def test_different_var_names(self):
        coord2 = self.coord1.copy()
        self.coord1.var_name = "varname1"
        coord2.var_name = "varname2"
        self.assertTrue(relaxed_equality(self.coord1, coord2))

    def test_unequal_lengths(self):
        coord2 = self.coord1[0:-1]
        self.assertFalse(relaxed_equality(self.coord1, coord2))


if __name__ == "__main__":
    ants.tests.main()

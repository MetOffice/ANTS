# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.utils._dask import _is_masked_array


class TestIsMaskedArray(ants.tests.TestCase):
    def setUp(self):
        self.unmasked_cube = ants.tests.stock.geodetic((3, 2))
        self.masked_cube = ants.tests.stock.geodetic((3, 2))
        self.masked_cube.data = np.ma.array(self.masked_cube.data)
        self.masked_cube.data[:, 0] = np.ma.masked
        self.masked_cube.attributes["emission_type"] = "2"

    def test_realised_masked_array(self):
        self.assertTrue(np.ma.isMaskedArray(self.masked_cube.data))
        self.assertFalse(self.masked_cube.has_lazy_data())
        self.assertIsInstance(self.masked_cube.data, np.ma.MaskedArray)

    @ants.tests.enable_all_lazy_data
    def test_lazy_masked_array(self):
        self.assertIsInstance(self.masked_cube.data, np.ma.MaskedArray)
        masked_deferred_cube = ants.utils.cube.defer_cube(self.masked_cube)
        self.assertTrue(
            masked_deferred_cube.has_lazy_data(), msg="Function expected lazy data"
        )
        self.assertTrue(_is_masked_array(masked_deferred_cube.core_data()))
        self.assertTrue(
            masked_deferred_cube.has_lazy_data(), msg="Lazy data unexpectedly realised"
        )

    def test_realised_unmasked_array(self):
        self.assertIsInstance(self.unmasked_cube.data, np.ndarray)
        self.assertFalse(self.unmasked_cube.has_lazy_data())
        self.assertFalse(_is_masked_array(self.unmasked_cube.data))

    @ants.tests.enable_all_lazy_data
    def test_lazy_unmasked_array(self):
        self.assertIsInstance(self.unmasked_cube.data, np.ndarray)
        deferred_unmasked_cube = ants.utils.cube.defer_cube(self.unmasked_cube)
        self.assertTrue(
            deferred_unmasked_cube.has_lazy_data(), msg="Function expected lazy data"
        )
        self.assertFalse(_is_masked_array(deferred_unmasked_cube.core_data()))
        self.assertTrue(
            deferred_unmasked_cube.has_lazy_data(),
            msg="Lazy data unexpectedly realised",
        )

    def test_masked_cube_of_length_one(self):
        test_cube = ants.tests.stock.geodetic((1, 1))
        test_cube.data = np.ma.array(test_cube.data)
        test_cube.data[:, 0] = np.ma.masked
        test_cube.attributes["emission_type"] = "2"
        lazy_test_cube = ants.utils.cube.defer_cube(test_cube)
        self.assertTrue(_is_masked_array(lazy_test_cube.core_data()))

    def test_unmasked_cube_of_length_one(self):
        test_cube = ants.tests.stock.geodetic((1, 1))
        test_cube.data = np.ma.array(test_cube.data)
        test_cube.attributes["emission_type"] = "2"
        lazy_test_cube = ants.utils.cube.defer_cube(test_cube)
        self.assertFalse(_is_masked_array(lazy_test_cube.core_data()))

    def test_masked_cube_of_three(self):
        test_cube = ants.tests.stock.geodetic((1, 23, 45))
        test_cube.data = np.ma.array(test_cube.data)
        test_cube.data[:, 0] = np.ma.masked
        test_cube.attributes["emission_type"] = "2"
        lazy_test_cube = ants.utils.cube.defer_cube(test_cube)
        self.assertTrue(_is_masked_array(lazy_test_cube.core_data()))


if __name__ == "__main__":
    ants.tests.main()

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import numpy as np
from ants.analysis import make_consistent_with_lsm


class TestRegular(ants.tests.TestCase):
    def setUp(self):
        self.source = ants.tests.stock.geodetic((2, 2))
        self.lsm = ants.tests.stock.geodetic((2, 2))
        self.lsm.data = self.lsm.data.astype("bool")

    @mock.patch("ants.analysis.UMSpiralSearch")
    def test_default_filler_called(self, patch_fill):
        make_consistent_with_lsm(self.source, self.lsm, False)
        patch_fill.assert_called_once_with(self.source, target_mask=self.lsm)

    @mock.patch("ants.analysis.UMSpiralSearch")
    def test_filler_called(self, patch_fill):
        make_consistent_with_lsm(self.source, self.lsm, False, "spiral")
        patch_fill.assert_called_once_with(self.source, target_mask=self.lsm)

    @mock.patch("ants.analysis.UMSpiralSearch")
    def test_case_insensitive(self, patch_fill):
        make_consistent_with_lsm(self.source, self.lsm, False, "Spiral")
        patch_fill.assert_called_once_with(self.source, target_mask=self.lsm)

    @mock.patch("ants.utils.cube.guess_horizontal_bounds")
    def test_guess_bounds(self, patch_guess):
        make_consistent_with_lsm(self.source, self.lsm, False)
        patch_guess.assert_has_calls([mock.call(self.lsm), mock.call(self.source)])
        self.assertEqual(2, patch_guess.call_count)

    def test_invalid_search_method(self):
        with self.assertRaisesRegex(RuntimeError, "Unknown search method: banana"):
            make_consistent_with_lsm(self.source, self.lsm, False, "banana")


class TestKDTree(ants.tests.TestCase):
    def setUp(self):
        self.source = ants.tests.stock.geodetic((2, 2))
        self.lsm = ants.tests.stock.geodetic((2, 2))
        self.lsm.data = self.lsm.data.astype("bool")

    @mock.patch("ants.analysis.KDTreeFill")
    def test_filler_called(self, patch_fill):
        make_consistent_with_lsm(self.source, self.lsm, False, "kdtree")
        patch_fill.assert_called_once_with(self.source, target_mask=self.lsm)

    @mock.patch("ants.analysis.KDTreeFill")
    def test_case_insensitive(self, patch_fill):
        make_consistent_with_lsm(self.source, self.lsm, False, "KDTree")
        patch_fill.assert_called_once_with(self.source, target_mask=self.lsm)

    @mock.patch("ants.utils.cube.guess_horizontal_bounds")
    def test_guess_bounds(self, patch_guess):
        make_consistent_with_lsm(self.source, self.lsm, False)
        patch_guess.assert_has_calls([mock.call(self.lsm), mock.call(self.source)])
        self.assertEqual(2, patch_guess.call_count)


class TestLSMWarning(ants.tests.TestCase):
    def setUp(self):
        self.source = ants.tests.stock.geodetic((2, 2))
        self.lsm = ants.tests.stock.geodetic((2, 2))
        self.lsm.data = self.lsm.data.astype("bool")

    def test_no_warning(self):
        with mock.patch("warnings.warn") as mock_warn:
            make_consistent_with_lsm(self.source, self.lsm, False)
        self.assertEqual(mock_warn.call_count, 0)

    def test_masked_value(self):
        self.lsm.data = np.ma.masked_array(self.lsm.data, mask=[[0, 1], [0, 0]])
        with mock.patch("warnings.warn") as mock_warn:
            make_consistent_with_lsm(self.source, self.lsm, False)
        self.assertEqual(mock_warn.call_count, 1)

    def test_non_bool_value(self):
        self.lsm.data = np.array([[0, 1], [2, 0]])
        with mock.patch("warnings.warn") as mock_warn:
            make_consistent_with_lsm(self.source, self.lsm, False)
        self.assertEqual(mock_warn.call_count, 1)

    def test_non_bool_value_between_0_and_1(self):
        self.lsm.data = np.array([[0, 1], [0.5, 0]])
        with mock.patch("warnings.warn") as mock_warn:
            make_consistent_with_lsm(self.source, self.lsm, False)
        self.assertEqual(mock_warn.call_count, 1)

    def test_masked_value_and_non_bool_value(self):
        self.lsm.data = np.array([[0, 1], [2, 0]])
        self.lsm.data = np.ma.masked_array(self.lsm.data, mask=[[0, 1], [0, 0]])
        with mock.patch("warnings.warn") as mock_warn:
            make_consistent_with_lsm(self.source, self.lsm, False)
        self.assertEqual(mock_warn.call_count, 2)


class TestErrorsRaised(ants.tests.TestCase):
    def setUp(self):
        self.source = ants.tests.stock.geodetic((2, 2))
        self.lsm = ants.tests.stock.geodetic((2, 2))
        self.lsm.data = self.lsm.data.astype("bool")

        self.ugrid_source = ants.tests.stock.geodetic((2, 2))
        self.ugrid_source.attributes["Conventions"] = "UGRID"
        self.ugrid_lsm = ants.tests.stock.geodetic((2, 2))
        self.ugrid_lsm.data = self.lsm.data.astype("bool")
        self.ugrid_lsm.attributes["Conventions"] = "UGRID"

    def test_error_raised_with_ugrid_lsm(self):
        """Tests that a ValueError will be thrown is make_constistent_with_lsm is
        given a ugrid lsm."""
        with self.assertRaisesRegex(
            ValueError, "ANTS doesn't support ugrid data. Please use UG-ANTS instead."
        ):
            make_consistent_with_lsm(self.source, self.ugrid_lsm, False)

    def test_error_raised_with_ugrid_sources(self):
        """Tests that a ValueError will be thrown is make_constistent_with_lsm is
        given a ugrid lsm."""
        with self.assertRaisesRegex(
            ValueError, "ANTS doesn't support ugrid data. Please use UG-ANTS instead."
        ):
            make_consistent_with_lsm(self.ugrid_source, self.lsm, False)

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
from ants.regrid import _create_horizontal_regrid_scheme_instance
from ants.regrid.esmf import ConservativeESMF
from ants.regrid.rectilinear import AreaWeighted, Linear, TwoStage
from iris.analysis import Nearest


class TestLinear(ants.tests.TestCase):
    def test_default_extrapolation(self):
        """Test that the Linear regrid scheme is instantiated,
        and the default extrapolation mode has been set."""
        expected_extrapolation = Linear()._extrapolation
        scheme = _create_horizontal_regrid_scheme_instance("Linear", None)
        self.assertIsInstance(scheme, Linear)
        self.assertEqual(expected_extrapolation, scheme._extrapolation)

    def test_non_default_extrapolation(self):
        """Test that the Linear regrid scheme is instantiated,
        and a non-default extrapolation mode has been set."""
        expected_extrapolation = "mask"
        scheme = _create_horizontal_regrid_scheme_instance(
            "Linear", extrapolation_mode="mask"
        )
        self.assertIsInstance(scheme, Linear)
        self.assertEqual(expected_extrapolation, scheme._extrapolation)


class TestNearest(ants.tests.TestCase):
    def test_default_extrapolation(self):
        """Test that the Nearest regrid scheme is instantiated,
        and the default extrapolation mode has been set."""
        expected_extrapolation = Nearest().extrapolation_mode
        scheme = _create_horizontal_regrid_scheme_instance("Nearest", None)
        self.assertIsInstance(scheme, Nearest)
        self.assertEqual(expected_extrapolation, scheme.extrapolation_mode)

    def test_non_default_extrapolation(self):
        """Test that the Nearest regrid scheme is instantiated,
        and a non-default extrapolation mode has been set."""
        expected_extrapolation = "mask"
        scheme = _create_horizontal_regrid_scheme_instance(
            "Nearest", extrapolation_mode="mask"
        )
        self.assertIsInstance(scheme, Nearest)
        self.assertEqual(expected_extrapolation, scheme.extrapolation_mode)


class TestAreaWeighted(ants.tests.TestCase):
    def test_no_extrapolation(self):
        """Test that the AreaWeighted regrid scheme is instantiated.
        No extrapolation mode is required for AreaWeighted."""
        scheme = _create_horizontal_regrid_scheme_instance("AreaWeighted", None)
        self.assertIsInstance(scheme, AreaWeighted)

    def test_non_permitted_extrapolation(self):
        """Test that an error is raised when attempting to pass an extrapolation mode
        to the AreaWeighted regrid scheme."""
        with self.assertRaisesRegex(
            TypeError, "got an unexpected keyword argument 'extrapolation_mode'"
        ):
            _create_horizontal_regrid_scheme_instance("AreaWeighted", "nan")


class TestTwoStage(ants.tests.TestCase):
    def test_no_extrapolation(self):
        """Test that the TwoStage regrid scheme is instantiated.
        No extrapolation mode is required for TwoStage."""
        scheme = _create_horizontal_regrid_scheme_instance("TwoStage", None)
        self.assertIsInstance(scheme, TwoStage)

    def test_non_permitted_extrapolation(self):
        """Test that an error is raised when attempting to pass an extrapolation mode
        to the TwoStage regrid scheme."""
        with self.assertRaisesRegex(
            TypeError, "got an unexpected keyword argument 'extrapolation_mode'"
        ):
            _create_horizontal_regrid_scheme_instance("TwoStage", "nan")


class TestConservativeESMF(ants.tests.TestCase):
    def test_no_extrapolation(self):
        """Test that the ConservativeESMF regrid scheme is instantiated.
        No extrapolation mode is required for ConservativeESMF."""
        scheme = _create_horizontal_regrid_scheme_instance("ConservativeESMF", None)
        self.assertIsInstance(scheme, ConservativeESMF)

    def test_non_permitted_extrapolation(self):
        """Test that an error is raised when attempting to pass an extrapolation mode
        to the ConservativeESMF regrid scheme."""
        with self.assertRaisesRegex(
            TypeError, "got an unexpected keyword argument 'extrapolation_mode'"
        ):
            _create_horizontal_regrid_scheme_instance("ConservativeESMF", "nan")

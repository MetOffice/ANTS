# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
from ants.regrid import _create_vertical_regrid_scheme_instance
from ants.regrid.interpolation import Conservative, Linear, Nearest


class TestLinear(ants.tests.TestCase):
    def test_default_extrapolation(self):
        """Test that the Linear regrid scheme is instantiated,
        and the default extrapolation mode has been set."""
        expected_extrapolation = Linear()._extrapolation
        scheme = _create_vertical_regrid_scheme_instance("Linear", None)
        self.assertIsInstance(scheme, Linear)
        self.assertEqual(expected_extrapolation, scheme._extrapolation)

    def test_non_default_extrapolation(self):
        """Test that the Linear regrid scheme is instantiated,
        and a non-default extrapolation mode has been set."""
        expected_extrapolation = "nearest"
        scheme = _create_vertical_regrid_scheme_instance(
            "Linear", extrapolation_mode="nearest"
        )
        self.assertIsInstance(scheme, Linear)
        self.assertEqual(expected_extrapolation, scheme._extrapolation)


class TestNearest(ants.tests.TestCase):
    def test_default_extrapolation(self):
        """Test that the Nearest regrid scheme is instantiated,
        and the default extrapolation mode has been set."""
        expected_extrapolation = Nearest()._extrapolation
        scheme = _create_vertical_regrid_scheme_instance("Nearest", None)
        self.assertIsInstance(scheme, Nearest)
        self.assertEqual(expected_extrapolation, scheme._extrapolation)

    def test_non_default_extrapolation(self):
        """Test that the Nearest regrid scheme is instantiated,
        and a non-default extrapolation mode has been set."""
        expected_extrapolation = "nearest"
        scheme = _create_vertical_regrid_scheme_instance(
            "Nearest", extrapolation_mode="nearest"
        )
        self.assertIsInstance(scheme, Nearest)
        self.assertEqual(expected_extrapolation, scheme._extrapolation)


class TestConservative(ants.tests.TestCase):
    def test_no_extrapolation(self):
        """Test that the Conservative regrid scheme is instantiated.
        No extrapolation mode is required for Conservative."""
        scheme = _create_vertical_regrid_scheme_instance("Conservative", None)
        self.assertIsInstance(scheme, Conservative)

    def test_non_permitted_extrapolation(self):
        """Test that an error is raised when attempting to pass an extrapolation mode
        to the Conservative regrid scheme."""
        with self.assertRaisesRegex(
            TypeError, "got an unexpected keyword argument 'extrapolation'"
        ):
            _create_vertical_regrid_scheme_instance("Conservative", "nan")

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.config import CONFIG
from ants.regrid import GeneralRegridScheme, esmf, rectilinear
from iris.analysis import Nearest


class TestErrorMessages(ants.tests.TestCase):
    def test_no_scheme_given(self):
        source = ants.tests.stock.geodetic((2, 2))
        target = ants.tests.stock.geodetic((2, 2))
        scheme = GeneralRegridScheme()
        with self.assertRaises(AttributeError) as context:
            source.regrid(target, scheme)

            self.assertTrue(
                "At least one of horizontal \
            or vertical re-grid schemes must be provided."
                in context.exception
            )


class TestInterpolation(ants.tests.TestCase):
    def setUp(self):
        self.source = ants.tests.stock.geodetic((2, 2))
        self.target = self.source.copy()

    def test_conservative(self):
        scheme = "ants.regrid.interpolation.Conservative"
        with mock.patch(scheme) as patched_scheme:
            scheme = GeneralRegridScheme(vertical_scheme="Conservative")
            self.source.regrid(self.target, scheme)
        self.assertTrue(patched_scheme.called)

    def test_linear(self):
        scheme = "ants.regrid.interpolation.Linear"
        with mock.patch(scheme) as patched_scheme:
            scheme = GeneralRegridScheme(vertical_scheme="Linear")
            self.source.regrid(self.target, scheme)
        self.assertTrue(patched_scheme.called)

    def test_nearest(self):
        scheme = "ants.regrid.interpolation.Nearest"
        with mock.patch(scheme) as patched_scheme:
            scheme = GeneralRegridScheme(vertical_scheme="Nearest")
            self.source.regrid(self.target, scheme)
        self.assertTrue(patched_scheme.called)


class TestESMF(ants.tests.TestCase):
    @ants.tests.skip_esmpy
    def test_conservative(self):
        scheme = GeneralRegridScheme(horizontal_scheme="ConservativeESMF")
        source = ants.tests.stock.geodetic((2, 2))
        target = source.copy()
        res = source.regrid(target, scheme)
        self.assertEqual(res, target)

    def test_expected_scheme(self):
        with mock.patch("ants.regrid.esmf.ConservativeESMF") as patched_scheme:
            scheme = GeneralRegridScheme(horizontal_scheme="ConservativeESMF")
            source = ants.tests.stock.geodetic((2, 2))
            target = source.copy()
            source.regrid(target, scheme)
        self.assertTrue(patched_scheme.called)


class TestRectilinear(ants.tests.TestCase):
    def test_twostage(self):
        with mock.patch("ants.regrid.rectilinear.TwoStage") as patched_scheme:
            scheme = GeneralRegridScheme(horizontal_scheme="TwoStage")
            source = ants.tests.stock.geodetic((2, 2))
            target = source.copy()
            source.regrid(target, scheme)
        self.assertTrue(patched_scheme.called)

    def test_expected_scheme(self):
        # Ensure our Linear is used over the iris one.
        with mock.patch("ants.regrid.rectilinear.Linear") as patched_scheme:
            scheme = GeneralRegridScheme(horizontal_scheme="Linear")
            source = ants.tests.stock.geodetic((2, 2))
            target = source.copy()
            source.regrid(target, scheme)
        self.assertTrue(patched_scheme.called)


class TestIris(ants.tests.TestCase):
    def test_areaweighted(self):
        scheme = GeneralRegridScheme(horizontal_scheme="AreaWeighted")
        source = ants.tests.stock.geodetic((2, 2))
        target = source.copy()
        res = source.regrid(target, scheme)
        self.assertEqual(res, target)

    def test_expected_scheme(self):
        with mock.patch("ants.regrid.rectilinear.AreaWeighted") as patched_scheme:
            scheme = GeneralRegridScheme(horizontal_scheme="AreaWeighted")
            source = ants.tests.stock.geodetic((2, 2))
            target = source.copy()
            source.regrid(target, scheme)
        self.assertTrue(patched_scheme.called)


class TestHorizontalExtrapolationConfig(ants.tests.TestCase):
    """Tests for configuration of the horizontal extrapolation mode."""

    def test_Linear_scheme_nan_extrapolation(self):
        """Test that the 'Linear' scheme and 'nan' extrapolation mode are picked up
        from the config."""
        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "Linear",
                "extrapolation_mode": "nan",
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):
            scheme = GeneralRegridScheme()
        self.assertIsInstance(scheme._horizontal_scheme, rectilinear.Linear)
        self.assertEqual(scheme._horizontal_scheme.extrapolation_mode, "nan")

    def test_Linear_scheme_linear_extrapolation(self):
        """Test that the 'Linear' scheme and 'linear' extrapolation mode are picked up
        from the config."""
        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "Linear",
                "extrapolation_mode": "linear",
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):
            scheme = GeneralRegridScheme()
        self.assertIsInstance(scheme._horizontal_scheme, rectilinear.Linear)
        self.assertEqual(scheme._horizontal_scheme.extrapolation_mode, "linear")

    def test_Linear_scheme_default_extrapolation(self):
        """Test that when no extrapolation mode config is given, the default is used."""
        default_extrapolation_mode = rectilinear.Linear().extrapolation_mode

        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "Linear",
                "extrapolation_mode": None,
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):

            scheme = GeneralRegridScheme()
        self.assertIsInstance(scheme._horizontal_scheme, rectilinear.Linear)
        self.assertEqual(
            scheme._horizontal_scheme.extrapolation_mode, default_extrapolation_mode
        )

    def test_TwoStage_scheme_no_extrapolation(self):
        """The TwoStage regridder does not support extrapolation."""
        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "TwoStage",
                "extrapolation_mode": None,
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):
            scheme = GeneralRegridScheme()
        self.assertIsInstance(scheme._horizontal_scheme, rectilinear.TwoStage)

    def test_TwoStage_scheme_extrapolation_error(self):
        """The TwoStage regridder does not support extrapolation.

        If an extrapolation mode is given in the config, an error should be raised."""
        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "TwoStage",
                "extrapolation_mode": "nan",
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):
            with self.assertRaisesRegex(
                TypeError, "got an unexpected keyword argument 'extrapolation_mode'"
            ):
                GeneralRegridScheme()

    def test_ConservativeESMF_scheme_no_extrapolation(self):
        """The ConservativeESMF regridder does not support extrapolation."""
        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "ConservativeESMF",
                "extrapolation_mode": None,
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):
            scheme = GeneralRegridScheme()
        self.assertIsInstance(scheme._horizontal_scheme, esmf.ConservativeESMF)

    def test_ConservativeESMF_scheme_extrapolation_error(self):
        """The ConservativeESMF regridder does not support extrapolation.

        If an extrapolation mode is given in the config, an error should be raised."""
        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "ConservativeESMF",
                "extrapolation_mode": "nan",
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):
            with self.assertRaisesRegex(
                TypeError, "got an unexpected keyword argument 'extrapolation_mode'"
            ):
                GeneralRegridScheme()

    def test_Nearest_scheme_nan_extrapolation(self):
        """Test that the 'Nearest' scheme and 'nan' extrapolation mode are picked up
        from the config."""
        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "Nearest",
                "extrapolation_mode": "nan",
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):
            scheme = GeneralRegridScheme()
        self.assertIsInstance(scheme._horizontal_scheme, Nearest)
        self.assertEqual(scheme._horizontal_scheme.extrapolation_mode, "nan")

    def test_Nearest_scheme_mask_extrapolation(self):
        """Test that the 'Nearest' scheme and 'mask' extrapolation mode are picked up
        from the config."""
        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "Nearest",
                "extrapolation_mode": "mask",
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):
            scheme = GeneralRegridScheme()
        self.assertIsInstance(scheme._horizontal_scheme, Nearest)
        self.assertEqual(scheme._horizontal_scheme.extrapolation_mode, "mask")

    def test_Nearest_scheme_default_extrapolation(self):
        """Test that when no extrapolation mode config is given, the default is used."""
        default_extrapolation_mode = Nearest().extrapolation_mode

        new_config = {
            "ants_regridding_horizontal": {
                "scheme": "Nearest",
                "extrapolation_mode": None,
            }
        }
        with mock.patch.dict(CONFIG.config, new_config):

            scheme = GeneralRegridScheme()
        self.assertIsInstance(scheme._horizontal_scheme, Nearest)
        self.assertEqual(
            scheme._horizontal_scheme.extrapolation_mode, default_extrapolation_mode
        )

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import unittest.mock as mock

import ants.tests
from ants.regrid.rectilinear import AreaWeighted, Linear, TwoStage
from ants.tests.stock import simple_4d_with_hybrid_height


class TestZonalMeanTargetArea_Weighted(ants.tests.TestCase):
    def test_warning_raised_when_zonal_mean_target_called(self):
        """
        Checks a warning is raised to notify users that the target has been
        converted to a zonal mean.
        """
        source = simple_4d_with_hybrid_height(longitude=1)
        target = simple_4d_with_hybrid_height(longitude=2)
        scheme = AreaWeighted()

        with mock.patch("warnings.warn") as warn:
            regridder = scheme.regridder(source, target)
            regridder(source)

        warn.assert_called_once_with("Output converted to zonal mean.")

    def test_no_warning_raised_if_target_already_zonal_mean(self):
        """
        Checks a warning is not raised if the target is already a zonal mean.
        """
        source = simple_4d_with_hybrid_height(longitude=1)
        target = simple_4d_with_hybrid_height(longitude=1)
        scheme = AreaWeighted()

        with mock.patch("warnings.warn") as warn:
            regridder = scheme.regridder(source, target)
            regridder(source)

        warn.assert_not_called()

    def test_no_warning_raised_if_source_is_not_global_in_x(self):
        """
        Checks a warning is not raised if source is a subset (not global in x).
        """
        source = simple_4d_with_hybrid_height(longitude=2)
        source_subset = source[..., 0:1]

        target = simple_4d_with_hybrid_height(longitude=2)
        scheme = AreaWeighted()

        with mock.patch("warnings.warn") as warn:
            regridder = scheme.regridder(source_subset, target)
            regridder(source_subset)

        warn.assert_not_called()


class TestZonalMeanTargetLinear(ants.tests.TestCase):
    def test_warning_raised_when_zonal_mean_target_called(self):
        """
        Checks a warning is raised to notify users that the target has been
        converted to a zonal mean.
        """
        source = simple_4d_with_hybrid_height(longitude=1)
        target = simple_4d_with_hybrid_height(longitude=2)
        scheme = Linear()

        with mock.patch("warnings.warn") as warn:
            regridder = scheme.regridder(source, target)
            regridder(source)

        warn.assert_called_once_with("Output converted to zonal mean.")

    def test_no_warning_raised_if_target_already_zonal_mean(self):
        """
        Checks a warning is not raised if the target is already a zonal mean.
        """
        source = simple_4d_with_hybrid_height(longitude=1)
        target = simple_4d_with_hybrid_height(longitude=1)
        scheme = Linear()

        with mock.patch("warnings.warn") as warn:
            regridder = scheme.regridder(source, target)
            regridder(source)

        warn.assert_not_called()


class TestZonalMeanTargetTwoStage(ants.tests.TestCase):
    def test_warning_raised_when_zonal_mean_target_called(self):
        """
        Checks a warning is raised to notify users that the target has been
        converted to a zonal mean.
        """
        source = simple_4d_with_hybrid_height(longitude=1)
        target = simple_4d_with_hybrid_height(longitude=2)
        scheme = TwoStage()

        with mock.patch("warnings.warn") as warn:
            regridder = scheme.regridder(source, target)
            regridder(source)

        warn.assert_called_once_with("Output converted to zonal mean.")

    def test_no_warning_raised_if_target_already_zonal_mean(self):
        """
        Checks a warning is not raised if the target is already a zonal mean.
        """
        source = simple_4d_with_hybrid_height(longitude=1)
        target = simple_4d_with_hybrid_height(longitude=1)
        scheme = TwoStage()

        with mock.patch("warnings.warn") as warn:
            regridder = scheme.regridder(source, target)
            regridder(source)

        warn.assert_not_called()

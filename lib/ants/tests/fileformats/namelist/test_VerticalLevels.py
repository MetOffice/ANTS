# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.fileformats.namelist import VerticalLevels
from iris.coords import AuxCoord as AuxCoord
from iris.coords import DimCoord as DimCoord


class Common(object):
    # eta_rhos halfway between eta_thetas
    def setUp(self):
        vertical_def = {
            "z_top_of_model": 5.0,
            "first_constant_r_rho_level": 3,
            "eta_theta": [0.0, 0.1, 0.225, 0.4, 0.6, 1.0],
            "eta_rho": [0.05, 0.1625, 0.3125, 0.5, 0.8],
        }
        self.namelist_dict = {"vertlevs": vertical_def}
        self.actual = VerticalLevels(self.namelist_dict)


class Test___init___brlev(Common, ants.tests.TestCase):
    def test_calculate_blev(self):
        # Model top * eta_theta[1:]
        expected = [0.0, 0.5, 1.125, 2.0, 3.0, 5.0]
        self.assertArrayAlmostEqual(expected, self.actual._blev)

    def test_calculate_brlev(self):
        # Model top * eta rho, with first hardcoded to 0.0
        # Final value of 6.0 comes from F03, p29:
        # "For the top theta level, the upper layer boundary is a rho level
        # above which is calculated to be the same distance above as the rho
        # level below."

        expected = [0.0, 0.25, 0.8125, 1.5625, 2.5, 4.0, 6.0]
        self.assertArrayAlmostEqual(expected, self.actual._brlev)

    def test_calculate_bhlev(self):
        # See F03 appendix A for equation: C(k) = ...
        expected = [1.0, 0.4624, 0.0784, 0.0, 0.0, 0.0]
        self.assertArrayAlmostEqual(expected, self.actual._bhlev)

    def test_calculate_bhrlev(self):
        # See F03 appendix A for equation: C(k) = ...
        expected = [1.0, 0.7056, 0.2304, 0.0, 0.0, 0.0, 0.0]
        self.assertArrayAlmostEqual(expected, self.actual._bhrlev)

    def test_exception_for_wrong_array_lengths(self):
        # Truncate eta_theta to same length as eta_rho:
        self.namelist_dict["vertlevs"]["eta_theta"] = self.namelist_dict["vertlevs"][
            "eta_theta"
        ][:-1]

        with self.assertRaisesRegex(ValueError, 'Expecting "eta_theta"'):
            VerticalLevels(self.namelist_dict)


class Test_level_height(Common, ants.tests.TestCase):
    def test_coordinate(self):
        expected = AuxCoord(
            [0.0, 0.5, 1.125, 2.0, 3.0, 5.0],
            bounds=[
                [0.0, 0.25],
                [0.25, 0.8125],
                [0.8125, 1.5625],
                [1.5625, 2.5],
                [2.5, 4.0],
                [4.0, 6.0],
            ],
            var_name="level_height",
            attributes={"positive": "up"},
            units="m",
        )
        res = ants.utils.coord.relaxed_equality(expected, self.actual.level_height)
        self.assertTrue(res)

    def test_upper_bound_special_case(self):
        """Check for last upper bound (implementation is special case)"""
        expected = 6.0
        actual = self.actual.level_height.bounds[-1][-1]
        self.assertEqual(expected, actual)


class Test_model_level_number(Common, ants.tests.TestCase):
    def test_coordinate(self):
        expected = DimCoord(
            np.arange(6),
            standard_name="model_level_number",
            units="1",
            attributes={"positive": "up"},
        )
        res = ants.utils.coord.relaxed_equality(
            expected, self.actual.model_level_number
        )
        self.assertTrue(res)


class Test_sigma(Common, ants.tests.TestCase):
    def test_coordinate(self):
        expected = AuxCoord(
            [1.0, 0.4624, 0.0784, 0.0, 0.0, 0.0],
            bounds=[
                [1, 0.7056],
                [0.7056, 0.2304],
                [0.2304, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
            ],
            long_name="sigma",
            units="1",
        )
        res = ants.utils.coord.relaxed_equality(expected, self.actual.sigma)
        self.assertTrue(res)

    def test_lower_bound_special_case(self):
        """Check for first lower bound (implementation is special case)"""
        expected = 1.0
        actual = self.actual.sigma.bounds[0][0]
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    ants.tests.main()

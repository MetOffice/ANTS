# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.coord_systems import UM_SPHERE
from ants.fileformats.namelist.umgrid import _CAPGrid as CAPGrid


class DummyCAPGrid(CAPGrid):
    defaults = {"grid": {"phi_pole": 90, "lambda_pole": 0}}

    def x(self):
        pass

    def y(self):
        pass

    def attributes(self):
        pass

    def shape(self):
        pass


class Test__is_rotated(ants.tests.TestCase):
    def test_false(self):
        sample = {"grid": {"phi_pole": 90, "lambda_pole": 0}}
        grid = DummyCAPGrid(sample)
        self.assertFalse(grid._is_rotated)

    def test_true(self):
        sample = {"grid": {"phi_pole": 80, "lambda_pole": 10}}
        grid = DummyCAPGrid(sample)
        self.assertTrue(grid._is_rotated)


class Test_coord_system(ants.tests.TestCase):
    def test_not_rotated(self):
        sample = {"grid": {"phi_pole": 90, "lambda_pole": 0}}
        grid = DummyCAPGrid(sample)
        res = grid.coord_system
        self.assertEqual(res, UM_SPHERE.crs)

    def test_rotated(self):
        targ_x = mock.sentinel.lambda_pole
        targ_y = mock.sentinel.phi_pole

        sample = {"grid": {"phi_pole": targ_y, "lambda_pole": targ_x}}
        grid = DummyCAPGrid(sample)
        with mock.patch("iris.coord_systems.RotatedGeogCS") as protgeog:
            res = grid.coord_system

        protgeog.assert_called_once_with(targ_y, targ_x, ellipsoid=UM_SPHERE.crs)
        self.assertEqual(res, protgeog())


if __name__ == "__main__":
    ants.tests.main()

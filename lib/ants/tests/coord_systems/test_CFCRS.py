# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
from ants.coord_systems import CFCRS


class Common(object):
    def setUp(self):
        self.crs = iris.coord_systems.GeogCS(6e6)
        self.x_metadata = {"standard_name": "longitude", "units": "degree_east"}
        self.y_metadata = {"standard_name": "latitude", "units": "degree_north"}


class Test___init__(Common, ants.tests.TestCase):
    def test_correct_args(self):
        # Ensure that we don't fall over during correct initialisation of the
        # function.
        CFCRS(self.crs)


class Test_crs(Common, ants.tests.TestCase):
    def test_all(self):
        res_crs = CFCRS(self.crs)
        self.assertEqual(res_crs.crs, self.crs)
        self.assertIsNot(res_crs.crs, self.crs)


class Test_x(Common, ants.tests.TestCase):
    def test_geogcs(self):
        res_crs = CFCRS(self.crs)
        for key in self.x_metadata:
            self.assertEqual(getattr(res_crs.x, key), self.x_metadata[key])

    def test_rotated_geogcs(self):
        crs = iris.coord_systems.RotatedGeogCS(90, 0, ellipsoid=self.crs)
        res_crs = CFCRS(crs)
        x_metadata = {"standard_name": "grid_longitude", "units": "degrees"}
        for key in self.x_metadata:
            self.assertEqual(getattr(res_crs.x, key), x_metadata[key])

    def test_projection(self):
        crs = mock.Mock("projection")
        res_crs = CFCRS(crs)
        x_metadata = {"standard_name": "projection_x_coordinate", "units": "m"}
        for key in self.x_metadata:
            self.assertEqual(getattr(res_crs.x, key), x_metadata[key])


class Test_y(Common, ants.tests.TestCase):
    def test_geogcs(self):
        res_crs = CFCRS(self.crs)
        for key in self.y_metadata:
            self.assertEqual(getattr(res_crs.y, key), self.y_metadata[key])

    def test_rotated_geogcs(self):
        crs = iris.coord_systems.RotatedGeogCS(90, 0, ellipsoid=self.crs)
        res_crs = CFCRS(crs)
        y_metadata = {"standard_name": "grid_latitude", "units": "degrees"}
        for key in self.y_metadata:
            self.assertEqual(getattr(res_crs.y, key), y_metadata[key])

    def test_projection(self):
        crs = mock.Mock("projection")
        res_crs = CFCRS(crs)
        y_metadata = {"standard_name": "projection_y_coordinate", "units": "m"}
        for key in self.y_metadata:
            self.assertEqual(getattr(res_crs.y, key), y_metadata[key])


class Test___str__(Common, ants.tests.TestCase):
    def test_all(self):
        res_crs = CFCRS(self.crs)
        res = res_crs.__str__()
        tar = (
            "GeogCS(6000000.0), "
            "x_metadata=AxisMeta(standard_name='longitude', "
            "units='degree_east'), "
            "y_metadata=AxisMeta(standard_name='latitude', "
            "units='degree_north')"
        )
        self.assertEqual(res, tar)


class Test___repr__(Common, ants.tests.TestCase):
    def test_all(self):
        res_crs = CFCRS(self.crs)
        res = res_crs.__repr__()
        tar = "GeogCS(6000000.0)"
        self.assertEqual(res, tar)


if __name__ == "__main__":
    ants.tests.main()

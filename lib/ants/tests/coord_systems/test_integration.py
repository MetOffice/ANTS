# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.coord_systems as coord_systems
import ants.tests
import iris
from iris.coord_systems import OSGB, GeogCS


class TestANTSCoordinateSystems(ants.tests.TestCase):
    def test_wgs84_as_umsphere(self):
        # Coordinate systems considered equivalent.
        wgs84 = coord_systems.WGS84_GEODETIC.crs
        wgs84_v2 = GeogCS(semi_major_axis=6378137.0, semi_minor_axis=6356752.314245179)
        res_crs = wgs84.as_ants_crs()
        self.assertEqual(res_crs, coord_systems.UM_SPHERE.crs)

        res_crs = wgs84_v2.as_ants_crs()
        self.assertEqual(res_crs, coord_systems.UM_SPHERE.crs)

    def test_osgb_as_transverse_mercator(self):
        # Ensure that OSGB returns the more general Transverse Mercator in
        # order to remove projection limits in its usage.
        osgb = OSGB()
        res_crs = osgb.as_ants_crs()
        self.assertEqual(res_crs, coord_systems.OSGB.crs)
        self.assertEqual(type(res_crs), iris.coord_systems.TransverseMercator)

    def test_identical_return(self):
        # Coordinate systems with no equivalent
        crs = GeogCS(6000000)
        res_crs = crs.as_ants_crs()
        self.assertIs(res_crs, crs)

    def test_rotated_pole_treatment_as_unrotated(self):
        crs = iris.coord_systems.RotatedGeogCS(
            90, 180, ellipsoid=coord_systems.UM_SPHERE.crs
        )
        res_crs = crs.as_ants_crs()
        self.assertIsInstance(res_crs, coord_systems.UM_SPHERE.crs.__class__)

    def test_rotated_pole_treatment_unchanged(self):
        crs = iris.coord_systems.RotatedGeogCS(
            30, 180, ellipsoid=coord_systems.UM_SPHERE.crs
        )
        res_crs = crs.as_ants_crs()
        self.assertIs(res_crs, crs)

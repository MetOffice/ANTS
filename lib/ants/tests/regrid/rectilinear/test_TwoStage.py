# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
from ants.coord_systems import UM_SPHERE
from ants.regrid.rectilinear import TwoStage, compare_coordinate_reference_systems
from iris.fileformats.pp import EARTH_RADIUS

# Iris CRS test objects
GEOGCS = iris.coord_systems.GeogCS(EARTH_RADIUS)
ROTATED_GEOGCS_MAINTAIN_ROTATED = iris.coord_systems.RotatedGeogCS(
    grid_north_pole_latitude=30, grid_north_pole_longitude=30
)
ROTATED_GEOGCS_TREAT_AS_UNROTATED = iris.coord_systems.RotatedGeogCS(
    grid_north_pole_latitude=90,
    grid_north_pole_longitude=180,
    ellipsoid=iris.coord_systems.GeogCS(6371229.0),
)
TRANSVERSE_MERCATOR = iris.coord_systems.TransverseMercator(
    latitude_of_projection_origin=49.0,
    longitude_of_central_meridian=-2.0,
    false_easting=400000.0,
    false_northing=-100000.0,
    scale_factor_at_central_meridian=0.9996012717,
    ellipsoid=iris.coord_systems.GeogCS(
        semi_major_axis=6377563.396, semi_minor_axis=6356256.909
    ),
)
OSGB = iris.coord_systems.OSGB()
WGS84_GEODETIC = iris.coord_systems.GeogCS(
    semi_major_axis=6378137.0, semi_minor_axis=6356752.314245179
)


class TestCompareCoordinateReferenceSystems(ants.tests.TestCase):
    # only assert True where the CRSs are different, and therefore
    # a two stage process is required -
    # further information can be found in ants.coord_systems.py
    def setUp(self) -> None:
        self.geogcs = GEOGCS
        self.rotated_geogcs_maintain_rotated = ROTATED_GEOGCS_MAINTAIN_ROTATED
        self.rotated_geogcs_treat_as_unrotated = ROTATED_GEOGCS_TREAT_AS_UNROTATED
        self.transverse_mercator = TRANSVERSE_MERCATOR
        self.OSGB = OSGB
        self.wgs_geodetic = WGS84_GEODETIC
        return super().setUp()

    def test_coord_system_geogcs_as_ants_crs(self):
        self.assertFalse(
            compare_coordinate_reference_systems(self.geogcs, self.geogcs.as_ants_crs())
        )

    def test_coord_system_rotated_geogcs_as_ants_crs(self):
        self.assertFalse(
            compare_coordinate_reference_systems(
                self.rotated_geogcs_maintain_rotated,
                self.rotated_geogcs_maintain_rotated.as_ants_crs(),
            )
        )

    def test_coord_system_transverse_mercator_as_ants_crs(self):
        self.assertFalse(
            compare_coordinate_reference_systems(
                self.transverse_mercator, self.transverse_mercator.as_ants_crs()
            )
        )

    def test_coord_system_iris_osgb_not_equal_to_ants_osgb(self):
        # not equivalent because we define an ANTS version in ants.coord_systems.py
        self.assertTrue(
            compare_coordinate_reference_systems(self.OSGB, self.OSGB.as_ants_crs())
        )

    def test_coord_system_ants_osgb_as_ants_osgb(self):
        self.assertFalse(
            compare_coordinate_reference_systems(
                self.OSGB.as_ants_crs(), ants.coord_systems.OSGB.crs
            )
        )

    def test_um_sphere_equivalence_geogcs(self):
        self.assertFalse(
            compare_coordinate_reference_systems(
                self.geogcs.as_ants_crs(), UM_SPHERE.crs
            )
        )

    def test_um_sphere_not_equivalent_to_rotated_geogcs(self):
        self.assertTrue(
            compare_coordinate_reference_systems(
                self.rotated_geogcs_maintain_rotated.as_ants_crs(), UM_SPHERE.crs
            )
        )

    def test_um_sphere_equivalence_rotated_geogcs(self):
        self.assertFalse(
            compare_coordinate_reference_systems(
                self.rotated_geogcs_treat_as_unrotated.as_ants_crs(), UM_SPHERE.crs
            )
        )

    def test_wgs84_geodetic_equivalence_geogcs(self):
        self.assertFalse(
            compare_coordinate_reference_systems(
                self.wgs_geodetic.as_ants_crs(), UM_SPHERE.crs
            )
        )


class TestTwoStage(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.regrid.rectilinear._AreaWeightedRegridder")
        self.area_patch = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.regrid.rectilinear.Linear.regridder")
        self.linear_patch = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.regrid.rectilinear._gen_regular_target")
        self.regtar_patch = patch.start()
        self.addCleanup(patch.stop)

    def test_same_crs_regrid(self):
        src_cube = ants.tests.stock.geodetic((4, 4))
        tgt_cube = ants.tests.stock.geodetic((4, 4))
        regridder = TwoStage()
        re = regridder.regridder(src_cube, tgt_cube)
        re(src_cube)

        self.assertTrue(self.area_patch.called)
        self.assertFalse(self.regtar_patch.called)
        self.assertFalse(self.linear_patch.called)

    def test_diff_crs_regrid(self):
        src_cube = ants.tests.stock.geodetic((4, 4))
        tgt_cube = ants.tests.stock.osgb((4, 4))
        regridder = TwoStage()
        re = regridder.regridder(src_cube, tgt_cube)
        re(src_cube)

        self.assertTrue(self.area_patch.called)
        self.assertTrue(self.regtar_patch.called)
        self.assertTrue(self.linear_patch.called)

    def test_homogenised_crs(self):
        src_cube = ants.tests.stock.geodetic((4, 4))
        crs = ants.coord_systems.WGS84_GEODETIC.crs
        src_cube.coord(axis="x").coord_system = crs
        src_cube.coord(axis="y").coord_system = crs
        tgt_cube = ants.tests.stock.geodetic((4, 4))
        regridder = TwoStage()
        re = regridder.regridder(src_cube, tgt_cube)
        re(src_cube)

        self.assertTrue(self.area_patch.called)
        self.assertFalse(self.regtar_patch.called)
        self.assertFalse(self.linear_patch.called)


class Test___repr__(ants.tests.TestCase):
    def test(self):
        mdtol = 1
        scheme = TwoStage(mdtol=mdtol)
        tar = "TwoStage(mdtol={})".format(mdtol)
        self.assertEqual(repr(scheme), tar)

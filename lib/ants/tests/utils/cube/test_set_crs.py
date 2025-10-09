# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
from ants.utils.cube import set_crs


class TestAll(ants.tests.TestCase):
    def setUp(self):
        cube = iris.cube.Cube([0])
        x_coord = iris.coords.DimCoord(
            0,
            ants.coord_systems.UM_SPHERE.x.standard_name,
            coord_system=ants.coord_systems.UM_SPHERE.crs,
            units=ants.coord_systems.UM_SPHERE.x.units,
        )
        y_coord = iris.coords.DimCoord(
            0,
            ants.coord_systems.UM_SPHERE.y.standard_name,
            coord_system=ants.coord_systems.UM_SPHERE.crs,
            units=ants.coord_systems.UM_SPHERE.y.units,
        )
        cube.add_aux_coord(x_coord, 0)
        cube.add_aux_coord(y_coord, 0)
        self.cube = cube

    def test_no_change(self):
        target = self.cube.copy()
        set_crs(self.cube)
        self.assertEqual(self.cube, target)

    def test_missing_crs_xy_lat_lon(self):
        # Infer missing lat lon coordinate system
        target = self.cube.copy()
        self.cube.coord(axis="x").coord_system = None
        self.cube.coord(axis="y").coord_system = None

        set_crs(self.cube)
        self.assertEqual(self.cube, target)

    def test_missing_crs_xy_non_lat_lon(self):
        self.cube.coord(axis="x").rename("projection_x_coordinate")
        self.cube.coord(axis="y").rename("projection_y_coordinate")
        self.cube.coord(axis="x").coord_system = None
        self.cube.coord(axis="y").coord_system = None
        msg = "Conflicting standard_name, cannot set inferred crs"
        with self.assertRaisesRegex(RuntimeError, msg):
            set_crs(self.cube)

    def test_override_crs(self):
        # ants.coord_system.CFCRS crs with metadata checking
        target = self.cube.copy()
        crs = ants.coord_systems.WGS84_GEODETIC
        x = target.coord(axis="x")
        y = target.coord(axis="y")
        x.coord_system = crs.crs
        x.standard_name = crs.x.standard_name
        x.units = crs.x.units
        y.coord_system = crs.crs
        y.standard_name = crs.y.standard_name
        y.units = crs.y.units

        set_crs(self.cube, crs)
        self.assertEqual(self.cube, target)

    def test_missing_crs_x_lat_lon(self):
        target = self.cube.copy()
        self.cube.coord(axis="x").coord_system = None

        set_crs(self.cube)
        self.assertEqual(self.cube, target)

    def test_missing_crs_y_lat_lon(self):
        target = self.cube.copy()
        self.cube.coord(axis="y").coord_system = None

        set_crs(self.cube)
        self.assertEqual(self.cube, target)


if __name__ == "__main__":
    ants.tests.main()

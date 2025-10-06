# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import ants.tests
import iris
from ants.utils.cube import derive_circular_status


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.cube = iris.cube.Cube([0, 1])
        lat = iris.coords.AuxCoord(
            [-90, 90], standard_name="latitude", units="degree_north"
        )
        self.cube.add_aux_coord(lat, 0)

    def test_global(self):
        lon = iris.coords.DimCoord(
            [-90, 90],
            standard_name="longitude",
            units="degree_east",
            bounds=[[-180, 0], [0, 180]],
        )
        self.cube.add_dim_coord(lon, 0)
        derive_circular_status(self.cube)

        self.assertTrue(self.cube.coord("longitude").circular)

    def test_regional_no_wrap(self):
        lon = iris.coords.DimCoord(
            [-90, 90],
            standard_name="longitude",
            units="degree_east",
            bounds=[[-170, 0], [0, 170]],
        )
        self.cube.add_dim_coord(lon, 0)
        derive_circular_status(self.cube)

        self.assertFalse(self.cube.coord("longitude").circular)

    def test_regional_wrapped(self):
        lon = iris.coords.DimCoord(
            [-170, 180],
            standard_name="longitude",
            units="degree_east",
            bounds=[[-180, -160], [160, 180]],
        )
        self.cube.add_dim_coord(lon, 0)
        derive_circular_status(self.cube)

        self.assertTrue(self.cube.coord("longitude").circular)

    def test_single_point_no_bounds(self):
        # Ensure we handle the case where no bounds are present (we can't
        # guess them either) as we cannot derive the circular attribute in this
        # case.
        self.cube = self.cube[0:1]
        lon = iris.coords.DimCoord([0], standard_name="longitude", units="degree_east")
        self.cube.add_dim_coord(lon, 0)
        derive_circular_status(self.cube)
        self.assertFalse(self.cube.coord("longitude").circular)

    def test_aux_coord(self):
        lon = iris.coords.AuxCoord(
            [-90, 90],
            standard_name="longitude",
            units="degree_east",
            bounds=[[-180, 0], [0, 180]],
        )
        self.cube.add_aux_coord(lon, 0)
        derive_circular_status(self.cube)

        self.assertFalse(hasattr(self.cube.coord("longitude"), "circular"))


if __name__ == "__main__":
    ants.tests.main()

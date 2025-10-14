# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
from ants.fileformats.ancil import _cubes_to_ancilfile


class TestAll(ants.tests.TestCase):
    def setUp(self):
        cube = ants.tests.stock.geodetic((2, 1, 1))
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i001")
        self.cube = cube

    def test_reject_unsupported_pressure_coordinate(self):
        coord = iris.coords.AuxCoord([0, 1], var_name="level_pressure")
        self.cube.add_aux_coord(coord, 0)
        with self.assertRaises(RuntimeError):
            _cubes_to_ancilfile(self.cube)

    def test_reject_unsupported_depth_coordinate(self):
        coord = iris.coords.AuxCoord([0, 1], var_name="depth")
        self.cube.add_aux_coord(coord, 0)
        with self.assertRaises(ValueError):
            _cubes_to_ancilfile(self.cube)

    def test_accept_supported_depth_coordinate(self):
        # Only checking that this does not raise exception so no need to
        # check for return value
        coord = iris.coords.AuxCoord(
            [0, 1], var_name="depth", attributes={"positive": "down"}
        )
        self.cube.add_aux_coord(coord, 0)
        _cubes_to_ancilfile(self.cube)

    def test__sorted_ppfields_call(self):
        # Check that pp field sorting is called.
        cubes = iris.cube.CubeList([self.cube])
        with mock.patch.object(
            ants.fileformats.pp,
            "_sorted_ppfields",
            wraps=ants.fileformats.pp._sorted_ppfields,
        ) as patch:
            _cubes_to_ancilfile(cubes)
        patch.assert_called_once_with(cubes)

    def test_rotated_pole_treatment(self):
        # Check what happens for various scenarios for rotated pole treatment.
        for lat_pole, lon_pole in zip([89, 89, 90], [0, 180, 200]):
            crs = iris.coord_systems.RotatedGeogCS(
                lat_pole, lon_pole, ellipsoid=ants.coord_systems.UM_SPHERE.crs
            )
            self.cube.coord(axis="x").coord_system = crs
            self.cube.coord(axis="y").coord_system = crs

            ancil = _cubes_to_ancilfile(self.cube)
            targ_grid_type = 100
            self.assertEqual(ancil.fixed_length_header.horiz_grid_type, targ_grid_type)


if __name__ == "__main__":
    ants.tests.main()

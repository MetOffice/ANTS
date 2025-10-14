# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import cf_units
import iris
import numpy as np
from ants.fileformats.ancil.template import _set_levels


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.cubes = iris.cube.CubeList([iris.cube.Cube([0, 1])])
        self.headers = {
            "integer_constants": {"num_levels": None},
            "level_dependent_constants": {"dims": None},
        }

    def test_no_levels(self):
        expected = {
            "integer_constants": {"num_levels": 1},
            "level_dependent_constants": {"dims": (None)},
        }
        _set_levels(self.cubes, self.headers)
        self.assertEqual(expected, self.headers)

    def test_with_height_levels(self):
        expected = {
            "integer_constants": {"num_levels": 2},
            "level_dependent_constants": {"dims": (None)},
        }
        zc = iris.coords.DimCoord(
            [1, 2],
            standard_name="model_level_number",
            attributes={"positive": "up"},
        )
        height_cube = self.cubes[0].copy()
        height_cube.add_dim_coord(zc, 0)
        _set_levels(iris.cube.CubeList([height_cube]), self.headers)
        self.assertEqual(expected, self.headers)

    def test_with_depth_levels(self):
        expected = {
            "integer_constants": {"num_levels": 2},
            "level_dependent_constants": {"dims": (None)},
            "fixed_length_header": {"vert_coord_type": 4},
        }

        self.headers["fixed_length_header"] = {}
        zc = iris.coords.DimCoord(
            [1, 2],
            standard_name="model_level_number",
            attributes={"positive": "down"},
        )
        depth = iris.coords.AuxCoord(
            [0.5, 1.5],
            attributes={"positive": "down"},
            long_name="depth",
            units=cf_units.Unit("m"),
        )
        depth_cube = self.cubes[0].copy()
        depth_cube.add_dim_coord(zc, 0)
        depth_cube.add_aux_coord(depth, data_dims=0)
        _set_levels(iris.cube.CubeList([depth_cube]), self.headers)
        self.assertEqual(expected, self.headers)


class TestFailures(ants.tests.TestCase):
    def _make_cube(self, coord):
        cube = iris.cube.Cube(np.zeros((len(coord.points),)))
        cube.add_dim_coord(coord, 0)
        return cube

    def test_different_number_multi_level_fields(self):
        vc1 = iris.coords.DimCoord(
            [1, 2], attributes={"positive": "down"}, units=cf_units.Unit("m")
        )

        vc2 = iris.coords.DimCoord(
            [1, 2, 3], attributes={"positive": "down"}, units=cf_units.Unit("m")
        )

        cubes = iris.cube.CubeList(self._make_cube(vc) for vc in (vc1, vc1, vc2))

        self.assertRaises(RuntimeError, _set_levels, cubes, None)

    def test_different_type_multi_level_fields(self):
        vc1 = iris.coords.DimCoord(
            [1, 2], attributes={"positive": "down"}, units=cf_units.Unit("m")
        )

        vc2 = iris.coords.DimCoord(
            [1, 2], standard_name="model_level_number", attributes={"positive": "up"}
        )

        cubes = iris.cube.CubeList(self._make_cube(vc) for vc in (vc1, vc2))

        self.assertRaises(RuntimeError, _set_levels, cubes, None)


if __name__ == "__main__":
    ants.tests.main()

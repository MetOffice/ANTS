# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.fileformats.pp as pp
import ants.tests
import cf_units
import iris
import numpy as np


class TestAll(ants.tests.TestCase):
    def setUp(self):
        # Builds a cube of 2 x coordinates, 2 y coordinates, 4 levels,
        # and 2 months
        self.cube = self._build_cube()
        self.ffv = _Mock_FFV()

    def _build_cube(self, level_coord_name="model_level_number"):
        self.time_unit = cf_units.Unit(
            "days since 0001-01-01 00:00:00", calendar="gregorian"
        )
        tc = iris.coords.DimCoord(
            np.array([15.5, 349.5]),
            bounds=np.array([[0.0, 31.0], [334.0, 365.0]]),
            standard_name="time",
            units=self.time_unit,
        )

        xc = iris.coords.DimCoord(np.array((0, 1)), standard_name="longitude")
        yc = iris.coords.DimCoord(np.array((0, 1)), standard_name="latitude")

        lc = iris.coords.DimCoord(np.array((0, 1, 2, 3)), long_name=level_coord_name)
        points = np.array((0.5, 1.5, 2.5, 3.5))
        bounds = np.array([[0, 1], [1, 2], [2, 3], [3, 4]])
        level_height = iris.coords.AuxCoord(
            points, bounds=bounds, var_name="level_height"
        )
        sigma = iris.coords.AuxCoord(points, bounds=bounds, var_name="sigma")

        cube = iris.cube.Cube(np.zeros((2, 2, 4, 2)))
        cube.add_dim_coord(xc, 0)
        cube.add_dim_coord(yc, 1)
        cube.add_dim_coord(lc, 2)
        cube.add_dim_coord(tc, 3)
        cube.add_aux_coord(level_height, data_dims=2)
        cube.add_aux_coord(sigma, data_dims=2)
        return cube

    def _get_cubes(self, level_coord_name="model_level_number"):
        cubes = iris.cube.CubeList()
        for i in range(0, 3):
            c = self._build_cube(level_coord_name)
            c.long_name = "Cube {}".format(i)
            c.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi(
                "m01s00i00{}".format(i + 1)
            )
            cubes.append(c)
        return cubes

    def test_field_order_with_model_levels(self):
        fields = pp._sorted_ppfields(self._get_cubes())
        # 4 levels, 3 stashes and 2 months

        # 12 since we cycle through entire set of 4x3 stashes and levels
        # before changing month.
        expected_lbmon = [1] * 12 + [12] * 12
        # 4 since we cycle through 4 levels; 2 since whole
        # pattern is repeated for each month
        expected_stash = ([1] * 4 + [2] * 4 + [3] * 4) * 2
        # 24 since pseudo level doesn't vary across entire cycle of 4 levels,
        # 3 stashes and 2 months
        expected_lbplev = [0] * 24
        # 6 since whole pattern is repeated for each month, stash
        expected_blev = [0.5, 1.5, 2.5, 3.5] * 6
        for i in range(len(fields)):
            self.assertEqual(expected_lbmon[i], fields[i].lbmon)
            self.assertEqual(expected_stash[i], fields[i].lbuser[3])
            self.assertEqual(expected_lbplev[i], fields[i].lbuser[4])
            self.assertEqual(expected_blev[i], fields[i].blev)

    def test_field_order_with_pseudo_levels(self):
        fields = pp._sorted_ppfields(self._get_cubes("pseudo_level"))
        # 4 pseudo levels, 3 stashes and 2 months

        # 12 since we cycle through entire set of 4x3 stashes and pseudo levels
        # before changing month.
        expected_lbmon = [1] * 12 + [12] * 12
        # 4 since we cycle through 4 pseudo levels; 2 since whole
        # pattern is repeated for each month
        expected_stash = ([1] * 4 + [2] * 4 + [3] * 4) * 2
        # 24 since pseudo level doesn't vary across entire cycle of 4 levels,
        # 3 stashes and 2 months
        expected_lbplev = [0, 1, 2, 3] * 6
        # 6 since whole pattern is repeated for each month, stash.  0 since we
        # set missing model levels to 1 in code outside the purview of this
        # test.
        expected_blev = [0] * 24
        for i in range(len(fields)):
            self.assertEqual(expected_lbmon[i], fields[i].lbmon)
            self.assertEqual(expected_stash[i], fields[i].lbuser[3])
            self.assertEqual(expected_lbplev[i], fields[i].lbuser[4])
            self.assertEqual(expected_blev[i], fields[i].blev)


class TestSetStashCode(ants.tests.TestCase):
    """
    These tests ensure that the stash code is set correctly and, if set to
    be a correctly formatted string, is converted to an
    iris.fileformat.pp.STASH object.

    """

    def _build_cube_list(self, cube_stash_code):
        cubes = iris.cube.CubeList()
        cube = ants.tests.stock.geodetic((2, 1))
        cube.attributes["STASH"] = cube_stash_code
        cubes.append(cube)
        return cubes

    def test_string_convert_to_stash(self):
        string_stash = "m01s00i001"
        expected_stash = iris.fileformats.pp.STASH.from_msi(string_stash)
        cubes = self._build_cube_list(string_stash)
        fields = pp._sorted_ppfields(cubes)
        self.assertEqual(expected_stash, fields[0].stash)

    def test_set_stash_code(self):
        expected_stash = iris.fileformats.pp.STASH.from_msi("m01s00i001")
        cubes = self._build_cube_list(expected_stash)
        fields = pp._sorted_ppfields(cubes)
        self.assertEqual(expected_stash, fields[0].stash)


class _Mock_FFV(object):
    def __init__(self):
        self.integer_constants = np.zeros(15)
        self.fixed_length_header = _Mock_Header()


class _Mock_Header(object):
    def __init__(self):
        self.raw = np.ones(152) * -32768


if __name__ == "__main__":
    ants.tests.main()

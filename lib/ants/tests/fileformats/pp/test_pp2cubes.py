# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import numpy as np
from ants.fileformats.pp import pp2cubes
from iris.fileformats.pp import PPField2


class TestPP2Cube(ants.tests.TestCase):
    def _make_header(self, blev):
        return (
            2000,
            1,
            1,
            0,
            0,
            0,
            2000,
            1,
            1,
            0,
            0,
            0,
            11,
            0,
            0,
            1,
            0,
            1,
            1,
            0,
            0,
            3,
            0,
            0,
            0,
            1,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            10001111,
            1,
            0,
            0,
            1001,
            0,
            0,
            1,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            float(blev),
            0.0,
            0.0,
            0.0,
            90.0,
            0.0,
            0.0,
            -45.0,
            90.0,
            -90.0,
            180.0,
            -9999.0,
            1.0,
        )

    def _ppfield(self, value, blev):
        header = self._make_header(blev)
        ppfield = PPField2(header)
        ppfield.data = np.array([value]).reshape(1, 1)
        return ppfield

    def _assert_cube(self, cube, data, levels):
        self.assertArrayEqual(data, cube.data)
        self.assertArrayEqual(np.array([45.0]), cube.coords("latitude")[0].points)
        self.assertArrayEqual(np.array([90.0]), cube.coords("longitude")[0].points)
        self.assertArrayEqual(levels, cube.coords("height")[0].points)
        self.assertEqual("m01s01i001", cube.attributes["STASH"])
        self.assertEqual("10.0", cube.attributes["um_version"])

    def test_single_ppfield(self):
        ppfield = self._ppfield(10.0, 1)
        cube = pp2cubes(ppfield)
        self.assertIs(len(cube), 1)
        self._assert_cube(cube[0], np.array([10.0]).reshape(1, 1), 1.0)

    def test_two_ppfields(self):
        ppfields = [
            self._ppfield(dval, lev) for dval, lev in ((10.0, 1.0), (11.0, 2.0))
        ]
        cube = pp2cubes(ppfields)
        self.assertIs(len(cube), 1)
        self._assert_cube(
            cube[0], np.array([10.0, 11.0]).reshape(2, 1, 1), np.array([1.0, 2.0])
        )

    def test_bounds_derive(self):
        # Ensure that on converting pp fields to cubes, that we also have
        # bounds populated on the horizontal coordinates.
        ppfield = self._ppfield(10.0, 1)
        patch = mock.patch("ants.utils.cube.guess_horizontal_bounds")
        with patch as util_gbound:
            cube = pp2cubes(ppfield)
        util_gbound.assert_called_once_with(cube)


if __name__ == "__main__":
    ants.tests.main()

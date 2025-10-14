# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest

import ants.tests
import iris
from ants.utils.cube import concatenate_cube


def swap_dim_aux(cube, coord):
    coord = cube.coord(coord)
    coord_dims = cube.coord_dims(coord)
    cube.remove_coord(coord)
    cube.add_aux_coord(coord, coord_dims)


class TestAll(ants.tests.TestCase):
    def setUp(self):
        cube = ants.tests.stock.geodetic((4, 2))
        swap_dim_aux(cube, "longitude")
        swap_dim_aux(cube, "latitude")
        c1 = cube[:2]
        c2 = cube[2:]
        self.source = iris.cube.CubeList([c1, c2])

    @unittest.expectedFailure
    def test_iris_concat_behaviour(self):
        # If this starts passing then we can remove our concatenation wrapper.
        self.source.concatenate_cube()

    def test_workaround(self):
        res = concatenate_cube(self.source)
        self.assertIsInstance(res, iris.cube.Cube)


if __name__ == "__main__":
    ants.tests.main()

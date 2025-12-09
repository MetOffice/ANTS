# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest

import ants
import ants.tests
import iris
from ants.utils.cube import concatenate


def swap_dim_aux(cube, coord):
    coord = cube.coord(coord)
    coord_dims = cube.coord_dims(coord)
    cube.remove_coord(coord)
    cube.add_aux_coord(iris.coords.AuxCoord.from_coord(coord), coord_dims)


class TestAll(ants.tests.TestCase):
    def setUp(self):
        cube = ants.tests.stock.geodetic((6, 2))
        swap_dim_aux(cube, "longitude")
        swap_dim_aux(cube, "latitude")
        c1 = cube[:2]
        c2 = cube[2:]
        self.source = iris.cube.CubeList([c1, c2])

    @unittest.expectedFailure
    def test_iris_concat_behaviour(self):
        # If this starts passing then we can remove our concatenation wrapper.
        self.assertTrue(len(self.source.concatenate()) == 1)

    def test_workaround(self):
        res = concatenate(self.source)
        self.assertTrue(len(res) == 1)

    def test_silent_existing_dim_coord_failure(self):
        dimcoord = iris.coords.DimCoord(range(2), long_name="existing")
        self.source[0].add_dim_coord(dimcoord, 0)
        res = concatenate(self.source)
        self.assertTrue(len(res) == 2)

    def test_silent_unable_represent_aux_as_dim_coord_failure(self):
        coord = self.source[1].coord("latitude")
        points = coord.points.copy()
        points[0] = coord.points[1]
        points[1] = coord.points[0]
        coord.points = points
        res = concatenate(self.source)
        self.assertTrue(len(res) == 2)

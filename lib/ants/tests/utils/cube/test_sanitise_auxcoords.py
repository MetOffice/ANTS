# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import ants.tests
import iris
import numpy as np
from ants.utils.cube import sanitise_auxcoords


class TestAll(ants.tests.TestCase):
    def test_transpose_multidim_coords(self):
        # Ensure that multidimensional coordinates are transposed where
        # necessary so that their dimension mapping is in increasing order.
        data = np.zeros((1, 2, 3, 4, 5, 6))
        cube = iris.cube.Cube(data)
        aux_coord = iris.coords.AuxCoord(np.zeros((3, 1, 5, 2)), long_name="bing")
        cube.add_aux_coord(aux_coord, (2, 0, 4, 1))

        sanitise_auxcoords(cube)

        coord = cube.coord("bing")
        self.assertEqual(coord.shape, (1, 2, 3, 5))
        self.assertEqual(cube.coord_dims(coord), (0, 1, 2, 4))

    def test_derived_coords(self):
        cube = ants.tests.stock.simple_4d_with_hybrid_height()
        cube.transpose((0, 1, 3, 2))
        target_altitude = cube.coord("altitude").copy()

        sanitise_auxcoords(cube)
        self.assertEqual(cube.coord_dims("surface_altitude"), (2, 3))
        self.assertEqual(cube.coord_dims("altitude"), (1, 2, 3))
        self.assertEqual(cube.coord("altitude"), target_altitude)

    def test_bounds(self):
        data = np.zeros((4, 5))
        cube = iris.cube.Cube(data)
        aux_coord = iris.coords.AuxCoord(
            np.zeros((5, 4)), bounds=np.zeros((5, 4, 2)), long_name="bing"
        )
        cube.add_aux_coord(aux_coord, (1, 0))

        sanitise_auxcoords(cube)

        coord = cube.coord("bing")
        self.assertEqual(coord.bounds.shape, (4, 5, 2))
        self.assertEqual(cube.coord_dims(coord), (0, 1))


if __name__ == "__main__":
    ants.tests.main()

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
import numpy as np
from ants.utils.cube import horizontal_grid


class TestAll(ants.tests.TestCase):
    def test_exception_for_multidimensional_coords(self):
        cube = iris.cube.Cube(np.zeros((2, 2)))
        xcoord = iris.coords.AuxCoord(
            points=[[0, 1], [1, 2]], standard_name="longitude"
        )
        cube.add_aux_coord(xcoord, (0, 1))
        with self.assertRaises(iris.exceptions.CoordinateNotFoundError):
            ants.utils.cube.horizontal_grid(cube, dim_coords=True)

    def test_scalar_longitude_coord(self):
        cube = ants.tests.stock.geodetic((1, 2))
        xc = cube.coord("longitude")
        yc = cube.coord("latitude")
        # Testing as much for no exception, as for returned result
        self.assertEqual((xc, yc), horizontal_grid(cube))


if __name__ == "__main__":
    ants.tests.main()

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import ants.tests
import ants.tests.stock as stock
import iris
from ants.utils.cube import reverse_coordinate


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.cube = stock.geodetic((2, 2))

    def test_inversion_values(self):
        tar = self.cube.data[::-1]

        cube = reverse_coordinate(self.cube, "latitude")

        self.assertArrayAlmostEqual(cube.data, tar)

        tar = [45.0, -45.0]
        self.assertArrayAlmostEqual(cube.coord("latitude").points, tar)

        tar = [[90, 0], [0, -90]]
        self.assertArrayAlmostEqual(cube.coord("latitude").bounds, tar)

    def test_aux_coord(self):
        coord = iris.coords.AuxCoord.from_coord(self.cube.coord("latitude"))
        self.cube.remove_coord("latitude")
        self.cube.add_aux_coord(coord, 0)
        msg = (
            "Only an inversion of a dimension coordinate is supported " r"\(latitude\)"
        )
        with self.assertRaisesRegex(RuntimeError, msg):
            reverse_coordinate(self.cube, "latitude")

    def test_double_inversion(self):
        # Check that only the intended changes are made by double inversion.
        # We should have exactly the same thing as we started with.
        tar = self.cube.copy()
        cube = reverse_coordinate(self.cube, "latitude")
        cube = reverse_coordinate(cube, "latitude")
        self.assertEqual(cube, tar)


if __name__ == "__main__":
    ants.tests.main()

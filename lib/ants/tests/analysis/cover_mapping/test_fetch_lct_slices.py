# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
from ants.analysis.cover_mapping import fetch_lct_slices


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic([2, 3, 4])
        pseudo_coord = iris.coords.AuxCoord([3, 2], long_name="pseudo_level")

        self.cube.add_aux_coord(pseudo_coord, 0)

    def test_mapping1(self):
        target_slices = tuple([1, slice(None), slice(None)])
        slices = fetch_lct_slices(self.cube, 2)
        self.assertEqual(slices, target_slices)

    def test_mapping2(self):
        target_slices = tuple([slice(None), 1, slice(None)])
        self.cube.transpose([1, 0, 2])
        slices = fetch_lct_slices(self.cube, 2)
        self.assertEqual(slices, target_slices)

    def test_multiple_tile(self):
        target_slices = tuple([(1, 0), slice(None), slice(None)])
        slices = fetch_lct_slices(self.cube, [2, 3])
        self.assertEqual(slices, target_slices)


if __name__ == "__main__":
    ants.tests.main()

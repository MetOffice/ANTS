# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import copy

import ants.tests
import ants.tests.stock as stock
import iris
from ants.utils.cube import sort_cubes


class TestAll(ants.tests.TestCase):
    def setUp(self):
        cube1 = stock.geodetic((1, 1), name="cube1", stash="m01s01i001")
        cube2 = stock.geodetic((1, 1), name="cube2", stash="m01s01i002")
        self.primary = [cube1, cube2]
        self.alternate = copy.deepcopy(self.primary)[::-1]

    def test_unordered_stash_sorting(self):
        # Ensure that the cubes are ordered as we expect.
        result = sort_cubes(self.primary, self.alternate)
        target = [self.primary, self.alternate[::-1]]
        self.assertEqual(result, tuple(target))

    def test_unordered_name_sorting(self):
        # Ensure that the cubes are ordered as we expect.
        [cube.attributes.clear() for cube in self.primary]
        [cube.attributes.clear() for cube in self.alternate]
        result = sort_cubes(self.primary, self.alternate)
        target = [self.primary, self.alternate[::-1]]
        self.assertEqual(result, tuple(target))

    def test_single_cube(self):
        # Ensure that it does not matter if stash code don't match if we have
        # only one primary and alternate (at it is not ambiguous for a sort).
        # Downstream code should handle this issue - as it is not a sort one.
        target = [[self.primary[0]], [self.alternate[0]]]
        result = sort_cubes(*target)
        self.assertEqual(result, tuple(target))

    def test_ambigious_pairing(self):
        # Ensure a suitable exception is raised when there is no suitable
        # pairing between groups of cubes based on stash.
        alt_stash = iris.fileformats.pp.STASH.from_msi("m01s01i003")
        self.primary[0].attributes["STASH"] = alt_stash

        msg = "primary_cubes' and 'alternate_cubes' don't share common"
        with self.assertRaisesRegex(ValueError, msg):
            sort_cubes(self.primary, self.alternate)


if __name__ == "__main__":
    ants.tests.main()

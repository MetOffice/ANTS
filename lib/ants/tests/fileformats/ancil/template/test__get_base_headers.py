# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants
import ants.tests
import iris
from ants.fileformats.ancil.template import _get_base_headers


class TestAll(ants.tests.TestCase):
    def setUp(self):
        cube1 = iris.cube.Cube([0])
        self.cubes = iris.cube.CubeList([cube1, cube1, cube1])
        self.field = ants.fileformats.ancil._Field3.empty()

    def test_ancil_version_call(self):
        ancil_version = "ants.fileformats.ancil.template._ancil_version"
        with mock.patch(ancil_version) as mock_version:
            _get_base_headers(self.cubes, self.field)
            mock_version.assert_called_once_with()

    def test_num_field_types(self):
        actual = _get_base_headers(self.cubes, self.field)
        self.assertEqual(
            len(self.cubes), actual["integer_constants"]["num_field_types"]
        )
        cubes_subset = self.cubes[:-1]
        actual = _get_base_headers(cubes_subset, self.field)
        self.assertEqual(
            len(cubes_subset), actual["integer_constants"]["num_field_types"]
        )


if __name__ == "__main__":
    ants.tests.main()

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import mule
from ants.fileformats.ancil.template import create


class TestAll(ants.tests.TestCase):
    def setUp(self):
        cube = iris.cube.Cube([0])
        self.cubes = iris.cube.CubeList([cube, cube])
        self.field = mule.Field3.empty()

    def test__get_base_headers_call(self):
        with mock.patch.multiple(
            "ants.fileformats.ancil.template",
            _get_base_headers=mock.DEFAULT,
            _set_levels=mock.DEFAULT,
            _set_grid_definition=mock.DEFAULT,
            _get_grid=mock.DEFAULT,
            time_headers=mock.DEFAULT,
        ) as patches:
            create(self.cubes, self.field)
            patches["_get_base_headers"].assert_called_once_with(self.cubes, self.field)

    def test__set_levels_call(self):
        with mock.patch.multiple(
            "ants.fileformats.ancil.template",
            _get_base_headers=mock.DEFAULT,
            _set_levels=mock.DEFAULT,
            _set_grid_definition=mock.DEFAULT,
            _get_grid=mock.DEFAULT,
            time_headers=mock.DEFAULT,
        ) as patches:
            patches["_get_base_headers"].return_value = mock.sentinel.headers
            create(self.cubes, self.field)
            patches["_set_levels"].assert_called_once_with(
                self.cubes,
                mock.sentinel.headers,
            )

    def test__get_grid_call(self):
        with mock.patch.multiple(
            "ants.fileformats.ancil.template",
            _get_base_headers=mock.DEFAULT,
            _set_levels=mock.DEFAULT,
            _set_grid_definition=mock.DEFAULT,
            _get_grid=mock.DEFAULT,
            time_headers=mock.DEFAULT,
        ) as patches:
            create(self.cubes, self.field)
            patches["_get_grid"].assert_called_once_with(self.cubes)

    def test__set_grid_definition_call(self):
        with mock.patch.multiple(
            "ants.fileformats.ancil.template",
            _get_base_headers=mock.DEFAULT,
            _set_levels=mock.DEFAULT,
            _set_grid_definition=mock.DEFAULT,
            _get_grid=mock.DEFAULT,
            time_headers=mock.DEFAULT,
        ) as patches:
            patches["_get_base_headers"].return_value = mock.sentinel.headers
            patches["_get_grid"].return_value = mock.sentinel.grid
            create(self.cubes, self.field)
            patches["_set_grid_definition"].assert_called_once_with(
                mock.sentinel.headers, mock.sentinel.grid, self.field
            )

    def test_set_headers_time_information_call(self):
        with mock.patch.multiple(
            "ants.fileformats.ancil.template",
            _get_base_headers=mock.DEFAULT,
            _set_levels=mock.DEFAULT,
            _set_grid_definition=mock.DEFAULT,
            _get_grid=mock.DEFAULT,
            time_headers=mock.DEFAULT,
        ) as patches:
            patches["_get_base_headers"].return_value = mock.sentinel.headers
            create(self.cubes, self.field)
            time_headers = patches["time_headers"]
            time_headers.set_headers_time_information.assert_called_once_with(
                self.cubes[0],
                mock.sentinel.headers,
            )


if __name__ == "__main__":
    ants.tests.main()

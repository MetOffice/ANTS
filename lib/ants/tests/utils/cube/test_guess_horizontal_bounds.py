# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
from ants.utils.cube import guess_horizontal_bounds


class TestAll(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.utils.coord.guess_bounds")
        self.mock_guess = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.utils.cube.horizontal_grid")
        self.mock_hgrid = patch.start()
        self.mock_hgrid.return_value = mock.sentinel.x, mock.sentinel.y
        self.addCleanup(patch.stop)

    def test_single_cube(self):
        cube = mock.Mock(name="cube", spec_set=iris.cube.Cube)
        guess_horizontal_bounds(cube)
        self.mock_hgrid.called_once_with(cube)
        self.mock_guess.called_once_with(mock.sentinel.x, mock.sentinel.y)

    def test_multi_cube(self):
        cube = mock.Mock(name="cube", spec_set=iris.cube.Cube)
        cube2 = mock.Mock(name="cube2", spec_set=iris.cube.Cube)
        guess_horizontal_bounds([cube, cube2])
        self.mock_hgrid.called_with(cube)
        self.mock_hgrid.called_with(cube2)


if __name__ == "__main__":
    ants.tests.main()

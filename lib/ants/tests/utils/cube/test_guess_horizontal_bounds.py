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
        """Test that arguments are being passed in correctly with a single cube as
        input"""
        cube = mock.Mock(name="cube", spec_set=iris.cube.Cube)
        guess_horizontal_bounds(cube)
        self.mock_hgrid.assert_called_once_with(cube)
        assert (
            mock.call(mock.sentinel.x, strict=False) in self.mock_guess.call_args_list
        )
        assert (
            mock.call(mock.sentinel.y, strict=False) in self.mock_guess.call_args_list
        )

    def test_multi_cube(self):
        """Test that both cubes are used when a cubelist is passed into
        guess_horizontal_bounds"""
        cube = mock.Mock(name="cube", spec_set=iris.cube.Cube)
        cube2 = mock.Mock(name="cube2", spec_set=iris.cube.Cube)
        guess_horizontal_bounds([cube, cube2])
        assert mock.call(cube) in self.mock_hgrid.call_args_list
        assert mock.call(cube2) in self.mock_hgrid.call_args_list

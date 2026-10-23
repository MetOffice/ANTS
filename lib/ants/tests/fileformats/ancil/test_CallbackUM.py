# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

# Some of this file has been edited using Met Office Github Copilot Enterprise.
import unittest.mock as mock

import ants.tests
import iris
from ants.fileformats.ancil import _CallbackUM as CallbackUM


@ants.tests.skip_mule
class Test___call__(ants.tests.TestCase):
    def setUp(self):
        self.cube = iris.cube.Cube([0])

        mock_headers = mock.Mock(name="Headers")
        mock_headers.fixed_length_header.grid_staggering = 3
        patch = mock.patch("mule.AncilFile.from_file", return_value=mock_headers)
        self.mock_ancilfv = patch.start()
        self.addCleanup(patch.stop)

        # The coordinate handling is tested in test__set_regular_coords_float64.
        patch = mock.patch("ants.fileformats.ancil._set_regular_coords_float64")
        self.mock_set_regular_coords = patch.start()
        self.addCleanup(patch.stop)

    def call(self):
        CallbackUM({mock.sentinel.filename: 6}).__call__(
            self.cube, mock.sentinel.field, mock.sentinel.filename
        )

    def test_check_ppcallback_callable_called(self):
        """The parent pp callback is still run by the UM callback."""
        pp_callback_callable = "ants.fileformats.pp._CallbackPP.__call__"

        with mock.patch(pp_callback_callable) as pp_call_mock:
            self.call()
        pp_call_mock.assert_called_once_with(
            self.cube, mock.sentinel.field, mock.sentinel.filename
        )

    def test_set_regular_coords_float64_called(self):
        """The callback calls the float64 coordinate helper with the cube and field."""
        self.call()
        self.mock_set_regular_coords.assert_called_once_with(
            self.cube, mock.sentinel.field
        )

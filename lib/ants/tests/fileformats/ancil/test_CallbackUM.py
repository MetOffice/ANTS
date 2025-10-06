# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import unittest.mock as mock

import ants.tests
import iris
from ants.fileformats.ancil import _CallbackUM as CallbackUM


class Test___call__(ants.tests.TestCase):
    def setUp(self):
        self.cube = iris.cube.Cube([0])

        mock_headers = mock.Mock(name="Headers")
        mock_headers.fixed_length_header.grid_staggering = 3
        patch = mock.patch("mule.AncilFile.from_file", return_value=mock_headers)
        self.mock_ancilfv = patch.start()
        self.addCleanup(patch.stop)

    def call(self):
        CallbackUM({mock.sentinel.filename: 6}).__call__(
            self.cube, mock.sentinel.field, mock.sentinel.filename
        )

    def test_check_ppcallback_callable_called(self):
        pp_callback_callable = "ants.fileformats.pp._CallbackPP.__call__"

        with mock.patch(pp_callback_callable) as pp_call_mock:
            self.call()
        pp_call_mock.assert_called_once_with(
            self.cube, mock.sentinel.field, mock.sentinel.filename
        )


if __name__ == "__main__":
    ants.tests.main()

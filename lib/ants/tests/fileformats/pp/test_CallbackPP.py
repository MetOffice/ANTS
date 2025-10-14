# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import unittest.mock as mock

import ants.tests
import iris
from ants.fileformats.pp import _CallbackPP as CallbackPP


class Test___call__(ants.tests.TestCase):
    def setUp(self):
        self.cube = iris.cube.Cube([0])
        self.user_callback = mock.Mock(name="user_callback")

    def call(self):
        callback = CallbackPP()
        callback.append_user_callback(self.user_callback)
        callback(self.cube, mock.sentinel.field, mock.sentinel.filename)

    def test__freeze_pseudo_level_is_called_if_pseudo_level_present(self):
        pseudo_level = iris.coords.DimCoord([0], long_name="pseudo_level")
        self.cube.add_dim_coord(pseudo_level, 0)

        freeze_level = "ants.fileformats.pp._CallbackPP._freeze_pseudo_level"
        with mock.patch(freeze_level) as freeze_pseudo_level_mocked:
            self.call()
        freeze_pseudo_level_mocked.assert_called_once_with(self.cube)

    def test__freeze_pseudo_level_not_called_if_no_pseudo_level_present(self):
        freeze_level = "ants.fileformats.pp._CallbackPP._freeze_pseudo_level"
        with mock.patch(freeze_level) as freeze_pseudo_level_mocked:
            self.call()
        self.assertFalse(freeze_pseudo_level_mocked.called)

    def test_file_not_used(self):
        mockfile = mock.Mock()
        CallbackPP().__call__(self.cube, None, mockfile)
        self.assertFalse(mockfile.called)

    def test_user_callback_called(self):
        self.call()
        self.user_callback.assert_called_once_with(
            self.cube, mock.sentinel.field, mock.sentinel.filename
        )


if __name__ == "__main__":
    ants.tests.main()

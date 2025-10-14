# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.fileformats.namelist import load_um_vertical


class TestInterface(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.fileformats.namelist._read_namelist")
        self.group = {"vertlevs": 1}
        self.patch_read_namelist = patch.start()
        self.patch_read_namelist.return_value = self.group
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.fileformats.namelist.VerticalLevels")
        self.patch_vert_levs = patch.start()
        self.patch_vert_levs().get_cube.return_value = mock.sentinel.vert_cube
        self.addCleanup(patch.stop)

    def test_arguments(self):
        res = next(load_um_vertical("dummy_filename"))
        self.patch_vert_levs.assert_called_with(self.group)
        self.assertIs(res, mock.sentinel.vert_cube)

    def test_callback_arguments(self):
        groups = {"vertlevs": mock.sentinel.grid}
        self.patch_read_namelist.return_value = groups

        my_callback = mock.Mock()

        with mock.patch("iris.io.run_callback") as run_callback_patch:
            next(load_um_vertical("dummy_filename", callback=my_callback))
        run_callback_patch.assert_called_once_with(
            my_callback, mock.sentinel.vert_cube, groups, "dummy_filename"
        )


class TestExceptions(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.fileformats.namelist._read_namelist")
        self.patch_read_namelist = patch.start()
        self.addCleanup(patch.stop)

    def test_duplicate_groups(self):
        # Handling of the case where we return two groups with the same name.
        # Since f90nml returns dictionaries, this can only happen when parsing
        # more than one file.
        filenames = ["dummy_filename1", "dummy_filename2"]
        self.patch_read_namelist.side_effect = [{"group1": 1}, {"group1": 2}]
        msg = "Cannot handle duplicate namelist groups."
        with self.assertRaisesRegex(RuntimeError, msg):
            next(load_um_vertical(filenames))

    def test_missing_any_valid_group(self):
        self.patch_read_namelist.return_value = {"group1": 1}
        msg = "No supported groups found"
        with self.assertRaisesRegex(ValueError, msg):
            next(load_um_vertical("dummy_filename"))


if __name__ == "__main__":
    ants.tests.main()

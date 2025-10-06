# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import os
import unittest.mock as mock

import ants.tests
from ants.config import dirpath_writeable


class TestAll(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("os.path.exists")
        self.mock_exists = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("os.makedirs")
        self.mock_mkdir = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("os.access")
        self.mock_access = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("os.path.expandvars", side_effect=lambda x: x)
        self.mock_expandvars = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("os.path.expanduser", side_effect=lambda x: x)
        self.mock_expanduser = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("os.path.realpath", side_effect=lambda x: x)
        self.mock_realpath = patch.start()
        self.addCleanup(patch.stop)

        self.filepath = os.path.join("/", "path", "to", "some", "file.ext")
        self.dirpath = os.path.join("/", "path", "to", "some")

    def test_no_read_write_perms(self):
        self.mock_exists.return_value = True
        self.mock_access.return_value = False
        msg = "You do not have read-write permissions to"
        with self.assertRaisesRegex(IOError, msg):
            dirpath_writeable(self.filepath)

    def test_not_exist(self):
        self.mock_exists.return_value = False
        res = dirpath_writeable(self.filepath)
        self.assertEqual(res, self.filepath)
        self.mock_mkdir.assert_called_once_with(self.dirpath)

    def test_all_ok(self):
        self.mock_exists.return_value = True
        self.mock_access.return_value = True
        res = dirpath_writeable(self.filepath)
        self.assertEqual(res, self.filepath)
        self.assertFalse(self.mock_mkdir.called)

    def test_expansions(self):
        res = dirpath_writeable(self.filepath)
        self.assertEqual(res, self.filepath)
        self.mock_expanduser.assert_called_once_with(self.filepath)
        self.mock_expandvars.assert_called_once_with(self.filepath)
        self.mock_realpath.assert_called_once_with(self.filepath)


if __name__ == "__main__":
    ants.tests.main()

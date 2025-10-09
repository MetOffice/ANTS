# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import argparse
import os
import unittest.mock as mock

import ants.tests
from ants.config import filepath_readable


class TestAll(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("os.path.exists")
        self.mock_exists = patch.start()
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

        self.filepath = os.path.join("/", "path", "to", "some", "file.ext")

    def test_not_readable(self):
        self.mock_exists.return_value = True
        self.mock_access.return_value = False
        msg = "You do not have read permissions to"
        with self.assertRaisesRegex(argparse.ArgumentTypeError, msg):
            filepath_readable(self.filepath)

    def test_not_exist(self):
        self.mock_exists.return_value = False
        msg = self.filepath.replace(r"/", r"\/") + " does not exist."
        with self.assertRaisesRegex(argparse.ArgumentTypeError, msg):
            filepath_readable(self.filepath)

    def test_expansions(self):
        with mock.patch("os.path.realpath", side_effect=lambda x: x) as mock_realpath:
            res = filepath_readable(self.filepath)
        self.assertEqual(res, self.filepath)
        self.mock_expanduser.assert_called_once_with(self.filepath)
        self.mock_expandvars.assert_called_once_with(self.filepath)
        mock_realpath.assert_called_once_with(self.filepath)


if __name__ == "__main__":
    ants.tests.main()

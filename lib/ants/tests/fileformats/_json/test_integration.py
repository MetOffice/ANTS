# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.fileformats.json import load


class Test_load(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("json.load")
        self.jpatch = patch.start()
        self.tar = {"key1": 1, "key2": 2}
        self.jpatch.return_value = self.tar
        self.addCleanup(patch.stop)

        patch = mock.patch("builtins.open")
        self.opatch = patch.start()
        self.addCleanup(patch.stop)

    def test_value(self):
        res = load(mock.sentinel.path)
        self.assertEqual(res, self.tar)


if __name__ == "__main__":
    ants.tests.main()

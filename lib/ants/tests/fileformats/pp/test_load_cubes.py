# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.fileformats.pp import load_cubes


class TestAll(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("iris.fileformats.pp.load_cubes")
        self.mock_load = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.fileformats.pp._CallbackPP")
        self.mock_callback = patch.start()
        self.addCleanup(patch.stop)

    def test_iris_call(self):
        load_cubes(mock.sentinel.dummy)
        self.mock_load.assert_called_once_with(
            mock.sentinel.dummy, self.mock_callback()
        )


if __name__ == "__main__":
    ants.tests.main()

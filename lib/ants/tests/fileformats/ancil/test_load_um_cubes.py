# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.fileformats.ancil import load_cubes


class TestAll(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("iris.fileformats.um.load_cubes")
        self.mock_load = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.fileformats.ancil._CallbackUM")
        self.mock_callback = patch.start()
        self.addCleanup(patch.stop)

        self.grid_staggering = {mock.sentinel.dummy: 6}
        patch = mock.patch("ants.fileformats.ancil._fetch_grid_staggering_from_file")
        self.mock_fetch_grid_stagger = patch.start()
        self.mock_fetch_grid_stagger.return_value = self.grid_staggering
        self.addCleanup(patch.stop)

    def test_iris_call(self):
        load_cubes(mock.sentinel.dummy)
        self.mock_callback.called_once_with(self.grid_staggering)
        self.mock_load.assert_called_once_with(
            mock.sentinel.dummy, self.mock_callback()
        )


if __name__ == "__main__":
    ants.tests.main()

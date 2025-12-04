# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.io.save as save
import ants.tests


class TestSave(ants.tests.TestCase):
    def setUp(self):
        self.cube = ants.tests.stock.geodetic((3, 4))

    def test_save_ancil(self):
        # Ensure expected arguments passed to the underlying um.save
        apatch = mock.patch("ants.io.save.ancil")
        with apatch as ancil_patch:
            filename = "dummy_fnme"
            self.cube.attributes["STASH"] = "m01s01i001"
            save.ancil(self.cube, filename)
            ancil_patch.assert_called_once_with(self.cube, filename)

    def test_invalid_filename(self):
        # Ensure ancil saver raises a ValueError for filenames ending .nc
        filename = "dummy_fnme.nc"
        with self.assertRaisesRegex(
            ValueError, "F03 UM ancillary files cannot be saved with a .nc extension."
        ):
            save.ancil(self.cube, filename)

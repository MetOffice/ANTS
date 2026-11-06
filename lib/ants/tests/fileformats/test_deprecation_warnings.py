# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

from unittest.mock import patch

import ants


class TestWarnings(ants.tests.TestCase):

    def test_ants_load(self):
        """Tests that calling the deprecated function ants.load will give a
        FutureWarning."""
        message = "ants.load has been deprecated. Please use ants.io.load.load instead."
        with patch("ants.io.load.load"):
            with self.assertRaisesRegex(FutureWarning, message):
                ants.load("test_ants_load_fake_filepath")

    def test_ants_load_landsea_mask(self):
        """Tests that calling the deprecated function
        ants.fileformats.load_landsea_mask will give a FutureWarning."""
        message = "ants.fileformats.load_landsea_mask has been deprecated. Please "
        "use ants.io.load.load_landsea_mask instead"
        with patch("ants.io.load.load_landsea_mask"):
            with self.assertRaisesRegex(FutureWarning, message):
                ants.fileformats.load_landsea_mask(
                    "test_ants_load_landea_mask_fake_filepath"
                )

    def test_ants_load_grid(self):
        """Tests that calling the deprecated function ants.load_grid will give a
        FutureWarning."""
        message = "ants.load_grid has been deprecated. Please use "
        "ants.io.load.load_grid instead."
        with patch("ants.io.load.load_grid"):
            with self.assertRaisesRegex(FutureWarning, message):
                ants.load_grid("test_ants_load_grid_fake_filepath")

    def test_ants_load_cube(self):
        """Tests that calling the deprecated function ants.load_cube will give a
        FutureWarning."""
        message = "ants.load_cube has been deprecated. Please use "
        "ants.io.load.load_cube instead."
        with patch("ants.io.load.load_cube"):
            with self.assertRaisesRegex(FutureWarning, message):
                ants.load_cube("test_ants_load_cube_fake_filepath")

    def test_ants_load_cubes(self):
        """Tests that calling the deprecated function ants.load_cubes will give a
        FutureWarning."""
        message = "ants.load_cubes has been deprecated. Please use "
        "ants.io.load.load_cubes instead."
        with patch("ants.io.load.load_cubes"):
            with self.assertRaisesRegex(FutureWarning, message):
                ants.load_cubes("test_ants_load_fake_filepath")

    def test_ants_load_raw(self):
        """Tests that calling the deprecated function ants.load will give a
        FutureWarning."""
        message = "ants.load_raw has been deprecated. Please use "
        "ants.io.load.load_raw instead."
        with patch("ants.io.load.load_raw"):
            with self.assertRaisesRegex(FutureWarning, message):
                ants.load_raw("test_ants_load_fake_filepath")

    def test_ants_load_um_vertical(self):
        """Tests that calling the deprecated function ants.load_um_vertical will
        give a FutureWarning."""
        message = "load_um_vertical has been deprecated. Please use "
        "ants.fileformats.namelist.load_vertical with option "
        "remove_level_zero=True"
        with patch("ants.fileformats.namelist.load_vertical"):
            with self.assertRaisesRegex(FutureWarning, message):
                ants.fileformats.namelist.load_um_vertical(
                    "test_ants_load_fake_filepath"
                )

    def test_ants_load_lfric_vertical(self):
        """Tests that calling the deprecated function ants.load_um_vertical will
        give a FutureWarning."""
        message = "load_lfric_vertical has been deprecated. Please use "
        "ants.fileformats.namelist.load_vertical with option "
        "remove_level_zero=False"
        with patch("ants.fileformats.namelist.load_vertical"):
            with self.assertRaisesRegex(FutureWarning, message):
                ants.fileformats.namelist.load_lfric_vertical(
                    "test_ants_load_fake_filepath"
                )

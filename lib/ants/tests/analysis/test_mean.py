# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
from ants.analysis import mean


class Testall(ants.tests.TestCase):
    def setUp(self):
        self.src_cube = iris.cube.Cube(1, long_name="Something")
        self.tgt_cube = iris.cube.Cube(1)
        self.src_cube.regrid = mock.Mock("regridder", return_value=self.tgt_cube)

        patch = mock.patch("ants.regrid.GeneralRegridScheme")
        self.mock_regridder = patch.start()
        self.addCleanup(patch.stop)

    def test_metadata(self):
        res = mean(self.src_cube, self.tgt_cube)
        self.assertEqual(res.long_name, "mean Something")
        cm = iris.coords.CellMethod("area: mean (area-weighted)")
        self.assertEqual(len(res.cell_methods), 1)
        self.assertEqual(res.cell_methods[0], cm)

    def test_metadata_no_existing_long_name(self):
        self.src_cube.long_name = None
        res = mean(self.src_cube, self.tgt_cube)
        self.assertEqual(res.long_name, None)


if __name__ == "__main__":
    ants.tests.main()

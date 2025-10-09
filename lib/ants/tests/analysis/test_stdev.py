# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.analysis import standard_deviation


class Testall(ants.tests.TestCase):
    def setUp(self):
        self.src_cube = iris.cube.Cube([10, 5, 17], long_name="Something")
        self.mean = iris.cube.Cube([1, 1, 1])

        patch = mock.patch("ants.regrid.GeneralRegridScheme")
        self.mock_regridder = patch.start()
        self.addCleanup(patch.stop)

        rpatch = mock.patch("iris.cube.Cube.regrid", return_value=self.src_cube)
        self.mock_regrid = rpatch.start()
        self.addCleanup(rpatch.stop)

    def test_metadata(self):
        res = standard_deviation(self.src_cube, self.mean)
        self.assertEqual(res.long_name, "standard deviation Something")
        cm_str = "area: standard_deviation (area-weighted)"
        cm = iris.coords.CellMethod(cm_str)
        self.assertEqual(len(res.cell_methods), 1)
        self.assertEqual(res.cell_methods[0], cm)

    def test_metadata_no_existing_long_name(self):
        self.src_cube.long_name = None
        res = standard_deviation(self.src_cube, self.mean)
        self.assertEqual(res.long_name, None)

    def test_values(self):
        # Testing explicitly the logic within our standard_deviation, not the regrid.
        result = standard_deviation(self.src_cube, self.mean)
        target = np.array([3.0, 2.0, 4.0])
        self.assertArrayAlmostEqual(result.data, target)


if __name__ == "__main__":
    ants.tests.main()

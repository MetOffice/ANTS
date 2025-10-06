# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.analysis import merge


class Testall(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.analysis.UMSpiralSearch")
        self.mock_fill = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch(
            "ants.utils.cube.sort_cubes", side_effect=lambda x, y: (x, y)
        )
        self.mock_sort = patch.start()
        self.addCleanup(patch.stop)

    def generate_dummy_cube(self, shape):
        latitude = iris.coords.DimCoord(
            np.linspace(-90, 90, 4), standard_name="latitude", units="degrees"
        )
        longitude = iris.coords.DimCoord(
            np.linspace(45, 360, 8), standard_name="longitude", units="degrees"
        )
        cube = iris.cube.Cube(
            np.zeros(shape, np.float32),
            dim_coords_and_dims=[(latitude, 0), (longitude, 1)],
        )
        return cube

    def test_call_args(self):
        primary_cube = self.generate_dummy_cube(shape=(4, 8))
        alternate_cube = self.generate_dummy_cube(shape=(4, 8))

        with mock.patch("ants.analysis._merge.merge") as mock_method:
            merge(primary_cube, alternate_cube, None)

        mock_method.assert_called_once_with(primary_cube, alternate_cube, None)
        self.assertFalse(self.mock_fill.called)


if __name__ == "__main__":
    ants.tests.main()

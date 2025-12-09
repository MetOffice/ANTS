# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.analysis.cover_mapping import normalise_fractions


class TestAll(ants.tests.TestCase):
    def setUp(self):
        data = np.array(
            [
                [[0, 0.9, 0], [1, 0.45, 1], [1, 1, 1]],
                [[1, 0, 0.9], [0, 0.45, 0], [0, 0, 0]],
            ]
        )
        self.cube = ants.tests.stock.geodetic(data=data)
        pseudo_coord = iris.coords.AuxCoord([3, 2], long_name="pseudo_level")

        self.cube.add_aux_coord(pseudo_coord, 0)

    def test_value(self):
        normalise_fractions(self.cube)
        tar = [[[0, 1, 0], [1, 0.5, 1], [1, 1, 1]], [[1, 0, 1], [0, 0.5, 0], [0, 0, 0]]]
        self.assertArrayAlmostEqual(self.cube.data, tar)

    def test_masked_array(self):
        # Ensure that the mask is retained after normalisation.
        data = self.cube.data
        data = np.ma.array(data)
        data[1, :] = np.ma.masked
        self.cube.data = data
        mask = self.cube.data.mask

        normalise_fractions(self.cube)
        tar = np.ma.array(
            [[[0, 1, 0], [1, 0.5, 1], [1, 1, 1]], [[1, 0, 1], [0, 0.5, 0], [0, 0, 0]]],
            mask=mask,
        )
        self.assertMaskedArrayAlmostEqual(self.cube.data, tar)

    def test_alternative_mapping(self):
        self.cube.transpose((1, 0, 2))
        normalise_fractions(self.cube)
        tar = [
            [[0.0, 1.0, 0.0], [1.0, 0.0, 1.0]],
            [[1.0, 0.5, 1.0], [0.0, 0.5, 0.0]],
            [[1.0, 1.0, 1.0], [0.0, 0.0, 0.0]],
        ]
        self.assertArrayAlmostEqual(self.cube.data, tar)

    def test_multidim_pseudo(self):
        self.cube.remove_coord("pseudo_level")
        pseudo_coord = iris.coords.AuxCoord(
            [[3, 2, 2], [3, 2, 2]], long_name="pseudo_level"
        )
        self.cube.add_aux_coord(pseudo_coord, (0, 1))

        msg = "Expecting a 1D pseudo_level coordinate not 2D."
        with self.assertRaisesRegex(RuntimeError, msg):
            normalise_fractions(self.cube)

    def test_out_of_bounds(self):
        data = [
            [[0.5, 0.5, 0.5], [0, 1, 1], [1, 1, 0.5]],
            [[1.5, 1.0, -0.1], [1.5, 0, 0], [0, 0, 0.1]],
        ]
        self.cube.data = data
        tar = [
            [[0.333333, 0.333333, 1.0], [0.0, 1.0, 1.0], [1.0, 1.0, 0.833333]],
            [[0.666666, 0.666666, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.166666]],
        ]
        normalise_fractions(self.cube)
        self.assertArrayAlmostEqual(self.cube.data, tar)

    def test_no_fractions(self):
        # Ensure that where there are no fractions that we ignore such
        # locations and inform the user of them.
        self.cube.data[:] = 0
        tar = self.cube.data.copy()

        with mock.patch("warnings.warn") as warn_patch:
            normalise_fractions(self.cube)

        msg = (
            "Locations present with no classification fraction, ignoring "
            "such locations."
        )
        warn_patch.assert_called_once_with(msg)
        self.assertArrayEqual(self.cube.data, tar)

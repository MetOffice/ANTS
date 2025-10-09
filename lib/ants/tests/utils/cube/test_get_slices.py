# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import numpy as np
from ants.utils.cube import get_slices


class TestNoPadding(ants.tests.TestCase):
    def test_global(self):
        cube = ants.tests.stock.geodetic((4, 4))
        slices = get_slices(cube, (-90, 90.0), (-180, 180))
        target_slices = [(slice(0, 4, None), slice(0, 4, None))]
        self.assertEqual(slices, target_slices)

    def test_increasing(self):
        cube = ants.tests.stock.geodetic((4, 4), ylim=(-90, 90))
        slices = get_slices(cube, (-60, 30), (-180, 180))
        target_slices = [(slice(0, 3, None), slice(0, 4, None))]
        self.assertEqual(slices, target_slices)

    def test_decreasing(self):
        cube = ants.tests.stock.geodetic((4, 4), ylim=(90, -90))
        slices = get_slices(cube, (-30, 60), (-180, 180))
        target_slices = [(slice(0, 3, None), slice(0, 4, None))]
        self.assertEqual(slices, target_slices)

    def test_no_coverage(self):
        cube = ants.tests.stock.geodetic((4, 4), ylim=(90, 60))
        with self.assertRaises(ants.exceptions.NoCoverageError):
            get_slices(cube, (-80, -90), (-180, 180))

    def test_alt_mapping(self):
        cube = ants.tests.stock.geodetic((4, 4), ylim=(-90, 90))
        cube.transpose((1, 0))
        slices = get_slices(cube, (-60, 30), (-180, 180))
        target_slices = [(slice(0, 4, None), slice(0, 3, None))]
        self.assertEqual(slices, target_slices)

    def test_cell_crossing_dateline(self):
        # Returning indices rather than slices
        cube = ants.tests.stock.geodetic((4, 8), xlim=(-180, 180))
        slices = get_slices(cube, (-90, 90), (90, 210))
        target_slices = [
            (slice(0, 4, None), slice(0, 1, None)),
            (slice(0, 4, None), slice(5, 8, None)),
        ]
        self.assertEqual(slices, target_slices)

    def test_circular(self):
        cube = ants.tests.stock.geodetic((4, 4), xlim=(-180, 0))
        slices = get_slices(cube, (-90, 90), (0, 360))
        target_slices = [(slice(0, 4, None), slice(0, 4, None))]
        self.assertEqual(slices, target_slices)

    def test_additional_dimensions(self):
        # Ensure that we provide the appropriate slice for additional
        # dimensions.
        data = np.zeros((2, 3, 4, 4))
        cube = ants.tests.stock.geodetic(data.shape, data=data)
        slices = get_slices(cube, (-90, 90), (0, 360))
        target_slices = [
            (slice(None), slice(None), slice(0, 4, None), slice(0, 4, None))
        ]
        self.assertEqual(slices, target_slices)

    def test_extract_range_entirely_within_source_bounds(self):
        cube = ants.tests.stock.geodetic((4, 4))
        slices = get_slices(cube, (1, 2), (1, 2))
        target_slices = [(slice(2, 3, None), slice(2, 3, None))]
        self.assertEqual(slices, target_slices)

    def test_extract_range_entirely_within_source_bounds_v2(self):
        cube = ants.tests.stock.geodetic((4, 4), xlim=(-10, 20))
        slices = get_slices(cube, (1, 2), (19, 19.2))
        target_slices = [(slice(2, 3, None), slice(3, 4, None))]
        self.assertEqual(slices, target_slices)

    def test_extract_range_entirely_within_source_bounds_inverse_dir(self):
        cube = ants.tests.stock.geodetic((4, 4), xlim=(20, -10))
        slices = get_slices(cube, (1, 2), (19, 19.5))
        target_slices = [(slice(2, 3, None), slice(0, 1, None))]
        self.assertEqual(slices, target_slices)

    def test_extract_range_entirely_within_source_bounds_global(self):
        # Ensure that we handle the following case:
        # source bounds = [-180, 180] getting translated to [180, 180] via wrap
        # around.
        cube = ants.tests.stock.geodetic((1, 1))
        slices = get_slices(cube, (1, 2), (1, 2))
        target_slices = [(slice(0, 1, None), slice(0, 1, None))]
        self.assertEqual(slices, target_slices)


class TestPadded(ants.tests.TestCase):
    def get_slices(self, pad_width, circular=False):
        cube = ants.tests.stock.geodetic((4, 8), xlim=(-180, 180))
        cube.coord(axis="x").circular = circular
        return get_slices(cube, (-90, 90), (-100, -80), pad_width=pad_width)

    def test_pad_0(self):
        slices = self.get_slices(0)
        target_slices = [(slice(0, 4, None), slice(1, 3, None))]
        self.assertEqual(slices, target_slices)

    def test_pad_1(self):
        slices = self.get_slices(1)
        target_slices = [(slice(0, 4, None), slice(0, 4, None))]
        self.assertEqual(slices, target_slices)

    def test_pad_2(self):
        slices = self.get_slices(2)
        target_slices = [(slice(0, 4, None), slice(0, 5, None))]
        self.assertEqual(slices, target_slices)

    def test_pad_2_circular(self):
        slices = self.get_slices(2, circular=True)
        target_slices = [
            (slice(0, 4, None), slice(0, 5, None)),
            (slice(0, 4, None), slice(7, 8, None)),
        ]
        self.assertEqual(slices, target_slices)


class TestExceptions(ants.tests.TestCase):
    def test_discontiguous_y(self):
        # This should not be possible, however if it does we need to raise a
        # a suitable exception to debug/support such a case.
        cube = ants.tests.stock.geodetic((4, 8), xlim=(-180, 180))
        with mock.patch("numpy.unique", return_value=np.array([1, 2])):
            msg = "Unable to resolve discontiguous extraction along y-axis"
            with self.assertRaisesRegex(RuntimeError, msg):
                get_slices(cube, (-90, 90), (-100, -80))


if __name__ == "__main__":
    ants.tests.main()

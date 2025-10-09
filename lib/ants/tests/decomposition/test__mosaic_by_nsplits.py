# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
from ants.decomposition import _mosaic_by_nsplits as mosaic_by_nsplits


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.src_shape = (2, 2, 2)

    def _test_iterable_compare(self, result, target):
        for res, tgt in zip(result, target):
            self.assertEqual(res, tgt)

    def test_single_slice(self):
        split = (1, 1, 1)
        iter_result = mosaic_by_nsplits(self.src_shape, split)
        iter_target = [tuple([slice(0, None, 1) for i in range(3)])]
        self._test_iterable_compare(iter_result, iter_target)

    def test_multi_slice(self):
        split = (1, 2, 1)
        iter_result = mosaic_by_nsplits(self.src_shape, split)
        iter_target = [
            (slice(0, None, 1), slice(0, 1, None), slice(0, None, 1)),
            (slice(0, None, 1), slice(1, None, 1), slice(0, None, 1)),
        ]
        self._test_iterable_compare(iter_result, iter_target)

    def test_multi_slice_multi_dim(self):
        split = (1, 2, 2)
        iter_result = mosaic_by_nsplits(self.src_shape, split)
        iter_target = [
            (slice(0, None, 1), slice(0, 1), slice(0, 1)),
            (slice(0, None, 1), slice(0, 1), slice(1, None, 1)),
            (slice(0, None, 1), slice(1, None, 1), slice(0, 1)),
        ]
        self._test_iterable_compare(iter_result, iter_target)

    def test_shape_mismatch(self):
        split = (1, 1)
        msg = "Source shape with length 3 does not match split length 2"
        with self.assertRaisesRegex(ValueError, msg):
            mosaic_by_nsplits(self.src_shape, split)

    def test_non_positive_split(self):
        split = (1, 1, 0)
        msg = "Split shape at index 2 has value 0, must be a positive integer."
        with self.assertRaisesRegex(ValueError, msg):
            mosaic_by_nsplits(self.src_shape, split)

    def test_non_positive_src_shape(self):
        split = (1, 1, 1)
        self.src_shape = (1, 1, 0)
        msg = "Source shape at index 2 has value 0, must be a positive " "integer."
        with self.assertRaisesRegex(ValueError, msg):
            mosaic_by_nsplits(self.src_shape, split)

    def test_too_many_splits(self):
        split = (10, 1, 1)
        msg = "Cannot split our domain into more pieces than there are " "elements"
        with self.assertRaisesRegex(ValueError, msg):
            mosaic_by_nsplits(self.src_shape, split)

    def test_odd_shape(self):
        # Ensure that we can handle the case where we request a slice iterator
        # which splits the domain by a number which does not divide exactly
        # into equal sized pieces.
        self.src_shape = (1, 9, 1)
        split = (1, 2, 1)
        iter_result = mosaic_by_nsplits(self.src_shape, split)
        iter_target = [
            (slice(0, None, 1), slice(0, 4), slice(0, None, 1)),
            (slice(0, None, 1), slice(4, None, 1), slice(0, None, 1)),
        ]
        self._test_iterable_compare(iter_result, iter_target)


if __name__ == "__main__":
    ants.tests.main()

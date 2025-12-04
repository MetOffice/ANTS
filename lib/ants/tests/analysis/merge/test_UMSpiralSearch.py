# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.analysis._merge import UMSpiralSearch


class Common(object):
    def setUp(self):
        # Intentionally limit ourselves to the simplest case where distance
        # constraints and cyclic behaviour is not observed.

        self.source = ants.tests.stock.geodetic((3, 3), xlim=(3, 5), ylim=(3, 5))
        source_mask = np.array(
            [[True, False, False], [False, False, False], [True, True, False]]
        )
        self.source.data = np.ma.array(self.source.data, mask=source_mask)

        target_mask = np.array(
            [[False, False, True], [True, False, False], [False, True, True]]
        )
        self.target_mask = self.source.copy(target_mask)

        patch = mock.patch("warnings.warn")
        self.mock_warning = patch.start()
        self.addCleanup(patch.stop)


@ants.tests.skip_spiral
class TestConstrained(Common, ants.tests.TestCase):
    # Define a class where constrained == True
    class ConstrainedUMSpiralSearch(UMSpiralSearch):
        _CONSTRAINED = True

    def test_target_mask(self):
        nfiller = self.ConstrainedUMSpiralSearch(
            self.source, target_mask=self.target_mask
        )
        nfiller(self.source)

        target = np.ma.array([[1, 1, 2], [3, 4, 5], [4, 7, 8]])
        target.mask = self.target_mask.data
        self.assertMaskedArrayEqual(self.source.data, target)

    def test_no_target_mask(self):
        nfiller = self.ConstrainedUMSpiralSearch(self.source)
        nfiller(self.source)

        target = np.ma.array([[1, 1, 2], [3, 4, 5], [3, 8, 8]])
        self.assertMaskedArrayEqual(self.source.data, target)

    def conflicting_src_tgt_mask(self, xfrac, target):
        source_mask = np.array(
            [[True, True, True], [False, False, True], [True, True, False]]
        )
        target_mask = np.array(
            [[False, False, True], [True, True, True], [True, True, False]]
        )
        target.mask = target_mask.copy()

        source = ants.tests.stock.geodetic((3, 3), xlim=(3, 3 + xfrac), ylim=(3, 3.01))
        source.data = np.ma.array(source.data, mask=source_mask.copy())
        tgt_mask = source.copy(target_mask.copy())

        nfiller = self.ConstrainedUMSpiralSearch(source, target_mask=tgt_mask)
        nfiller(source)
        self.assertMaskedArrayEqual(source.data, target)

    def test_conflicting_src_tgt_mask_lt_200km(self):
        # Take the nearest unmasked land point as identified by the target
        # mask.
        target = np.ma.array([[8, 8, 2], [3, 4, 5], [6, 7, 8]])
        self.conflicting_src_tgt_mask(0.001, target)

    def test_conflicting_src_tgt_mask_gt_200km(self):
        # Take the nearest unmasked source point (irrespective of whether
        # target says is ocean/land) if there are no land points within 200km.
        target = np.ma.array([[3, 4, 2], [3, 4, 5], [6, 7, 8]])
        self.conflicting_src_tgt_mask(100, target)


@ants.tests.skip_spiral
class TestAll(Common, ants.tests.TestCase):
    def test_no_target_mask_provided(self):
        # Ensure that when no target has been provided, that all points are
        # considered valid.
        source = ants.tests.stock.geodetic((3, 3), xlim=(3, 303), ylim=(3, 3.01))
        source.data = np.ma.array(source.data)
        source.data[1, 1] = np.ma.masked
        with mock.patch("ants.analysis._merge._spiral_wrapper") as spatch:
            spatch.return_value = [0, 0]
            UMSpiralSearch(source)
        self.assertTrue(spatch.called)
        self.assertFalse(spatch.call_args[0][4].any())

    def test_conflicting_src_tgt_mask(self):
        source_mask = np.array(
            [[True, True, True], [False, False, True], [True, True, False]]
        )
        target_mask = np.array(
            [[False, False, True], [True, True, True], [True, True, False]]
        )
        target = np.ma.array([[3, 4, 2], [3, 4, 5], [6, 7, 8]])
        target.mask = target_mask.copy()

        source = ants.tests.stock.geodetic((3, 3), xlim=(3, 303), ylim=(3, 3.01))
        source.data = np.ma.array(source.data, mask=source_mask.copy())
        tgt_mask = source.copy(target_mask.copy())

        nfiller = UMSpiralSearch(source, target_mask=tgt_mask)
        nfiller(source)

        self.assertMaskedArrayEqual(source.data, target)

    def test_search_mask(self):
        nfiller = UMSpiralSearch(self.source, search_mask=self.target_mask)
        nfiller(self.source)
        target = np.ma.array([[1, 1, 2], [3, 4, 5], [4, 4, 8]])
        self.assertMaskedArrayEqual(self.source.data, target)

    def test_search_mask_lsm_inheritance(self):
        nfiller = UMSpiralSearch(
            self.source, search_mask=self.target_mask, target_mask=self.target_mask
        )
        nfiller(self.source)
        target = np.ma.array([[1, 1, -1], [-1, 4, 5], [4, -1, -1]])
        target.mask = self.target_mask.data.copy()
        self.assertMaskedArrayEqual(self.source.data, target)

    def no_source_mask(self):
        # Ensure we still inherit the final mask.
        self.source.data = self.source.data.data
        target = np.ma.array(self.source.data.copy())
        target.mask = self.target_mask.data
        nfiller = UMSpiralSearch(self.source, target_mask=self.target_mask)
        nfiller(self.source)
        self.assertMaskedArrayEqual(self.source.data, target)

    def test_no_source_mask(self):
        self.no_source_mask()

    def test_no_source_mask_no_spiral_search_call(self):
        # Ensure we do not call the spiral search unnecessarily (i.e. when we
        # have no missing data in the source.
        spiral_func = "um_spiral_search.um_spiral_search.spiral_search"
        with mock.patch(spiral_func) as spiral_patch:
            self.no_source_mask()
        self.assertFalse(spiral_patch.spiral_circle_search.called)

    def test_nan_as_missing(self):
        # Ensure NaN values are treated as masked - a double check here is
        # mixing the source mask with NaN data to ensure that the two are
        # combined correctly.
        # Source data must be float to have NaN values.
        self.source.data = self.source.data.astype("float")
        self.source.data[2, 0] = np.nan
        nfiller = UMSpiralSearch(self.source)
        nfiller(self.source)

        target = np.ma.array([[1, 1, 2], [3, 4, 5], [3, 8, 8]])
        self.assertMaskedArrayEqual(self.source.data, target)

    def test_spiralsearch_args(self):
        # Ensure that parameters we pass to the spiral search are those we
        # expect.
        spiral_func = mock.patch(
            "ants.analysis._merge.spiral",
            return_value=np.ones(2, dtype="int"),
            autospec=True,
        )
        self.source.coord(axis="x").circular = mock.sentinel.circular
        with spiral_func as spiral_patch:
            UMSpiralSearch(self.source, target_mask=self.target_mask)
        target = (6371229.0, True, False, False, 200000.0, 3)
        self.assertEqual(spiral_patch.call_args_list[0][0][5:11], target)

    def caching_utilised(self):
        source1 = self.source.copy()
        source2 = self.source.copy()
        source3 = self.source.copy()
        nfiller = UMSpiralSearch(self.source, target_mask=self.target_mask)
        nfiller(source1)
        nfiller(source2)
        nfiller(source3)
        return source1, source2, source3

    def test_caching_utilised_value(self):
        # Ensure that the values assigned to the sources are as expected.
        source1, source2, source3 = self.caching_utilised()
        target = np.ma.array([[1, 1, 2], [3, 4, 5], [3, 7, 8]])
        target.mask = self.target_mask.data
        for source in [source1, source2, source3]:
            self.assertMaskedArrayEqual(source.data, target)

    def test_caching_utilised_spiral_call(self):
        # Ensure we only call the spiral search once.
        spiral_func = mock.patch(
            "ants.analysis._merge.spiral",
            return_value=np.ones(2, dtype="int"),
            autospec=True,
        )
        with spiral_func as spiral_patch:
            self.caching_utilised()
        self.assertEqual(spiral_patch.call_count, 1)

    def test_ndsupport(self):
        source1 = self.source.copy()
        source2 = self.source.copy()
        source1.add_aux_coord(iris.coords.AuxCoord(0, long_name="bing"), None)
        source2.add_aux_coord(iris.coords.AuxCoord(2, long_name="bing"), None)
        source = iris.cube.CubeList([source1, source2]).merge_cube()
        nfiller = UMSpiralSearch(source, target_mask=self.target_mask)
        nfiller(source)

        target = np.ma.array([[1, 1, 2], [3, 4, 5], [3, 7, 8]])
        target.mask = self.target_mask.data
        target = np.ma.array([target, target])
        self.assertMaskedArrayEqual(source.data, target)

    def test_no_warning(self):
        UMSpiralSearch(self.source, target_mask=self.target_mask)
        self.assertFalse(self.mock_warning.called)


@ants.tests.skip_spiral
class TestExceptions(Common, ants.tests.TestCase):
    def test_target_mask_not_2dim(self):
        # Make a 3dim target mask.
        self.target_mask = iris.cube.CubeList(
            [self.target_mask.copy(), self.target_mask.copy()]
        )
        self.target_mask[0].add_aux_coord(
            iris.coords.AuxCoord(0, long_name="bing"), None
        )
        self.target_mask[1].add_aux_coord(
            iris.coords.AuxCoord(1, long_name="bing"), None
        )
        self.target_mask = self.target_mask.merge_cube()

        msg = "Expecting a 2-dimensional target_mask, got 3-dimensions."
        with self.assertRaisesRegex(ValueError, msg):
            UMSpiralSearch(self.source, target_mask=self.target_mask)

    def test_target_mask_coords_incompatible_with_source(self):
        points = self.target_mask.coord(axis="y").points.copy()
        points[0] = points[0] + 1e-6
        self.target_mask.coord(axis="y").points = points

        msg = (
            "The provided target_mask's y coordinates do not match "
            "those of the source."
        )
        with self.assertRaisesRegex(ValueError, msg):
            UMSpiralSearch(self.source, target_mask=self.target_mask)

    def test_search_mask_coords_incompatible_with_source(self):
        points = self.target_mask.coord(axis="x").points.copy()
        points[0] = points[0] + 1e-6
        self.target_mask.coord(axis="x").points = points

        msg = (
            "The provided search_mask's x coordinates do not match "
            "those of the source."
        )
        with self.assertRaisesRegex(ValueError, msg):
            UMSpiralSearch(self.source, search_mask=self.target_mask)

    def test_source_coords_incompatibility_with_cache(self):
        nfiller = UMSpiralSearch(self.source, target_mask=self.target_mask)
        points = self.source.coord(axis="x").points.copy()
        points[0] = points[0] + 1e-6
        self.source.coord(axis="x").points = points
        msg = (
            "The provided destination cube's x coordinates do not "
            "match those of the source."
        )
        with self.assertRaisesRegex(ValueError, msg):
            nfiller(self.source)

    def test_source_mask_incompatibility_with_cache(self):
        nfiller = UMSpiralSearch(self.source, target_mask=self.target_mask)
        self.source.data.mask = ~self.source.data.mask
        msg = "Destination mask is not compatible with the cached nearest neighbours."
        with self.assertRaisesRegex(ValueError, msg):
            nfiller(self.source)

    def test_no_valid_data(self):
        # When no valid data is present, the spiral search returns a negative
        # index.  The spiral search can cause segmentation faults
        # in this case so we capture the case ourselves.
        # Ensure we provide additional context to users to help users.
        self.source.data[:] = np.ma.masked
        self.target_mask.data[:] = False
        msg = ".*any valid data."
        with self.assertRaisesRegex(ValueError, msg):
            UMSpiralSearch(self.source, target_mask=self.target_mask)

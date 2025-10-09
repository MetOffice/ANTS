# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock
import warnings

import ants.tests
import ants.tests.stock as stock
import iris
import iris.coord_systems
import numpy as np
from ants._constraints import _extract_overlap as extract_overlap


class TestValue(ants.tests.TestCase):
    def test_wraparound_same_crs_bounds(self):
        # Uses intersection with native coordinates
        # Intersection previously wrapped points at (base + period) where base
        # is the minimum and period the modulus (i.e. 360).
        source = stock.geodetic((4, 4))
        grid = stock.geodetic((3, 3))
        overlap = extract_overlap(source, grid, fix_period=True, pad_width=0)

        tdata = source.data.copy()

        self.assertArrayAlmostEqual(overlap.data, tdata)

        coord = "longitude"
        points = [-135.0, -45.0, 45.0, 135]
        self.assertArrayAlmostEqual(overlap.coord(coord).points, points)

    def test_wraparound_same_crs_no_bounds(self):
        # Uses intersection with native coordinates
        # Intersection previously wrapped points at (base + period) where base
        # is the minimum and period the modulus (i.e. 360).
        # Defining the target as having bounds should yield the same results as
        # without bounds as we are generating global fields.
        source = stock.geodetic((4, 4), with_bounds=False)
        grid = stock.geodetic((3, 3), with_bounds=True)
        overlap = extract_overlap(source, grid, fix_period=True, pad_width=0)

        tdata = source.data.copy()
        coord = "longitude"
        points = [-135.0, -45.0, 45.0, 135]
        self.assertArrayAlmostEqual(overlap.data, tdata)
        self.assertArrayAlmostEqual(overlap.coord(coord).points, points)
        self.assertTrue(source.coord(axis="x").has_bounds)

    def test_same_crs_non_modulus(self):
        # Ensure that we can handle coordinates with no modulus (i.e. not in
        # degrees).
        source = stock.osgb((4, 4), xlim=(1000, 4000), ylim=(1000, 4000))
        grid = stock.osgb((4, 4), xlim=(3000, 4000), ylim=(3000, 4000))
        overlap = extract_overlap(source, grid, fix_period=True, pad_width=0)

        tdata = source.data.copy()[2:, 2:]
        self.assertArrayAlmostEqual(overlap.data, tdata)
        coord = "projection_x_coordinate"
        points = source.coord(coord).points[2:]
        self.assertArrayAlmostEqual(overlap.coord(coord).points, points)

    def test_diff_crs_target_modulus(self):
        # Ensure that we can handle the case of different coordinates.
        # Since the source rather than the target has no modulus, iris
        # intersection will not be used.
        source = stock.osgb((4, 4), xlim=(-12, 7e5), ylim=(-12, 13e5))
        grid = stock.geodetic((16, 16), ylim=(50, 65), xlim=(-1, 10))
        overlap = extract_overlap(source, grid, fix_period=True, pad_width=0)

        tdata = source.data.copy()[:, 2:]
        self.assertArrayAlmostEqual(overlap.data, tdata)
        coord = "projection_x_coordinate"
        points = source.coord(coord).points[2:]
        self.assertArrayAlmostEqual(overlap.coord(coord).points, points)

    def test_wraparound_dateline(self):
        source = stock.geodetic((4, 4), xlim=(0, 360))
        grid = stock.geodetic((4, 4), xlim=(-180, -10))
        target = source[:, 2:].copy()
        target.coord(axis="x")

        overlap = extract_overlap(source, grid, fix_period=True, pad_width=0)
        self.assertEqual(overlap, target)

    def wraparound_discontiguous_over_orig_range(self, fix_period):
        # wraparound extract which is discontiguous over the original range
        # (from the definition of iris which is not wraparound aware).
        source = stock.geodetic((4, 4), xlim=(0, 360))
        grid = stock.geodetic((4, 4), xlim=(-10, 90))
        if not fix_period:
            target = source[:, tuple([3, 0, 1])]
            points = target.coord(axis="x").points.copy()
            points[-2:] += 360
            bounds = target.coord(axis="x").bounds.copy()
            bounds[-2:] += 360
            target.coord(axis="x").points = points
            target.coord(axis="x").bounds = bounds
        else:
            target = source[:, tuple([0, 1, 3])]
            target.coord(axis="x").circular = True

        overlap = extract_overlap(source, grid, fix_period=fix_period, pad_width=0)
        self.assertEqual(overlap, target)

    def test_wraparound_dateline_discon_fixed_period(self):
        # wraparound resulting in discontiguous bounds when defined over the
        # original range i.e. we need to change range in order for iris to deem
        # it contiguous so we raise an exception here.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.wraparound_discontiguous_over_orig_range(True)

    def test_wraparound_dateline_contig_not_fixed_period(self):
        # wraparound resulting is contiguous bounds when range is allowed to
        # adjust following an extract.
        self.wraparound_discontiguous_over_orig_range(False)

    def test_wraparound_dateline_global(self):
        source = stock.geodetic((4, 4), xlim=(100, 460))
        grid = stock.geodetic((4, 4), xlim=(-180, 180))
        grid.coord(axis="x").circular = False

        overlap = extract_overlap(source, grid, fix_period=True, pad_width=0)
        self.assertEqual(overlap, source)

    def test_multiple_geometry_support(self):
        # Ensure that multiple geometries are merged together to an appropriate
        # range.
        source = stock.geodetic((4, 16), xlim=(-180, 180))
        grid = stock.geodetic((4, 4), xlim=(0, 360))
        grid.coord(axis="x").coord_system = iris.coord_systems.GeogCS(6371230.0)
        grid.coord(axis="y").coord_system = iris.coord_systems.GeogCS(6371230.0)
        overlap = extract_overlap(source, grid, fix_period=True, pad_width=0)
        self.assertEqual(overlap, source)

    def test_circular_status(self):
        source = stock.geodetic((4, 4))
        grid = stock.geodetic((3, 3))
        pcircular = mock.patch(
            "ants.utils.cube.derive_circular_status",
            return_value=mock.sentinel.circular,
        )
        with pcircular as patch_circular:
            extract_overlap(source, grid, fix_period=True, pad_width=0)
        self.assertTrue(patch_circular.called)

    def test_discontiguous_extract(self):
        # Two separate overlapping pieces cannot be resolved as contiguous
        # coordinates on return.
        #
        # Illustration:
        # 0                                      360 Range
        # |                                       |
        # |-----------------------|                  Source
        # |--|                 |------------------|  Grid
        # |--|                 |--|                  Extract
        source = stock.geodetic((4, 16), xlim=(-180, 10))
        grid = stock.geodetic((4, 4), xlim=(0, 190))
        grid.coord(axis="x").coord_system = iris.coord_systems.GeogCS(6371330.0)
        grid.coord(axis="y").coord_system = iris.coord_systems.GeogCS(6371330.0)
        msg = "Unable to perform extraction and maintain contiguous " "coordinates."
        with mock.patch("warnings.warn") as warn:
            overlap = extract_overlap(source, grid, fix_period=False, pad_width=0)
        warn.assert_called_once_with(msg)

        target = [4.0625, 185.9375]
        self.assertArrayEqual(overlap.coord(axis="x").points, target)

    def test_split_geometries_at_dateline(self):
        # Two separate geometries which are resolved by being stitching
        # together.
        source = stock.geodetic((4, 16), xlim=(-180, 180), ylim=(-60, 90))
        grid = stock.geodetic((4, 4), xlim=(178, 182), ylim=(-2, 2))

        tgt_crs = iris.coord_systems.RotatedGeogCS(
            72.1, 179.0, ellipsoid=ants.coord_systems.UM_SPHERE.crs
        )
        grid.coord(axis="x").coord_system = tgt_crs
        grid.coord(axis="y").coord_system = tgt_crs
        overlap = extract_overlap(source, grid, fix_period=False, pad_width=0)

        # Padding of 1 occurs as we go cross crs.
        target = [168.75, 191.25]
        self.assertArrayEqual(overlap.coord(axis="x").points, target)

    def test_non_horizontal_dimensions_congruent_grid(self):
        # Dimensions not mapping to the horizontal grid.
        data = np.arange(8).reshape(2, 2, 2)
        source = stock.geodetic(data=data)
        grid = stock.geodetic((2, 2))
        overlap = extract_overlap(source, grid, fix_period=False, pad_width=0)
        # The two cubes should be equal but we cannot perform this check due
        # to an iris bug - instead we perform equality on array.
        # https://github.com/SciTools/iris/issues/2123
        # self.assertEqual(overlap, source)
        self.assertArrayEqual(overlap.data, source.data)


class TestExceptions(ants.tests.TestCase):
    def test_unexpected_slices(self):
        # Ensure we raise exception for case where multiple slices are
        # returned.  We could support this case, however we have no use
        # case driving a requirement for it at this time.
        source = stock.geodetic((6, 6))
        grid = stock.geodetic((3, 3))

        gs_patch = mock.patch(
            "ants.utils.cube.get_slices",
            return_value=[
                tuple([slice(0, 2), slice(0, 2)]),
                tuple([slice(2, 4), slice(2, 4)]),
                tuple([slice(4, 6), slice(4, 6)]),
            ],
        )
        msg = (
            "3 slices were found, expecting 1 or 2.  Currently no support "
            "for this case"
        )
        with gs_patch, self.assertRaisesRegex(RuntimeError, msg):
            extract_overlap(source, grid, pad_width=0)

    def test_split_geometries_unstitchable(self):
        # Ensure we raise an exception for the case where we cannot
        # represent a geographic area for extraction by a single geometry.
        source = stock.geodetic((4, 4), xlim=(-180, 180), ylim=(-60, 90))
        grid = stock.geodetic((4, 4), xlim=(178, 182), ylim=(-2, 2))

        tgt_crs = iris.coord_systems.RotatedGeogCS(
            72.1, 179.0, ellipsoid=ants.coord_systems.UM_SPHERE.crs
        )
        gx = grid.coord(axis="x")
        gx.coord_system = tgt_crs
        gx.units = None
        gy = grid.coord(axis="y")
        gy.coord_system = tgt_crs
        gy.units = None
        msg = f"""Proj4 has returned multiple geometries during
                    extraction, resulting in discontiguous extraction
                    which cannot be resolved. modulus: {gx.units.modulus}.
                    """
        with self.assertRaisesRegex(RuntimeError, msg):
            extract_overlap(source, grid, fix_period=False, pad_width=0)


if __name__ == "__main__":
    ants.tests.main()

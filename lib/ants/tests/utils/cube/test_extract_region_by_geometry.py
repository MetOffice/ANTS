# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import shapely
from ants.utils.cube import extract_region_by_geometry


class TestAll(ants.tests.TestCase):
    def setUp(self):
        # Construct a polygon that looks something like this:
        #       X
        #
        #  X         X
        #
        #  x         X
        #
        #       X
        points = [(-15, -10), (0, -20), (15, -10), (15, 10), (0, 20), (-15, 10)]
        self.polygon = shapely.Polygon(points)

        # Construct a 1 degree global cube
        self.source = ants.tests.stock.geodetic((180, 360))

        self.expected_slice_x = slice(152, 208)
        self.expected_slice_y = slice(57, 123)

        # region size, as calculated by diagonal distance across bounding box
        self.distance = 50.0

    def test_slices(self):
        """Test that the correct slices are identified for region extraction."""
        _, _, _, slices = extract_region_by_geometry(self.source, self.polygon)
        self.assertEqual(slices[0], self.expected_slice_y)
        self.assertEqual(slices[1], self.expected_slice_x)

    def test_region_cube(self):
        """Test that the region cube is correctly extracted from the source."""
        region_cube, _, _, _ = extract_region_by_geometry(self.source, self.polygon)
        expected_region_cube = self.source[self.expected_slice_y, self.expected_slice_x]
        self.assertEqual(region_cube, expected_region_cube)

    def test_extraction_geom(self):
        """Test that the region extraction geometry is calculated correctly."""
        _, extraction_geom, _, _ = extract_region_by_geometry(self.source, self.polygon)
        expected_extraction_geom = self.polygon.buffer(self.distance * 0.25)
        self.assertEqual(extraction_geom, expected_extraction_geom)

    def test_containment_geom(self):
        """Test that the region containment geometry is calculated correctly."""
        _, _, containment_geom, _ = extract_region_by_geometry(
            self.source, self.polygon
        )
        expected_containment_geom = self.polygon.buffer(self.distance * 0.02)
        self.assertEqual(containment_geom, expected_containment_geom)

    def test_dateline_crossing_failure(self):
        """
        Test that when a region to extract crosses the dateline, an exception is raised.

        In this case, the polygon itself doesn't cross the dateline, but the buffered
        extraction geometry does, so multiple slices are needed to extract the region.
        """
        points = [(170, 0), (179, 5), (165, 10)]
        polygon = shapely.Polygon(points)
        expected_msg = "Expecting 1 slice, got 2 slices"
        with self.assertRaisesRegex(RuntimeError, expected_msg):
            extract_region_by_geometry(self.source, polygon)

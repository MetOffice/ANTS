# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.coord_systems import WGS84_GEODETIC
from ants.fileformats.raster import _derive_coord


class TestDeriveCoord(ants.tests.TestCase):
    def setUp(self):
        self.origin_xy = (180.0, 90.0)
        self.pixel_width = (0.003, -10.0)
        self.num_xy = (4, 3)
        self.crs = WGS84_GEODETIC

    def test_x_coord_points(self):
        """Test that the x coordinate points have been derived correctly.

        The origin, pixel width and number have been chosen such that using
        np.arange gives the **wrong** number of points. np.linspace is used
        instead, see https://code.metoffice.gov.uk/trac/ancil/ticket/2547.
        """
        actual_coord = _derive_coord(
            ax_dir="x",
            origin_xy=self.origin_xy,
            pixel_width=self.pixel_width,
            num_xy=self.num_xy,
            crs=self.crs,
        )
        expected_points = np.array([180.0015, 180.0045, 180.0075, 180.0105])
        self.assertArrayAlmostEqual(actual_coord.points, expected_points)

    def test_x_coord_bounds(self):
        """Test that the x coordinate bounsd have been derived correctly.

        The origin, pixel width and number have been chosen such that using
        np.arange gives the **wrong** number of points. np.linspace is used
        instead, see https://code.metoffice.gov.uk/trac/ancil/ticket/2547.
        """
        actual_coord = _derive_coord(
            ax_dir="x",
            origin_xy=self.origin_xy,
            pixel_width=self.pixel_width,
            num_xy=self.num_xy,
            crs=self.crs,
        )
        expected_bounds = np.array(
            [
                [180.000, 180.003],
                [180.003, 180.006],
                [180.006, 180.009],
                [180.009, 180.012],
            ]
        )
        self.assertArrayAlmostEqual(actual_coord.bounds, expected_bounds)

    def test_x_coord_crs(self):
        """Test that the crs has been added to the x coordinate."""
        actual_coord = _derive_coord(
            ax_dir="x",
            origin_xy=self.origin_xy,
            pixel_width=self.pixel_width,
            num_xy=self.num_xy,
            crs=self.crs,
        )
        self.assertEqual(actual_coord.coord_system, self.crs.crs)

    def test_x_coord_metdata(self):
        """Test that the crs metadata has been added to the x coordinate."""
        actual_coord = _derive_coord(
            ax_dir="x",
            origin_xy=self.origin_xy,
            pixel_width=self.pixel_width,
            num_xy=self.num_xy,
            crs=self.crs,
        )
        self.assertEqual(actual_coord.standard_name, "longitude")
        self.assertEqual(actual_coord.units, "degrees")

    def test_y_coord_points(self):
        """Test that the y coordinate points have been derived correctly.

        The y coordinate direction is reversed: the origin y point provided to
        origin_xy will come at the end of the returned coordinate.
        """
        actual_coord = _derive_coord(
            ax_dir="y",
            origin_xy=self.origin_xy,
            pixel_width=self.pixel_width,
            num_xy=self.num_xy,
            crs=self.crs,
        )
        expected_points = np.array([65.0, 75.0, 85.0])
        self.assertArrayAlmostEqual(actual_coord.points, expected_points)

    def test_y_coord_bounds(self):
        """Test that the y coordinate bounds have been derived correctly.

        The y coordinate direction is reversed: the origin y point provided to
        origin_xy will come at the end of the returned coordinate.
        """
        actual_coord = _derive_coord(
            ax_dir="y",
            origin_xy=self.origin_xy,
            pixel_width=self.pixel_width,
            num_xy=self.num_xy,
            crs=self.crs,
        )
        expected_bounds = np.array([[60.0, 70.0], [70.0, 80.0], [80.0, 90.0]])
        self.assertArrayAlmostEqual(actual_coord.bounds, expected_bounds)

    def test_y_coord_crs(self):
        """Test that the crs has been added to the y coordinate."""
        actual_coord = _derive_coord(
            ax_dir="y",
            origin_xy=self.origin_xy,
            pixel_width=self.pixel_width,
            num_xy=self.num_xy,
            crs=self.crs,
        )
        self.assertEqual(actual_coord.coord_system, self.crs.crs)

    def test_y_coord_metdata(self):
        """Test that the crs metadata has been added to the y coordinate."""
        actual_coord = _derive_coord(
            ax_dir="y",
            origin_xy=self.origin_xy,
            pixel_width=self.pixel_width,
            num_xy=self.num_xy,
            crs=self.crs,
        )
        self.assertEqual(actual_coord.standard_name, "latitude")
        self.assertEqual(actual_coord.units, "degrees")

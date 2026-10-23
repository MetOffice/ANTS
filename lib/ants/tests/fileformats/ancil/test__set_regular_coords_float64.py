# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

# Some of this file has been edited using Met Office Github Copilot Enterprise.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.fileformats.ancil import RMDI, _set_regular_coords_float64
from iris.fileformats.pp import SplittableInt

# Expected values, for the header used in the tests below (see _Common).
#
# They are compared exactly: with the values chosen, the header calculation in
# float64 gives the same doubles as these literals.  None of the points is
# exactly representable in float32 (rounding changes them by up to ~3e-8), so
# any rounding to float32 along the way would make the comparison fail.  These
# small values do not show the iris-version dependence that prompted this
# code: that needs a large start value, and is tested in
# test_integration.py::TestRegularCoordPrecision.  If the header values are
# changed, check the literals are still exactly equal to the calculation.
LON_POINTS = np.array([0.11, 0.22, 0.33, 0.44, 0.55])
LAT_POINTS = np.array([0.22, 0.44, 0.66])
LON_HALF_STEP = 0.055
LAT_HALF_STEP = 0.11


def bounds_around(points, half_step):
    """
    Return the bounds half a step below and above each of the points.

    Expected bounds are defined this way, rather than as decimal literals,
    because a literal such as 0.165 is not the same double as 0.11 + 0.055.

    """
    return np.stack([points - half_step, points + half_step], axis=-1)


class _Common:
    """
    Fake UM field header and matching cube shared by all the tests.

    The header describes a regular grid of 3 rows (latitude) by 5 columns
    (longitude).  In the UM header, ``bz`` is the value *before* the first
    point, so the points are ``bz + bd``, ``bz + 2 * bd``, ... and the
    expected coordinates are:

    * longitude: 0.11, 0.22, 0.33, 0.44, 0.55
    * latitude: 0.22, 0.44, 0.66

    The two axes have different steps so that mixing them up is detected.

    The cube is built from the header (see ``make_cube``), so the two always
    describe the same grid.  Tests that change the header must build the cube
    again afterwards.

    """

    def setUp(self):
        self.field = mock.Mock(
            name="field",
            # Last digit 1: regular grid, points only (no bounds).
            lbcode=SplittableInt(1),
            lbnpt=5,
            lbrow=3,
            bzx=0.0,
            bdx=0.11,
            bzy=0.0,
            bdy=0.22,
            bmdi=RMDI,
        )
        self.field.coord_system.return_value = iris.coord_systems.GeogCS(6371229.0)
        self.cube = self.make_cube()

    def make_cube(self, lat_name="latitude", lon_name="longitude", with_bounds=False):
        """
        Return the cube that iris would build from the header in ``self.field``.

        By the time ANTS' callback runs, iris has already built the horizontal
        coordinates from the header, as float32.  So that the cube always
        agrees with the header (shape, coordinate system, points, and bounds if
        requested), the coordinates are the header's float64 points and bounds
        rounded to float32.

        """
        field = self.field
        crs = field.coord_system()
        coords = []
        for name, zero, step, count in (
            (lat_name, field.bzy, field.bdy, field.lbrow),
            (lon_name, field.bzx, field.bdx, field.lbnpt),
        ):
            points = (zero + step) + step * np.arange(count, dtype=np.float64)
            bounds = None
            if with_bounds:
                bounds = bounds_around(points, 0.5 * step).astype(np.float32)
            coords.append(
                iris.coords.DimCoord(
                    points.astype(np.float32),
                    bounds=bounds,
                    standard_name=name,
                    units="degrees",
                    coord_system=crs,
                )
            )
        cube = iris.cube.Cube(np.zeros((field.lbrow, field.lbnpt)))
        cube.add_dim_coord(coords[0], 0)
        cube.add_dim_coord(coords[1], 1)
        return cube


class TestPoints(_Common, ants.tests.TestCase):
    """Points are rebuilt in float64 from the header values."""

    def test_longitude_points(self):
        """The longitude points come from the header start and step."""
        _set_regular_coords_float64(self.cube, self.field)
        actual = self.cube.coord("longitude").points
        self.assertArrayEqual(actual, LON_POINTS)

    def test_latitude_points(self):
        """The latitude points come from the header start and step."""
        _set_regular_coords_float64(self.cube, self.field)
        actual = self.cube.coord("latitude").points
        self.assertArrayEqual(actual, LAT_POINTS)

    def test_points_are_float64(self):
        """Both horizontal coordinates end up as float64, not float32."""
        _set_regular_coords_float64(self.cube, self.field)
        self.assertEqual(np.float64, self.cube.coord("longitude").dtype)
        self.assertEqual(np.float64, self.cube.coord("latitude").dtype)

    def test_circular_flag_preserved(self):
        """Replacing the points keeps the coordinate's circular flag."""
        self.cube.coord("longitude").circular = True
        _set_regular_coords_float64(self.cube, self.field)
        self.assertTrue(self.cube.coord("longitude").circular)

    def test_rotated_pole_coordinates(self):
        """A rotated pole grid has its grid_latitude and grid_longitude rebuilt."""
        # lbcode 101: rotated pole version of the regular grid type 1.
        self.field.lbcode = SplittableInt(101)
        self.field.coord_system.return_value = iris.coord_systems.RotatedGeogCS(
            39.25, 198.0
        )
        self.cube = self.make_cube(lat_name="grid_latitude", lon_name="grid_longitude")
        _set_regular_coords_float64(self.cube, self.field)
        actual = self.cube.coord("grid_longitude").points
        self.assertArrayEqual(actual, LON_POINTS)
        self.assertEqual(np.float64, self.cube.coord("grid_latitude").dtype)


class TestBounds(_Common, ants.tests.TestCase):
    """Bounds are only produced when the header asks for them."""

    def setUp(self):
        super().setUp()
        # Last digit 2: regular grid, with bounds.  Iris has already given the
        # coordinates (placeholder) bounds in this case.
        self.field.lbcode = SplittableInt(2)
        self.cube = self.make_cube(with_bounds=True)

    def test_longitude_bounds(self):
        """Longitude bounds are half a header step either side of each point."""
        _set_regular_coords_float64(self.cube, self.field)
        actual = self.cube.coord("longitude").bounds
        self.assertArrayEqual(actual, bounds_around(LON_POINTS, LON_HALF_STEP))

    def test_latitude_bounds(self):
        """Latitude bounds are half a header step either side of each point."""
        _set_regular_coords_float64(self.cube, self.field)
        actual = self.cube.coord("latitude").bounds
        self.assertArrayEqual(actual, bounds_around(LAT_POINTS, LAT_HALF_STEP))

    def test_bounds_are_float64(self):
        """Bounds are float64, as the points are."""
        _set_regular_coords_float64(self.cube, self.field)
        self.assertEqual(np.float64, self.cube.coord("longitude").bounds.dtype)
        self.assertEqual(np.float64, self.cube.coord("latitude").bounds.dtype)

    def test_no_bounds_when_not_requested(self):
        """With a last lbcode digit of 1 no bounds are created."""
        self.field.lbcode = SplittableInt(1)
        self.cube = self.make_cube()
        _set_regular_coords_float64(self.cube, self.field)
        self.assertFalse(self.cube.coord("longitude").has_bounds())


class TestSinglePointAxis(_Common, ants.tests.TestCase):
    """
    An axis with a single point still gets header derived bounds.

    Iris builds the bounds of a one point axis from the header step, so this
    is the behaviour ANTS preserves.  ``ants.utils.coord.guess_bounds`` could
    not be used instead: it has no access to the header step, so it either
    raises (``strict=True``) or adds no bounds (``strict=False``) for a one
    point coordinate.

    """

    def setUp(self):
        super().setUp()
        self.field.lbnpt = 1
        self.cube = self.make_cube()

    def test_single_point_has_bounds_when_requested(self):
        """With a last lbcode digit of 2 a one point axis gets bounds."""
        self.field.lbcode = SplittableInt(2)
        self.cube = self.make_cube(with_bounds=True)
        _set_regular_coords_float64(self.cube, self.field)
        actual = self.cube.coord("longitude").bounds
        self.assertArrayEqual(actual, bounds_around(LON_POINTS[:1], LON_HALF_STEP))

    def test_single_point_has_no_bounds_when_not_requested(self):
        """With a last lbcode digit of 1 a one point axis gets no bounds."""
        _set_regular_coords_float64(self.cube, self.field)
        self.assertFalse(self.cube.coord("longitude").has_bounds())


class TestCoordinatesLeftUnchanged(_Common, ants.tests.TestCase):
    """Cases where iris' float32 coordinates must be left as they are."""

    def test_variable_resolution_axis(self):
        """
        An axis with no regular spacing in the header is left unchanged.

        For a variable resolution grid, ANTS sets the header spacing to the
        missing data indicator and iris takes the points from elsewhere, so
        there is nothing to rebuild.  The other (regular) axis is still
        converted.

        """
        self.field.bdx = RMDI
        _set_regular_coords_float64(self.cube, self.field)
        self.assertEqual(np.float32, self.cube.coord("longitude").dtype)
        self.assertEqual(np.float64, self.cube.coord("latitude").dtype)

    def test_cross_section(self):
        """
        A cross section (5 digit lbcode) is left unchanged.

        The final lbcode digit is a supported grid type (1), so only the
        number of digits identifies this as something other than a lat-lon grid.

        """
        self.field.lbcode = SplittableInt(10101)
        _set_regular_coords_float64(self.cube, self.field)
        self.assertEqual(np.float32, self.cube.coord("longitude").dtype)
        self.assertEqual(np.float32, self.cube.coord("latitude").dtype)

    def test_unsupported_grid_type(self):
        """A grid type other than 1 or 2 (here 3) is left unchanged."""
        self.field.lbcode = SplittableInt(3)
        _set_regular_coords_float64(self.cube, self.field)
        self.assertEqual(np.float32, self.cube.coord("longitude").dtype)
        self.assertEqual(np.float32, self.cube.coord("latitude").dtype)

    def test_unsupported_rotated_grid_type(self):
        """A rotated grid (leading 1) of type other than 1 or 2 is left unchanged."""
        self.field.lbcode = SplittableInt(103)
        _set_regular_coords_float64(self.cube, self.field)
        self.assertEqual(np.float32, self.cube.coord("longitude").dtype)
        self.assertEqual(np.float32, self.cube.coord("latitude").dtype)

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

# Some of this file has been edited using Met Office Github Copilot Enterprise.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.fileformats.ancil import _CallbackUM as CallbackUM
from iris.fileformats.pp import SplittableInt


@ants.tests.skip_mule
class Test___call__(ants.tests.TestCase):
    def setUp(self):
        self.cube = iris.cube.Cube([0])

        mock_headers = mock.Mock(name="Headers")
        mock_headers.fixed_length_header.grid_staggering = 3
        patch = mock.patch("mule.AncilFile.from_file", return_value=mock_headers)
        self.mock_ancilfv = patch.start()
        self.addCleanup(patch.stop)

        self.field = mock.Mock(
            name="field",
            lbcode=SplittableInt(1),
            lbnpt=5,
            lbrow=3,
            bzx=341.30499999999995,
            bdx=0.11,
            bzy=-0.2750000000000021,
            bdy=0.11,
            bmdi=-1073741824.0,
        )
        self.field.coord_system.return_value = None

    def call(self):
        CallbackUM({mock.sentinel.filename: 6}).__call__(
            self.cube, self.field, mock.sentinel.filename
        )

    def test_check_ppcallback_callable_called(self):
        pp_callback_callable = "ants.fileformats.pp._CallbackPP.__call__"

        with mock.patch(pp_callback_callable) as pp_call_mock:
            self.call()
        pp_call_mock.assert_called_once_with(
            self.cube, self.field, mock.sentinel.filename
        )

    def _regular_cube(self, with_bounds=False):
        # Mimic the float32 coordinates that iris generates for regular grids.
        y = iris.coords.DimCoord.from_regular(
            self.field.bzy,
            self.field.bdy,
            3,
            standard_name="latitude",
            units="degrees",
            with_bounds=with_bounds,
        )
        x = iris.coords.DimCoord.from_regular(
            self.field.bzx,
            self.field.bdx,
            5,
            standard_name="longitude",
            units="degrees",
            circular=True,
            with_bounds=with_bounds,
        )
        cube = iris.cube.Cube(np.zeros((3, 5)))
        cube.add_dim_coord(y, 0)
        cube.add_dim_coord(x, 1)
        self.cube = cube

    def test_regular_coords_float64(self):
        self._regular_cube()
        self.call()
        x = self.cube.coord("longitude")
        y = self.cube.coord("latitude")
        self.assertEqual(x.dtype, np.float64)
        self.assertArrayAlmostEqual(
            x.points, 341.305 + 0.11 * np.arange(1, 6), decimal=12
        )
        self.assertArrayAlmostEqual(
            y.points, -0.275 + 0.11 * np.arange(1, 4), decimal=12
        )
        self.assertTrue(x.circular)
        self.assertFalse(x.has_bounds())

    def test_regular_coords_bounds(self):
        self._regular_cube(with_bounds=True)
        self.field.lbcode = SplittableInt(2)
        self.call()
        x = self.cube.coord("longitude")
        self.assertEqual(x.bounds.dtype, np.float64)
        self.assertArrayAlmostEqual(x.bounds[:, 0], x.points - 0.055, decimal=12)
        self.assertArrayAlmostEqual(x.bounds[:, 1], x.points + 0.055, decimal=12)

    def _single_point_x_cube(self, with_bounds):
        self.field.lbnpt = 1
        self.field.bzx = -349.75
        self.field.bdx = 0.5
        y = iris.coords.DimCoord.from_regular(
            self.field.bzy,
            self.field.bdy,
            3,
            standard_name="latitude",
            units="degrees",
        )
        x = iris.coords.DimCoord.from_regular(
            self.field.bzx,
            self.field.bdx,
            1,
            standard_name="longitude",
            units="degrees",
            with_bounds=with_bounds,
        )
        cube = iris.cube.Cube(np.zeros((3, 1)))
        cube.add_dim_coord(y, 0)
        cube.add_dim_coord(x, 1)
        self.cube = cube

    def test_single_point_axis_bounds(self):
        # Iris derives bounds from the header step even for a single point,
        # which ants.utils.coord.guess_bounds cannot do.
        self._single_point_x_cube(with_bounds=True)
        self.field.lbcode = SplittableInt(2)
        self.call()
        x = self.cube.coord("longitude")
        self.assertEqual(x.dtype, np.float64)
        self.assertArrayAlmostEqual(x.points, [-349.25], decimal=12)
        self.assertArrayAlmostEqual(x.bounds, [[-349.5, -349.0]], decimal=12)

    def test_single_point_axis_no_bounds(self):
        self._single_point_x_cube(with_bounds=False)
        self.call()
        x = self.cube.coord("longitude")
        self.assertEqual(x.dtype, np.float64)
        self.assertArrayAlmostEqual(x.points, [-349.25], decimal=12)
        self.assertFalse(x.has_bounds())

    def test_rotated_names(self):
        self._regular_cube()
        for name in ("latitude", "longitude"):
            self.cube.coord(name).rename(f"grid_{name}")
        self.field.coord_system.return_value = iris.coord_systems.RotatedGeogCS(
            39.25, 198.0
        )
        self.call()
        self.assertEqual(self.cube.coord("grid_longitude").dtype, np.float64)

    def _assert_float32_untouched(self, *names):
        for name in names:
            before = self._before[name]
            coord = self.cube.coord(name)
            self.assertEqual(coord, before)
            self.assertEqual(coord.dtype, np.float32)

    def _remember_coords(self):
        self._before = {
            name: self.cube.coord(name).copy() for name in ("latitude", "longitude")
        }

    def test_irregular_axis_untouched(self):
        self._regular_cube()
        self._remember_coords()
        self.field.bdx = self.field.bmdi
        self.call()
        self._assert_float32_untouched("longitude")
        self.assertEqual(self.cube.coord("latitude").dtype, np.float64)

    def test_cross_section_untouched(self):
        # A 5 digit lbcode whose final digit would otherwise be a supported
        # horizontal grid type.
        self._regular_cube()
        self._remember_coords()
        self.field.lbcode = SplittableInt(10101)
        self.call()
        self._assert_float32_untouched("longitude", "latitude")

    def test_unsupported_grid_type_untouched(self):
        for lbcode in (3, 103):
            with self.subTest(lbcode=lbcode):
                self._regular_cube()
                self._remember_coords()
                self.field.lbcode = SplittableInt(lbcode)
                self.call()
                self._assert_float32_untouched("longitude", "latitude")

    def test_coord_length_mismatch_untouched(self):
        self._regular_cube()
        self._remember_coords()
        self.field.lbnpt = 7
        self.call()
        self._assert_float32_untouched("longitude")
        self.assertEqual(self.cube.coord("latitude").dtype, np.float64)

    def test_coord_not_a_dimension_coord_untouched(self):
        self._regular_cube()
        x = self.cube.coord("longitude")
        self.cube.remove_coord(x)
        self.cube.add_aux_coord(iris.coords.AuxCoord.from_coord(x), 1)
        self._remember_coords()
        self.call()
        self._assert_float32_untouched("longitude")
        self.assertEqual(self.cube.coord("latitude").dtype, np.float64)

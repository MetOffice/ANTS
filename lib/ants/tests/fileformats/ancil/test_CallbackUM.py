# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

#Some of this file has been edited using Met Office Github Copilot Enterprise.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.fileformats.ancil import _CallbackUM as CallbackUM


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
            lbcode=[1, 0, 0],
            lbnpt=5,
            lbrow=3,
            bzx=341.30499999999995,
            bdx=0.11,
            bzy=-0.2750000000000021,
            bdy=0.11,
            bmdi=-1073741824.0,
        )
        self.field.coord_system.return_value = None

    def call(self, field=None):
        CallbackUM({mock.sentinel.filename: 6}).__call__(
            self.cube, field or self.field, mock.sentinel.filename
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
        self.field.lbcode = [2, 0, 0]
        self.call()
        x = self.cube.coord("longitude")
        self.assertEqual(x.bounds.dtype, np.float64)
        self.assertArrayAlmostEqual(x.bounds[:, 0], x.points - 0.055, decimal=12)
        self.assertArrayAlmostEqual(x.bounds[:, 1], x.points + 0.055, decimal=12)

    def test_rotated_names(self):
        self._regular_cube()
        for name in ("latitude", "longitude"):
            self.cube.coord(name).rename(f"grid_{name}")
        self.field.coord_system.return_value = iris.coord_systems.RotatedGeogCS(
            39.25, 198.0
        )
        self.call()
        self.assertEqual(self.cube.coord("grid_longitude").dtype, np.float64)

    def test_irregular_axis_untouched(self):
        self._regular_cube()
        self.field.bdx = self.field.bmdi
        before = self.cube.coord("longitude").copy()
        self.call()
        self.assertEqual(self.cube.coord("longitude"), before)
        self.assertEqual(self.cube.coord("latitude").dtype, np.float64)

    def test_cross_section_untouched(self):
        self._regular_cube()
        self.field.lbcode = [10101, 0, 0, 0, 0]
        before = self.cube.coord("longitude").copy()
        self.call()
        self.assertEqual(self.cube.coord("longitude"), before)

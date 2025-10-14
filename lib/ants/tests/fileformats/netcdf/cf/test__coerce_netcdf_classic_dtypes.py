# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants
import ants.tests
import iris
import numpy as np
from ants.fileformats.netcdf.cf import _coerce_netcdf_classic_dtypes


class TestAll(ants.tests.TestCase):
    def test_no_coerce(self):
        cube = ants.tests.stock.geodetic((2, 2))
        with mock.patch("numpy.can_cast") as can_cast:
            _coerce_netcdf_classic_dtypes(cube)
        self.assertFalse(can_cast.called)
        # We don't coerce so cube data should remain its original non-lazy self.
        self.assertFalse(cube.has_lazy_data())

    def test_dim_coord_points_coerce(self):
        cube = ants.tests.stock.geodetic((2, 2))
        coord = cube.coord(axis="x")
        coord.points = coord.points.astype("uint8")
        _coerce_netcdf_classic_dtypes(cube)
        self.assertEqual(coord.dtype, "i2")
        # Dim coords aren't lazy as they have to pass monotonicity checks on
        # initialisation - so will return False.
        self.assertFalse(coord.has_lazy_points())

    def test_dim_coord_bounds_coerce(self):
        cube = ants.tests.stock.geodetic((2, 2), xlim=[0, 90])
        coord = cube.coord(axis="x")
        coord.bounds = coord.bounds.astype("uint16")
        _coerce_netcdf_classic_dtypes(cube)
        self.assertEqual(coord.bounds_dtype, "i4")
        # Dim coords aren't lazy as they have to pass monotonicity checks on
        # initialisation - so will return False.
        self.assertFalse(coord.has_lazy_bounds())

    def test_aux_coord_points_coerce(self):
        cube = ants.tests.stock.geodetic((2, 2))
        coord = cube.coord(axis="x")
        coord.points = coord.points.astype("uint8")

        # Turn dim coord into an aux coord
        cube.remove_coord(coord)
        cube.add_aux_coord(iris.coords.AuxCoord.from_coord(coord), 1)
        coord = cube.coord(axis="x")

        _coerce_netcdf_classic_dtypes(cube)
        self.assertEqual(coord.dtype, "i2")
        self.assertTrue(coord.has_lazy_points())

    def test_aux_coord_bounds_coerce(self):
        cube = ants.tests.stock.geodetic((2, 2), xlim=[0, 90])
        coord = cube.coord(axis="x")
        coord.bounds = coord.bounds.astype("uint16")

        # Turn dim coord into an aux coord
        cube.remove_coord(coord)
        cube.add_aux_coord(iris.coords.AuxCoord.from_coord(coord), 1)
        coord = cube.coord(axis="x")

        _coerce_netcdf_classic_dtypes(cube)
        self.assertEqual(coord.bounds_dtype, "i4")
        self.assertTrue(coord.has_lazy_bounds())

    def test_data_coerce(self):
        cube = ants.tests.stock.geodetic((2, 2))
        cube.data = cube.data.astype("bool")
        _coerce_netcdf_classic_dtypes(cube)
        self.assertEqual(cube.dtype, "i1")
        self.assertTrue(cube.has_lazy_data())

    def test_unsafe_coerce(self):
        cube = ants.tests.stock.geodetic((2, 2))
        limits = np.iinfo(np.uint64)
        cube.data = cube.data.astype("uint64")
        cube.data[:] = limits.max
        # We don't coerce so cube data should remain its original non-lazy self.
        self.assertFalse(cube.has_lazy_data())
        msg = "Cannot safely re-cast uint64 array to "
        with self.assertRaisesRegex(OverflowError, msg):
            _coerce_netcdf_classic_dtypes(cube)

    def test_bool(self):
        data = np.zeros((2, 2), dtype="bool")
        cube = ants.tests.stock.geodetic(data=data)
        _coerce_netcdf_classic_dtypes(cube)
        self.assertEqual(cube.data.dtype, np.int8)
        self.assertEqual(cube.attributes["valid_range"], [0, 1])

    def test_unsigned_handling(self):
        data = np.zeros((2, 2), dtype="uint8")
        cube = ants.tests.stock.geodetic(data=data)
        _coerce_netcdf_classic_dtypes(cube)
        self.assertEqual(cube.data.dtype, np.int16)
        self.assertEqual(cube.attributes["valid_range"], [0, 255])


if __name__ == "__main__":
    ants.tests.main()

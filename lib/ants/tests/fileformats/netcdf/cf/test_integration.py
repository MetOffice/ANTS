# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import tempfile
from unittest import mock

import ants
import ants.io.save
import ants.tests
import ants.tests.stock


class TestAll(ants.tests.TestCase):
    def test_netcdf_classic_int64_coordinates(self):
        # NETCDF_CLASSIC does not support 64bit integer coordinates, ensure
        # that we can handle them.
        cube = ants.tests.stock.geodetic((2, 2))
        coord = cube.coord(axis="x")
        coord.points = coord.points.astype("int64")
        fh = tempfile.NamedTemporaryFile()
        self.assertIsNone(ants.io.save.netcdf(cube, fh.name))

    def test_netcdf_classic_int64_data(self):
        # NETCDF_CLASSIC does not support 64bit integer data, ensure
        # that we can handle them (via iris).
        cube = ants.tests.stock.geodetic((2, 2))
        cube.data = cube.data.astype("int64")
        fh = tempfile.NamedTemporaryFile()
        self.assertIsNone(ants.io.save.netcdf(cube, fh.name))

    @ants.tests.enable_all_lazy_data
    def test_netcdf_classic_int64_lazy_data(self):
        # Confirm that Iris is now saving lazy int64
        # data to NETCDF_CLASSIC without error.
        cube = ants.tests.stock.geodetic((2, 2))
        cube = ants.utils.cube.defer_cube(cube)
        cube.data = cube.core_data().astype("int64")
        fh = tempfile.NamedTemporaryFile()
        self.assertTrue(cube.has_lazy_data())
        self.assertIsNone(ants.io.save.netcdf(cube, fh.name))

    def test_fill_value_argument_passed_to_iris(self):
        """Check fill value is passed through to the iris save call."""
        cube = ants.tests.stock.geodetic((2, 2))
        with mock.patch("ants.io.save.iris.save") as mock_iris_save:
            ants.io.save.netcdf(cube, "foo.nc", fill_value=-1)
        mock_iris_save.assert_called_once_with(
            cube,
            "foo.nc",
            saver="nc",
            netcdf_format="NETCDF4_CLASSIC",
            local_keys=None,
            unlimited_dimensions=None,
            zlib=False,
            complevel=4,
            fill_value=-1,
        )

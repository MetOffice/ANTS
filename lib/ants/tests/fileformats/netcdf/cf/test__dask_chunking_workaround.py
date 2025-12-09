# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import copy
from unittest import mock

import ants.tests
import ants.tests.stock
from ants.fileformats.netcdf.cf import _iris_dask_chunking_workaround


class TestAll(ants.tests.TestCase):
    @ants.tests.enable_all_lazy_data
    def test_innermost_dimension_is_single_chunk(self):
        # Dask defines "chunks" to refer to the size of each chunk, not the
        # number of chunks.  So a dimension of 10 cells could have chunks of:
        #
        # (10, ), i.e. a single chunk,
        # (5, 5, ) i.e. 2 equally sized chunks,
        # (4, 4, 2) for 3 chunks
        # ...etc.
        #
        # This means for a dimension of 10 cells, the expected chunks would be
        # a value of (10, ) for a single chunk for the whole dimension.
        expected = (10,)

        cube = ants.tests.stock.geodetic((2, 10))
        cube = ants.utils.cube.defer_cube(cube)
        assert cube.has_lazy_data()
        # And now set the chunking to 1 cell chunks in the outer dimension,
        # and 5 cell chunks in the inner dimension:
        cube.data = cube.core_data().rechunk((1, 5))
        assert cube.core_data().chunks == ((1, 1), (5, 5))

        _iris_dask_chunking_workaround(cube)
        actual = cube.core_data().chunks[-1]

        self.assertEqual(actual, expected)

    @ants.tests.enable_all_lazy_data
    def test_workaround_does_not_realise_data(self):
        expected = True

        cube = ants.tests.stock.geodetic((2, 2))
        cube = ants.utils.cube.defer_cube(cube)
        assert cube.has_lazy_data()

        _iris_dask_chunking_workaround(cube)
        actual = cube.has_lazy_data()

        self.assertEqual(actual, expected)

    @ants.tests.enable_all_lazy_data
    def test_dask_rechunking_enabled_by_default(self):
        cube = ants.tests.stock.geodetic((2, 2))
        cube = ants.utils.cube.defer_cube(cube)
        with mock.patch("ants.fileformats.netcdf.cf._rechunk") as mock_rechunk:
            _iris_dask_chunking_workaround(cube)
        mock_rechunk.assert_called_once_with(cube)

    def test_dask_rechunking_disabled_by_config(self):
        cube = ants.tests.stock.geodetic((2, 2))
        cube = ants.utils.cube.defer_cube(cube)

        # Mock out config so changes are isolated to this test.
        stub_config = copy.copy(ants.config.GlobalConfiguration())
        stub_config.__init__()
        stub_config["ants_tuning"]["disable_rechunking"] = "True"
        with mock.patch("ants.fileformats.netcdf.cf.CONFIG", new=stub_config):
            with mock.patch("ants.fileformats.netcdf.cf._rechunk") as mock_rechunk:
                _iris_dask_chunking_workaround(cube)
        mock_rechunk.assert_not_called()

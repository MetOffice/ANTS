# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import os
import tempfile
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
import scipy.sparse
from ants.regrid.esmf import ConservativeESMF


class Common1D(object):
    def setUp(self):
        """
        source / (unknown)                  (latitude: 4; longitude: 5)
             Dimension coordinates:
                  latitude                         x             -
                  longitude                        -             x

        target / (unknown)                  (-- : 2; grid_latitude: 16; \
                grid_longitude: 16)
             Dimension coordinates:
                  grid_latitude                 -                 x     \
                          -
                  grid_longitude                -                 -     \
                          x
             Auxiliary coordinates:
                  charlie                       x                 x     \
                          -

        """
        # We patch the cache filename to ensure there is no collision when
        # running these tests with multiprocessing (these tests use common
        # source-target pairs).

        tmpf = tempfile.NamedTemporaryFile(suffix=".nc")
        tmpf.close()
        patch = mock.patch(
            "ants.regrid.esmf.ESMFRegridder._gen_cache_filename",
            return_value=tmpf.name,
        )
        self.cache_filename_patch = patch.start()
        self.addCleanup(patch.stop)

        src_cube = ants.tests.stock.geodetic((4, 5))
        src_cube.data = src_cube.data.astype("float64")
        src_cube.rename("source")
        self.src = src_cube

        tgt_cube = ants.tests.stock.geodetic((2, 16, 16))
        tx, ty = tgt_cube.coord(axis="x"), tgt_cube.coord(axis="y")
        tcrs = iris.coord_systems.RotatedGeogCS(
            ellipsoid=iris.coord_systems.GeogCS(6371229.0),
            grid_north_pole_latitude=10,
            grid_north_pole_longitude=20,
        )
        tx.coord_system = tcrs
        ty.coord_system = tcrs
        tx.standard_name = "grid_longitude"
        ty.standard_name = "grid_latitude"
        aux_coord = iris.coords.AuxCoord(
            np.arange(32).reshape((2, 16)), long_name="charlie"
        )
        tgt_cube.add_aux_coord(aux_coord, (0, 1))
        tgt_cube.rename("target")
        self.tgt = tgt_cube

        self.scheme = ConservativeESMF()


@ants.tests.skip_esmpy
class Test_regridder_1D(Common1D, ants.tests.TestCase):
    def test_nochange(self):
        """Ensure no expensive calculation if it's not needed."""
        with mock.patch("esmpy.api.regrid.Regrid") as patch_esmpy_regrid:
            regridder = self.scheme.regridder(self.src, self.src)
            regridder(self.src)
        self.assertFalse(patch_esmpy_regrid.called)

    def test_grid_latitude_coordinate(self):
        """Check expected grid latitude."""
        expected = self.tgt.coord("grid_latitude")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.coord("grid_latitude")

        self.assertEqual(actual, expected)

    def test_grid_longitude_coordinate(self):
        """Check expected grid longitude."""
        expected = self.tgt.coord("grid_longitude")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.coord("grid_longitude")

        self.assertEqual(actual, expected)

    def test_data(self):
        """Check data payload."""
        source_areas = iris.analysis.cartography.area_weights(self.src)
        expected = self.src.collapsed(
            ["latitude", "longitude"], iris.analysis.MEAN, weights=source_areas
        )

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        result_areas = iris.analysis.cartography.area_weights(result)
        actual = result.collapsed(
            ["grid_latitude", "grid_longitude"],
            iris.analysis.MEAN,
            weights=result_areas,
        )

        self.assertArrayAlmostEqual(actual.data, expected.data, decimal=2)

    def test_alt_mapping(self):
        # Ensure that the ordering of the coordinates has no impact on the
        # results.
        input_cube = self.src.copy()
        input_cube.rename("input_cube")

        self.src.transpose((1, 0))
        self.tgt.transpose((1, 0, 2))
        msg = "Currently only increasing rank dimension mappings are " "supported."
        with self.assertRaisesRegex(RuntimeError, msg):
            regridder = self.scheme.regridder(self.src, self.tgt)
            regridder(input_cube)

    def test_attributes_persisting(self):
        # Certain atttributes from the source should persist to the target
        # cube.
        self.src.attributes = {"grid_staggering": 3, "valid_min": 0}
        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        atts = {"grid_staggering": 3}
        self.assertEqual(result.attributes, atts)

    def test_ants_set_crs_called(self):
        # Check that ants set_crs is called.  This ensure that coordinate
        # metadata checks are performed; missing coordinate systems are
        # fixed where possible and also ANTS crs equivalence is utilised.
        #
        # src, tgt and input cube should call this.
        new_src = self.src.copy()
        new_src.rename("new_source")
        with mock.patch("ants.utils.cube.set_crs") as patch_set_crs:
            regridder = self.scheme.regridder(self.src, self.tgt)
            regridder(new_src)
        mock.call(self.src) in patch_set_crs.call_args_list
        mock.call(self.tgt) in patch_set_crs.call_args_list
        mock.call(new_src) in patch_set_crs.call_args_list

    def test_values_beyond_extent(self):
        # Check what happens for points where there are target cells where no
        # source cells contribute to i.e. where there is not 100% coverage
        # of the target grid by the source grid.
        #
        # This does not capture the desired behaviour (which is NaN
        # values).  Instead this captures the behaviour that is coded
        # right now.  This current behaviour is that 'extrapolated points'
        # result in values of ~0.
        src_cube = ants.tests.stock.geodetic((4, 5), xlim=[0, 180])
        src_cube.data = src_cube.data + 10
        src_cube.data = src_cube.data.astype("float64")
        src_cube.rename("source")

        regridder = self.scheme.regridder(src_cube, self.tgt)
        result = regridder(src_cube)
        self.assertTrue((result.data == 0).sum() > 0)

    def test_masked_data(self):
        self.src.data = np.ma.array(self.src.data)
        self.src.data[0] = np.ma.masked
        tgt_cube = ants.tests.stock.geodetic((32, 32))

        regridder = self.scheme.regridder(self.src, tgt_cube)
        result = regridder(self.src)
        self.assertTrue(np.all(result.data.mask[0:7]))
        # We are intentionally not checking the boundary between masked an
        # unmasked values as these will be masked and unmasked based on
        # calculation error of great circle distances.
        self.assertTrue(np.all(~result.data.mask[9:]))

    def test_result_dtype_always_64bit(self):
        # Ensure that the resulting dtype is independent of properties of
        # either source or target.
        self.src.data = self.src.data.astype("int32")
        coords = [
            self.src.coord(axis="x"),
            self.src.coord(axis="y"),
            self.tgt.coord(axis="x"),
            self.tgt.coord(axis="y"),
        ]
        for coord in coords:
            coord.points = coord.points.astype("int32")
            coord.bounds = coord.bounds.astype("int32")
        self.src.data = self.src.data.astype("int32")
        self.tgt.data = self.tgt.data.astype("int32")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)

        self.assertEqual(result.data.dtype, np.dtype("float64"))
        self.assertEqual(result.coord(axis="x").bounds.dtype, np.dtype("int32"))
        self.assertEqual(result.coord(axis="y").bounds.dtype, np.dtype("int32"))

    def broadcasting_check(self, coords, dims):
        data = np.arange(20).reshape((4, 5))[None]
        data = np.repeat(data, 6, 0).reshape((2, 3, 4, 5))
        src_cube = ants.tests.stock.geodetic((2, 3, 4, 5), data=data)

        for coord, dim in zip(coords, dims):
            src_cube.add_aux_coord(coord, dim)
        src_cube.rename("source")

        scheme = ConservativeESMF()
        regridder = scheme.regridder(src_cube, self.tgt)
        result = regridder(src_cube)

        # The target is derived from a single regridded slice.
        src = src_cube[0, 0]
        src.remove_coord("bing")
        try:
            src.remove_coord("flop")
        except iris.exceptions.CoordinateNotFoundError:
            pass
        regridder = scheme.regridder(src, self.tgt)
        target = regridder(src)
        target = target.data.copy()[None]
        target = np.repeat(target, 6, 0).reshape((2, 3, 16, 16))

        self.assertArrayAlmostEqual(result.data, target)

    def test_broadcasting_nd_aux_coords(self):
        bing_coord = iris.coords.AuxCoord(
            np.arange(6).reshape((2, 3)), long_name="bing"
        )
        flop_coord = iris.coords.AuxCoord(
            np.arange(6).reshape((2, 3)), long_name="flop"
        )
        self.broadcasting_check([bing_coord, flop_coord], [(0, 1), (0, 1)])

    def test_broadcasting_nd_aux_coord(self):
        bing_coord = iris.coords.AuxCoord(
            np.arange(6).reshape((2, 3)), long_name="bing"
        )
        self.broadcasting_check([bing_coord], [(0, 1)])

    def test_broadcasting_1d_aux_coords(self):
        bing_coord = iris.coords.AuxCoord(np.arange(2), long_name="bing")
        flop_coord = iris.coords.AuxCoord(np.arange(3), long_name="flop")
        self.broadcasting_check([bing_coord, flop_coord], [(0,), (1,)])

    def test_input_cube_different_to_source_cube(self):
        # Ensure that an exception is raised where the grid used to derive the
        # weights is not identical to the input provided for regridding.
        new_src = self.src.copy()
        new_src.rename("new_source")
        coord = new_src.coord(axis="x")
        coord.points = coord.points + 1
        regridder = self.scheme.regridder(self.src, self.tgt)
        msg = (
            "The provided source cube has a horizontal grid which is not "
            "identical to that used to derive the weights."
        )
        with self.assertRaisesRegex(ValueError, msg):
            regridder(new_src)

    def test_src_cube_additional_coords(self):
        # Ensure we raise an exception in the case where the source cube has
        # additional coordinates mapped to the same dimensions as the
        # horizontal grid.
        msg = r"Additional coordinate\(s\) vary along the horizontal mapping."
        bing_coord = iris.coords.AuxCoord(np.arange(4), long_name="bing")
        self.src.add_aux_coord(bing_coord, 0)
        with self.assertRaisesRegex(ValueError, msg):
            self.scheme.regridder(self.src, self.tgt)

    def test_inp_cube_additional_coords(self):
        # Ensure we raise an exception in the case where the input cube has
        # additional coordinates mapped to the same dimensions as the
        # horizontal grid.
        new_src = self.src.copy()
        msg = r"Additional coordinate\(s\) vary along the horizontal mapping."
        bing_coord = iris.coords.AuxCoord(np.arange(4), long_name="bing")
        regridder = self.scheme.regridder(self.src, self.tgt)
        new_src.add_aux_coord(bing_coord, 0)
        with self.assertRaisesRegex(ValueError, msg):
            regridder(new_src)


@ants.tests.skip_esmpy
class Test_cache(Common1D, ants.tests.TestCase):
    def test_values(self):
        src = self.src
        tgt = self.tgt
        regridder = self.scheme.regridder(src, tgt)
        target = regridder(src)
        columns, rows, weights = regridder.cache

        source_flattened = src.data.reshape(-1)
        result = target.copy(np.zeros(target.shape, dtype="float"))
        result_flattened = result.data.reshape(-1)

        # APPLY WEIGHTS - straight area weighted regrid
        for ind in range(rows.size):
            row = rows[ind]
            column = columns[ind]
            result_flattened[row] = result_flattened[row] + (
                weights[ind] * source_flattened[column]
            )

        # Compare weights applied to ESMF applied cache results.
        self.assertArrayAlmostEqual(result.data, target.data)

    def test_values_using_sparse_arrays(self):
        # Check usage with sparse arrays.
        src = self.src
        tgt = self.tgt
        regridder = self.scheme.regridder(src, tgt)
        target = regridder(src)
        columns, rows, weights = regridder.cache

        result = target.copy(np.zeros(target.shape, dtype="float"))
        sparse_array = scipy.sparse.coo_matrix(
            (weights, (rows, columns)),
            shape=(np.prod([tgt.data.shape[1], tgt.data.shape[2]]), src.data.size),
        ).tocsc()
        result.data.reshape(-1)[:] = sparse_array * src.data.reshape(-1)

        # Compare weights applied to ESMPY applied cache results.
        self.assertArrayAlmostEqual(result.data, target.data)

    def test_cache_cleanup(self):
        regridder = self.scheme.regridder(self.src, self.tgt)
        cache_file = regridder._cache_fnme
        self.assertTrue(os.path.isfile(cache_file))
        del regridder
        self.assertFalse(os.path.isfile(cache_file))

    def test_cache_persistence(self):
        # Ensure that the file remains after getting rid of the regridder.
        regridder = self.scheme.regridder(self.src, self.tgt, persistent_cache=True)
        cache_file = regridder._cache_fnme
        self.assertTrue(os.path.isfile(cache_file))
        del regridder
        self.assertTrue(os.path.isfile(cache_file))
        os.remove(cache_file)

    def test_cache_persistence_regridder_usage(self):
        # Ensure that ESMF can successfully generate the same results when
        # utilising this cache to instantiate a regridder.
        regridder = self.scheme.regridder(self.src, self.tgt, persistent_cache=True)
        res1 = regridder(self.src)
        del regridder
        regridder = self.scheme.regridder(self.src, self.tgt, persistent_cache=False)
        res2 = regridder(self.src)
        self.assertArrayAlmostEqual(res1.data, res2.data)

    def test_cache_persistance_regridder_readfromfile(self):
        # Ensure that we are requesting that ESMF read the cache from disk for
        # instantiating its regridder in the case of persistent cache usage.
        regridder = self.scheme.regridder(self.src, self.tgt, persistent_cache=True)
        with mock.patch("esmpy.api.regrid.RegridFromFile") as cache_regrid:
            del regridder
            self.scheme.regridder(self.src, self.tgt, persistent_cache=False)
            self.assertTrue(cache_regrid.called)


class CommonND(object):
    def test_alt_mapping(self):
        input_cube = self.src.copy()
        input_cube.rename("input_cube")

        self.src.transpose((1, 0))
        self.tgt.transpose((1, 0))
        msg = "Currently only increasing rank dimension mappings are " "supported."
        with self.assertRaisesRegex(RuntimeError, msg):
            regridder = self.scheme.regridder(self.src, self.tgt)
            regridder(input_cube)


@ants.tests.skip_esmpy
class Test_regridder_1D_source_2D_target(CommonND, ants.tests.TestCase):
    def setUp(self):
        self.src = ants.tests.stock.geodetic((2, 3))

        crs = iris.coord_systems.RotatedGeogCS(20, 10)
        self.tgt = ants.tests.stock.gen_curvilinear_cube(crs, (4, 4))

        self.scheme = ConservativeESMF()

    def test_latitude_coordinate(self):
        """Check expected latitude."""
        expected = self.tgt.coord("latitude")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.coord("latitude")

        self.assertEqual(actual, expected)

    def test_longitude_coordinate(self):
        """Check expected longitude."""
        expected = self.tgt.coord("longitude")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.coord("longitude")

        self.assertEqual(actual, expected)

    def test_data(self):
        """Check data payload."""
        expected = np.array(
            [
                [1.43261933, 2.35197492, 1.07919774, 0.0],
                [1.91349803, 4.51747321, 2.6795686, 0.11329972],
                [1.72833981, 4.76524075, 3.45061807, 1.18936925],
                [2.92080226, 4.0, 4.0, 2.92080226],
            ]
        )

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.data

        self.assertArrayAlmostEqual(actual.data, expected.data)


@ants.tests.skip_esmpy
class Test_regridder_2D_source_1D_target(CommonND, ants.tests.TestCase):
    def setUp(self):
        crs = iris.coord_systems.RotatedGeogCS(20, 10)
        self.src = ants.tests.stock.gen_curvilinear_cube(crs, (2, 3))

        self.tgt = ants.tests.stock.geodetic((4, 4))
        self.scheme = ConservativeESMF()

    def test_latitude_coordinate(self):
        """Check expected latitude."""
        expected = self.tgt.coord("latitude")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.coord("latitude")

        self.assertEqual(actual, expected)

    def test_longitude_coordinate(self):
        """Check expected longitude."""
        expected = self.tgt.coord("longitude")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.coord("longitude")

        self.assertEqual(actual, expected)

    def test_data(self):
        """Check data payload."""
        expected = np.array(
            [
                [1.726662, 2.883659, 1.573794, 0.0],
                [1.755223, 4.334086, 3.129558, 0.133169],
                [1.266974, 4.589854, 3.461385, 1.32975],
                [2.699544, 4.0, 4.0, 3.116341],
            ]
        )

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.data

        self.assertArrayAlmostEqual(actual.data, expected.data)

    def test_src_cube_additional_coords(self):
        # Ensure we raise an exception in the case where the source cube has
        # additional coordinates mapped to the same dimensions as the
        # horizontal grid.
        msg = r"Additional coordinate\(s\) vary along the horizontal mapping."
        bing_coord = iris.coords.AuxCoord(np.arange(2), long_name="bing")
        self.src.add_aux_coord(bing_coord, 0)
        with self.assertRaisesRegex(ValueError, msg):
            self.scheme.regridder(self.src, self.tgt)


@ants.tests.skip_esmpy
class Test_regridder_2D_source_2D_target(CommonND, ants.tests.TestCase):
    def setUp(self):
        crs = iris.coord_systems.RotatedGeogCS(30, 10)
        self.src = ants.tests.stock.gen_curvilinear_cube(crs, (5, 5))

        crs = iris.coord_systems.RotatedGeogCS(20, 10)
        self.tgt = ants.tests.stock.gen_curvilinear_cube(crs, (4, 4))

        self.scheme = ConservativeESMF()

    def test_latitude_coordinate(self):
        """Check expected latitude."""
        expected = self.tgt.coord("latitude")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.coord("latitude")

        self.assertEqual(actual, expected)

    def test_longitude_coordinate(self):
        """Check expected longitude."""
        expected = self.tgt.coord("longitude")

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.coord("longitude")

        self.assertEqual(actual, expected)

    def test_data(self):
        """Check data payload."""
        expected = np.array(
            [
                [1.071448, 4.365377, 5.21863, 3.982292],
                [6.686008, 9.350128, 10.497595, 10.188842],
                [12.260536, 14.890911, 16.177303, 15.969216],
                [17.272277, 20.535876, 22.282553, 21.197149],
            ]
        )

        regridder = self.scheme.regridder(self.src, self.tgt)
        result = regridder(self.src)
        actual = result.data

        self.assertArrayAlmostEqual(actual.data, expected.data)


@ants.tests.skip_esmpy
class Test___del__(Common1D, ants.tests.TestCase):
    def test_usage(self):
        grid1 = mock.MagicMock(name="grid1")
        grid2 = mock.MagicMock(name="grid2")
        field1 = mock.MagicMock(name="field1")
        field2 = mock.MagicMock(name="field2")
        regrid_patch = mock.patch("esmpy.api.regrid.Regrid")
        grid_patch = mock.patch("esmpy.Grid", side_effect=[grid1, grid2])
        field_patch = mock.patch("esmpy.Field", side_effect=[field1, field2])
        tempfile_patch = mock.patch("tempfile.NamedTemporaryFile")
        os_patch = mock.patch("os.remove")
        with regrid_patch as rpatched:
            with grid_patch, field_patch, tempfile_patch, os_patch:
                regridder = self.scheme.regridder(self.src, self.tgt)
        del regridder
        for obj in [grid1, grid2, field1, field2, rpatched()]:
            self.assertTrue(obj.destroy.called)

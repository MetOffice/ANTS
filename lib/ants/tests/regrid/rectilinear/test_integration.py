# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest
import unittest.mock as mock
import warnings

import ants.regrid as regrid
import ants.tests
import ants.tests.stock as stock
import iris
import numpy as np


class _TestCommon(object):
    def check_attributes(self, cube, target_dict):
        self.assertEqual(cube.attributes.keys(), target_dict.keys())
        for key, value in cube.attributes.items():
            self.assertEqual(value, target_dict[key])


class TestIrisRegrid(ants.tests.TestCase):
    """Tests which ensure behaviour is maintained between iris versions."""

    def setUp(self):
        self.source = stock.geodetic((2, 2))
        self.target = stock.geodetic((2, 2))

    def assert_bilinear_dtype(self, src_dtype, tgt_dtype, exp_dtype):
        self.source.data = self.source.data.astype(src_dtype)
        self.target.data = self.target.data.astype(tgt_dtype)
        result = self.source.regrid(self.target, iris.analysis.Linear())
        self.assertEqual(result.data.dtype, np.dtype(exp_dtype))

    @unittest.expectedFailure
    def test_bilinear_uint8_source_int8_target(self):
        # Currently iris bilinear promotes those with kind 'i' exclusively.
        # https://github.com/SciTools/iris/issues/2058
        # If/when this test passes, we can re-evaluate whether we promote 16bit
        # floats ourselves which is currently done to circumvents the issue.
        self.assert_bilinear_dtype("uint8", "int8", "float16")

    def test_bilinear_int8_source_int8_target(self):
        self.assert_bilinear_dtype("int8", "int8", "float16")

    def test_bilinear_float16_source_int8_target(self):
        self.assert_bilinear_dtype("float16", "int8", "float16")

    def test_bilinear_int8_source_float16_target(self):
        self.assert_bilinear_dtype("int8", "float16", "float16")

    def test_dtype_handling(self):
        # Ensure that passing a source int8 vs float16 returns the same
        # result.
        self.source.data = self.source.data.astype("int8")
        result1 = self.source.regrid(self.target, iris.analysis.Linear())

        self.source.data = self.source.data.astype("float16")
        result2 = self.source.regrid(self.target, iris.analysis.Linear())

        self.assertArrayEqual(result1.data, result2.data)


class TestTwoStage(_TestCommon, ants.tests.TestCase):
    def test_warning(self):
        # Note that area weighted regridding within iris masks grid cells which
        # even slightly extend beyond the source extent, see iris github #1752.
        expected_warning = "NaN values introduced by extrapolation"
        source = stock.osgb((50, 50), xlim=(0, 6e5), ylim=(0, 12e5))
        target = stock.geodetic((50, 50), xlim=(-10, 10), ylim=(45, 65))
        with self.assertWarnsRegex(UserWarning, expected_warning):
            source.regrid(target, regrid.rectilinear.TwoStage())

    def test_attributes(self):
        # Check attributes persistance
        source = stock.osgb((2, 2), xlim=(0, 6e5), ylim=(0, 12e5))
        source.attributes = {"grid_staggering": 3, "valid_min": 0}
        target = stock.geodetic((2, 2), xlim=(-10, 10), ylim=(45, 65))
        with warnings.catch_warnings():
            # Ignore extrapolation warning - it's tested above, but this test
            # is interested in the cube attributes instead.
            warnings.filterwarnings(
                "ignore", "NaN values introduced by extrapolation", UserWarning
            )
            result = source.regrid(target, regrid.rectilinear.TwoStage())

        target = {"grid_staggering": 3}
        self.check_attributes(result, target)


class TestAreaWeighted(_TestCommon, ants.tests.TestCase):
    def setUp(self):
        self.source = stock.geodetic((2, 2))
        self.target = stock.geodetic((2, 2))

        purturbation = 1e-12
        self.source2 = self.source.copy()
        points = self.source2.coord(axis="x").points
        self.source2.coord(axis="x").points = points + purturbation

    def test_success(self):
        regridder = regrid.rectilinear.AreaWeighted().regridder(
            self.source, self.target
        )
        regridder(self.source2)

    def test_failure(self):
        # If this test fails then iris AreaWeighted regrid cache usage now
        # supports tolerant grid comparison.
        # This means that we can then remove
        # ants.regrid.rectilinear._override_coord_data
        regridder = iris.analysis.AreaWeighted().regridder(self.source, self.target)
        msg = "The given cube is not defined on the same source grid as this regridder"
        with self.assertRaisesRegex(ValueError, msg):
            regridder(self.source2)

    def test_lazy_data_type_promotion(self):
        initial_type = "int32"
        expected_type = "float64"

        self.assertTrue(self.source.dtype == initial_type)
        regridder = regrid.rectilinear.AreaWeighted().regridder(
            self.source, self.target
        )
        result = regridder(self.source)
        self.assertTrue(result.dtype == expected_type)
        self.assertTrue(result.has_lazy_data)


class TestLinear_regridder(_TestCommon, ants.tests.TestCase):
    def setUp(self):
        self.source = stock.geodetic((2, 2))
        self.target = stock.geodetic((2, 2))

    def test_homogenise(self):
        # Ensure that we homogenise coordinates.
        crs = ants.coord_systems.WGS84_GEODETIC.crs
        self.source.coord(axis="x").coord_system = crs
        self.source.coord(axis="y").coord_system = crs
        regridme = self.source.copy()

        patch_regrid_call = mock.patch("iris.analysis.RectilinearRegridder.__call__")
        with patch_regrid_call as mock_rect:
            scheme = regrid.rectilinear.Linear()
            regridder = scheme.regridder(self.source, self.target)
            regridder(regridme)

        tgt_crs = ants.coord_systems.UM_SPHERE.crs
        self.assertTrue(mock_rect.called)
        res_cube = mock_rect.call_args[0][0]
        self.assertEqual(res_cube.coord(axis="x").coord_system, tgt_crs)
        self.assertEqual(res_cube.coord(axis="y").coord_system, tgt_crs)

    def test_api(self):
        result = self.source.regrid(self.target, regrid.rectilinear.Linear())
        self.assertIsNotNone(result)

    def test_attributes(self):
        # Check attribute persistence
        self.source.attributes = {"grid_staggering": 3, "valid_min": 0}
        result = self.source.regrid(self.target, regrid.rectilinear.Linear())
        target = {"grid_staggering": 3}
        self.check_attributes(result, target)


class TestLinear_interpolator(_TestCommon, ants.tests.TestCase):
    def setUp(self):
        self.source = stock.geodetic((2, 2))

    def interpolate(self):
        interpolator = regrid.rectilinear.Linear().interpolator(
            self.source, ["latitude", "longitude"]
        )
        return interpolator([0, 0])

    def test_homogenise(self):
        # Ensure that we homogenise coordinates.
        crs = ants.coord_systems.WGS84_GEODETIC.crs
        self.source.coord(axis="x").coord_system = crs
        self.source.coord(axis="y").coord_system = crs

        result = self.interpolate()
        tgt_crs = ants.coord_systems.UM_SPHERE.crs
        self.assertEqual(result.coord(axis="x").coord_system, tgt_crs)
        self.assertEqual(result.coord(axis="y").coord_system, tgt_crs)

    def test_api(self):
        # Ensure that the interpolator still works as expected.
        self.assertEqual(self.interpolate().data, 1.5)

    def test_attributes(self):
        # Check attribute persistance
        self.source.attributes = {"grid_staggering": 3, "valid_min": 0}
        result = self.interpolate()
        target = {"grid_staggering": 3}
        self.check_attributes(result, target)

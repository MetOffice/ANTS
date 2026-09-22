# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import contextlib
import unittest.mock as mock
import warnings

import ants.tests
import ants.tests.stock as stock
import iris.coord_systems
import numpy as np
from ants.regrid.iris_esmf import IrisESMFAreaWeighted, _IrisESMFAreaWeightedRegridder


@contextlib.contextmanager
def _silence_experimental_warning():
    """Context manager silencing the "Experimental" scheme warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


class TestIrisESMFAreaWeighted(ants.tests.TestCase):
    def test_experimental_warning(self):
        with self.assertWarnsRegex(
            UserWarning, "Experimental, for evaluation purposes only"
        ):
            IrisESMFAreaWeighted()

    def test_default_mdtol(self):
        with _silence_experimental_warning():
            scheme = IrisESMFAreaWeighted()
        self.assertEqual(scheme.mdtol, 1.0)

    def test_mdtol_forwarded(self):
        with _silence_experimental_warning():
            scheme = IrisESMFAreaWeighted(mdtol=0.5)
        self.assertEqual(scheme.mdtol, 0.5)

    def test_no_extrapolation_kwarg_supported(self):
        with _silence_experimental_warning():
            with self.assertRaises(TypeError):
                IrisESMFAreaWeighted(extrapolation_mode="nan")

    def test_regridder_returns_wrapper(self):
        with _silence_experimental_warning():
            scheme = IrisESMFAreaWeighted(mdtol=0.5)
        source = stock.geodetic((2, 2))
        target = stock.geodetic((2, 2))
        with mock.patch(
            "ants.regrid.iris_esmf._IrisESMFAreaWeightedRegridder"
        ) as patched:
            scheme.regridder(source, target)
        patched.assert_called_once_with(source, target, mdtol=0.5)

    def test_repr(self):
        with _silence_experimental_warning():
            scheme = IrisESMFAreaWeighted(mdtol=0.5)
        self.assertEqual(repr(scheme), "IrisESMFAreaWeighted(mdtol=0.5)")


class TestImportGuard(ants.tests.TestCase):
    def test_raises_when_esmf_regrid_unavailable(self):
        with (
            mock.patch("ants.regrid.iris_esmf.esmf_regrid", None),
            mock.patch(
                "ants.regrid.iris_esmf._ESMF_REGRID_IMPORT_ERROR",
                ImportError("no esmf_regrid"),
            ),
        ):
            with self.assertRaises(ImportError):
                _IrisESMFAreaWeightedRegridder(
                    stock.geodetic((2, 2)), stock.geodetic((2, 2))
                )


class Common(object):
    def setUp(self):
        self.src = stock.geodetic((4, 5))
        self.src.data = self.src.data.astype("float64")
        self.tgt = stock.geodetic((8, 10))
        with _silence_experimental_warning():
            self.scheme = IrisESMFAreaWeighted()


@ants.tests.skip_esmf_regrid
class Test_regridder(Common, ants.tests.TestCase):
    def test_dtype_promotion(self):
        source = stock.geodetic((2, 2))
        target = stock.geodetic((2, 2))
        regridder = self.scheme.regridder(source, target)
        result = regridder(source)
        self.assertEqual(result.dtype, np.dtype("float64"))

    def test_outside_bounds_nan_fill(self):
        # Where the source domain does not cover the target domain (same
        # crs), target points outside the source domain should be NaN.
        source = stock.geodetic((4, 5), xlim=(-90, 90), ylim=(-45, 45))
        source.data = source.data.astype("float64")
        target = stock.geodetic((8, 10), xlim=(-180, 180), ylim=(-90, 90))
        regridder = self.scheme.regridder(source, target)
        result = regridder(source)
        self.assertTrue(np.isnan(result.data).any())
        self.assertFalse(np.ma.is_masked(result.data))

    def test_masked_data(self):
        source = stock.geodetic((4, 4))
        source.data = np.ma.masked_array(source.data.astype("float64"), mask=False)
        source.data.mask[0, 0] = True
        target = stock.geodetic((8, 8))
        regridder = self.scheme.regridder(source, target)
        result = regridder(source)
        self.assertTrue(np.ma.is_masked(result.data))

    def test_attributes(self):
        source = stock.geodetic((2, 2))
        source.attributes = {"grid_staggering": 3, "valid_min": 0}
        target = stock.geodetic((2, 2))
        regridder = self.scheme.regridder(source, target)
        result = regridder(source)
        self.assertEqual(result.attributes, {"grid_staggering": 3})

    def test_coordinate_tolerance(self):
        # The regridder should tolerate bit-level coordinate differences
        # between the cube it was built from and the cube it is called
        # with, unlike the underlying esmf_regrid/iris regridders.
        source = stock.geodetic((2, 2))
        target = stock.geodetic((2, 2))
        regridder = self.scheme.regridder(source, target)
        perturbed = source.copy()
        perturbed.coord(axis="x").points = perturbed.coord(axis="x").points + 1e-12
        result = regridder(perturbed)
        self.assertIsNotNone(result)

    def test_differing_crs_does_not_raise(self):
        # Unlike ants.regrid.rectilinear.TwoStage, this regridder has no
        # intermediate reprojection stage. ESMF regrids directly between
        # differing crs, but the NaN-fill-outside-bounds step (which
        # requires a common crs) should simply be skipped rather than
        # raising.
        source = self.src
        target = stock.geodetic((2, 16, 16))
        tx, ty = target.coord(axis="x"), target.coord(axis="y")
        tcrs = iris.coord_systems.RotatedGeogCS(
            ellipsoid=iris.coord_systems.GeogCS(6371229.0),
            grid_north_pole_latitude=10,
            grid_north_pole_longitude=20,
        )
        tx.coord_system = tcrs
        ty.coord_system = tcrs
        tx.standard_name = "grid_longitude"
        ty.standard_name = "grid_latitude"
        regridder = self.scheme.regridder(source, target)
        result = regridder(source)
        self.assertIsNotNone(result)

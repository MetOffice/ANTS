# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import iris
import numpy as np
from ants.analysis._merge import merge


class _Common(object):
    def setUp(self):
        self.primary = ants.tests.stock.geodetic((5, 5))
        data = np.zeros((5, 5))
        self.primary.data = data


class TestExceptions(_Common, ants.tests.TestCase):
    def test_diff_crs(self):
        # Ensure that we currently fall over for the case where the primary and
        # alternate datasets are defined with different coordinate systems.
        alternate = ants.tests.stock.osgb((5, 5))
        polygon = None
        msg = "Currently only same coordinate system merging supported"
        with self.assertRaisesRegex(RuntimeError, msg):
            merge(self.primary, alternate, polygon)

    def test_diff_grid(self):
        # Ensure that we raise an exception for the case where the horizontal
        # grid does not match.
        alternate = ants.tests.stock.geodetic((5, 5), xlim=(-45, 45))
        polygon = [[-40, -22], [60, -22], [60, 22], [-40, 22]]
        msg = (
            "Unable to define a unified grid covering the domain of both "
            "supplied cubes: Arrays are not compatible for merging"
        )
        with self.assertRaisesRegex(ValueError, msg):
            merge(self.primary, alternate, polygon)

    def test_diff_stash(self):
        self.primary.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi(
            "m01s00i001"
        )
        alternate = self.primary.copy()
        alternate.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i002")
        msg = "STASH attributes are not equal, m01s00i001 != m01s00i002"
        with self.assertRaisesRegex(ValueError, msg):
            merge(self.primary, alternate)

    def test_diff_standard_name(self):
        self.primary.standard_name = "air_pressure"
        alternate = self.primary.copy()
        alternate.standard_name = "air_pressure_anomaly"
        msg = "Cube standard_name do not match, air_pressure != " "air_pressure_anomaly"
        with self.assertRaisesRegex(ValueError, msg):
            merge(self.primary, alternate)

    def test_diff_units(self):
        alternate = self.primary.copy()
        alternate.units = 1
        msg = 'Cube "units" do not match, unknown != 1'
        with self.assertRaisesRegex(ValueError, msg):
            merge(self.primary, alternate)

    def test_domain_wholly_in_polygon(self):
        primary = ants.tests.stock.geodetic((5, 5), xlim=(-45, 45), ylim=(-45, 45))
        alternate = self.primary.copy()
        polygon = [[-180.0, -90.0], [180.0, -90.0], [180.0, 90.0], [-180.0, 90.0]]
        msg = "Target domain is wholly within the provided polygon"
        with self.assertRaisesRegex(RuntimeError, msg):
            merge(primary, alternate, polygon)


class TestValuesSameCRS(_Common, ants.tests.TestCase):
    def setUp(self):
        super(TestValuesSameCRS, self).setUp()
        self.alternate = self.primary.copy()
        self.alternate.data += 1

    def _merge_on_poly(self, primary, alternate, polyg):
        return merge(primary, alternate, polyg)

    def _aligned_to_grid_setup(self):
        # Define asymmetric polygon (to ensure no false positive attributed to
        # symmetry).
        polygon = [[-90, -45], [30, -45], [30, 45], [-90, 45]]
        target = self.alternate.data.copy()
        target[1:-1, 1:-2] = 0
        return polygon, target

    def test_polygon_aligned_to_grid(self):
        # Test a successful case where both primary and alternate are defined
        # on the same grid and polygon is aligned to the cell centres.
        polygon, target = self._aligned_to_grid_setup()
        res = self._merge_on_poly(self.primary, self.alternate, polygon)
        self.assertArrayEqual(res.data, target)

    def test_polygon_aligned_to_grid_different_dtype(self):
        # Ensure we correctly handle different data with different dtypes.
        polygon, target = self._aligned_to_grid_setup()
        alternate = self.alternate
        alternate.data.astype("int32")
        res = self._merge_on_poly(self.primary, alternate, polygon)
        self.assertArrayEqual(res.data, target)

    def test_polygon_aligned_to_grid_alternative_mapping(self):
        # Ensure that we correctly handle the case where x & y coordinates are
        # not mapped to the same dimension between primary and alternate cubes.
        polygon, target = self._aligned_to_grid_setup()
        self.primary.transpose((1, 0))
        res = self._merge_on_poly(self.primary, self.alternate, polygon)
        res.transpose((1, 0))
        self.assertArrayEqual(res.data, target)

    def test_polygon_unaligned_to_grid(self):
        # Test a successful case where both primary and alternate are defined
        # on the same grid and polygon has part cell coverage i.e. not aligned
        # to the cell centres.
        polygon = [[-40, -22], [40, -22], [40, 22], [-40, 22]]
        target = self.alternate.data.copy()
        target[1:-1, 1:-1] = 0
        res = self._merge_on_poly(self.primary, self.alternate, polygon)
        self.assertArrayEqual(res.data, target)

    def test_polygon_assymetric_on_grid(self):
        # Test a successful case where both primary and alternate are defined
        # on the same grid and polygon has part cell coverage i.e. not aligned
        # to the cell centres.
        polygon = [[45, 10], [120, 10], [120, 22], [45, 22]]
        target = self.alternate.data.copy()
        target = np.array(
            [
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
                [1, 1, 1, 0, 0],
                [1, 1, 1, 0, 0],
                [1, 1, 1, 1, 1],
            ]
        )
        res = self._merge_on_poly(self.primary, self.alternate, polygon)
        self.assertArrayEqual(res.data, target)

    def test_polygon_no_corner_overlap(self):
        # Capture the current behaviour, where no corner point within polygon
        # will result in no containment status of cell.
        polygon = [[45, 10], [80, 10], [80, 22], [45, 22]]
        target = self.alternate.data.copy()
        res = self._merge_on_poly(self.primary, self.alternate, polygon)
        self.assertArrayEqual(res.data, target)

    def test_grid_subset(self):
        # Ensure that we correctly handle the case where we have sources which
        # cover different areas of the same grid.  The result should return a
        # grid which contains the horizontal grid of both sources with the data
        # of both.
        alternate = self.primary
        self.primary = self.primary[1:-1, 1:-1]
        alternate.data[:] = 1
        polygon = [[-37, -19], [-35, -19], [-35, -17], [-37, -17]]
        res = self._merge_on_poly(self.primary, alternate, polygon)
        target = np.ma.array(
            [
                [1, 1, 1, 1, 1],
                [1, 0, 0, 1, 1],
                [1, 0, 0, 1, 1],
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
            ]
        )
        self.assertMaskedArrayAlmostEqual(res.data, target)

    def _detached_source(self):
        primary = self.primary[2:]
        primary.data[:] = 3
        polygon = None
        alternate = self.primary[:3]
        alternate.data[:] = 4

        target = np.ma.array(
            [
                [4, 4, 4, 4, 4],
                [4, 4, 4, 4, 4],
                [3, 3, 3, 3, 3],
                [3, 3, 3, 3, 3],
                [3, 3, 3, 3, 3],
            ],
            mask=False,
        )

        return primary, alternate, target, polygon

    def test_detached_sources(self):
        # Ensure that we correctly handle the case where the two sources
        # don't cover the same region of the grid.
        primary, alternate, target, polygon = self._detached_source()
        res = self._merge_on_poly(primary, alternate, polygon)
        self.assertMaskedArrayAlmostEqual(res.data, target)

    def test_detached_masked_sources(self):
        primary, alternate, target, polygon = self._detached_source()
        primary.data = np.ma.array(primary.data)
        primary.data[0, 0] = np.ma.masked
        alternate.data = np.ma.array(alternate.data)
        alternate.data[0, 0] = np.ma.masked

        res = self._merge_on_poly(primary, alternate, polygon)

        tmask = np.zeros((5, 5), dtype=bool)
        tmask[0, 0] = tmask[2, 0] = True
        target.mask = tmask
        self.assertMaskedArrayAlmostEqual(res.data, target)


class TestNoPolygon(ants.tests.TestCase):
    def test_separate_datasets(self):
        # Ensure that not providing the polygon results in stacking the
        # datasets together.
        source = ants.tests.stock.geodetic((5, 5))
        source.data = source.data.astype("float32")

        primary = source[:3]
        alternate = source[3:]
        merged_cube = merge(primary, alternate)
        self.assertMaskedArrayEqual(merged_cube.data, source.data)

    def test_nd_mapping_insensitive(self):
        # Ensure that the merge based on 'nan' values is insensitive to the
        # mapping of dimensions
        primary = ants.tests.stock.geodetic((2, 5, 5))
        primary.add_dim_coord(iris.coords.DimCoord([0, 1], long_name="bla"), 0)
        primary.data = primary.data.astype("float32")
        alternate = primary.copy()
        alternate.data += 100
        primary.transpose([1, 0, 2])
        primary.data[..., ::2] = np.nan

        target = primary.data.copy()
        target[..., ::2] = alternate.data[..., ::2].transpose([1, 0, 2])

        merged_cube = merge(primary, alternate)
        self.assertArrayEqual(merged_cube.data, target)

    def _overlapping_source(self):
        # Identified by means of np.nan values, points considered outside the
        # source extent are replaced by the alternate dataset points.
        # np.nan values are only possible with floating point numbers.
        # However, all regridding should return floating point numbers.
        source = ants.tests.stock.geodetic((5, 5))
        source.data = source.data.astype("float32")
        primary = source[:3]
        primary.data = np.ma.asarray(primary.data)
        alternate = source[2:]
        alternate.data = np.ma.asarray(alternate.data)
        return primary, alternate, source

    def test_overlapping_datasets_unmasked(self):
        primary, alternate, source = self._overlapping_source()
        primary.data[2] = np.nan

        merged_cube = merge(primary, alternate)
        self.assertMaskedArrayEqual(merged_cube.data, source.data)

    def test_overlapping_datasets_masked_primary(self):
        primary, alternate, source = self._overlapping_source()
        primary.data = np.ma.asarray(primary.data)
        primary.data[2] = np.nan
        primary.data[2] = np.ma.masked

        merged_cube = merge(primary, alternate)
        self.assertMaskedArrayEqual(merged_cube.data, source.data)

    def test_overlapping_datasets_no_mask_no_nan(self):
        # Ensure that two datasets are combined with the primary taking
        # precedence.
        primary, alternate, source = self._overlapping_source()
        merged_cube = merge(primary, alternate)
        self.assertMaskedArrayEqual(merged_cube.data, source.data)

    def test_overlapping_datasets_masked_alternate(self):
        # Ensure that the primary inherits the mask from the target in such a
        # case, but only over points where the primary has NaN values present.
        primary, alternate, source = self._overlapping_source()
        primary.data = np.ma.asarray(primary.data)
        primary.data[2] = np.nan
        alternate.data[:] = np.ma.masked

        merged_cube = merge(primary, alternate)
        source.data = np.ma.asarray(source.data)
        source.data[2:] = np.ma.masked
        self.assertMaskedArrayEqual(merged_cube.data, source.data)

    def test_missing_source_information(self):
        # Ensure that we fall over when there is missing source information to
        # populate the target grid area.
        source = ants.tests.stock.geodetic((5, 5))
        source.data = source.data.astype("float32")

        primary = source[:3]
        primary.data[2] = np.nan
        alternate = source[2:]
        alternate.data[2, 1] = np.nan

        msg = (
            "Coverage of provided sources is not complete, unable to " "merge datasets."
        )
        with self.assertRaisesRegex(RuntimeError, msg):
            merge(primary, alternate)


class TestMergeLSMs(ants.tests.TestCase):
    def test_merge_lsms(self):
        # Ensure that we can merge lsms (int8 type containing 0s and 1s)
        primary = ants.tests.stock.geodetic((5, 5))
        data = np.zeros([5, 5], np.int8)
        primary.data = data.copy()

        secondary = ants.tests.stock.geodetic((5, 5))
        data = np.ones([5, 5], np.int8)
        secondary.data = data.copy()

        polygon = [[45, 10], [120, 10], [120, 22], [45, 22]]
        target = secondary.data.copy()
        target = np.array(
            [
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
                [1, 1, 1, 0, 0],
                [1, 1, 1, 0, 0],
                [1, 1, 1, 1, 1],
            ]
        )

        merged_cube = merge(primary, secondary, polygon)
        self.assertMaskedArrayEqual(merged_cube.data, target)


if __name__ == "__main__":
    ants.tests.main()

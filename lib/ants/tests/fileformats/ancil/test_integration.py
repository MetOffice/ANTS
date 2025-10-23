# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import tempfile
import unittest.mock as mock

import ants
import ants.io.save as save
import ants.tests
import ants.tests.stock as stock
import cf_units
import iris
import numpy as np
from ants.fileformats.ancil import mule
from iris.coords import AuxCoord, DimCoord


class _BaseCommon(object):
    def _make_global_cube(self, shift, nlat=None, nlon=None, data=None):
        """
        Generate a new dynamics or engame grid, specified by the shift.

        The data should be provided or alternatively the nlat and nlon
        variables in order to specify the shape of the grid.
        The latitude and longitude coordinates are mapped to the inner most
        dimensions in that order.

        """
        if data is None:
            data = np.arange(nlat * nlon).reshape(nlat, nlon).astype(np.float64)
            data = np.ma.array(data, fill_value=-99.0)
        elif nlat is not None and nlon is not None:
            raise RuntimeError("Overspecified, both data and 'nlat/nlon' " "specified")
        else:
            (nlat, nlon) = data.shape[-2:]
        # Mask an element since we lose the fill_value when the array is not
        # masked.
        if np.ma.isMaskedArray(data):
            data[0, 0] = np.ma.masked
        cube = iris.cube.Cube(data)
        cube.attributes["grid_staggering"] = 6
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i000")
        crs = iris.coord_systems.GeogCS(6371229.0)
        x = shift * 3.75 + np.linspace(0, (nlon - 1) * 3.75, nlon)
        x = x.astype("float32")
        x_coord = iris.coords.DimCoord(
            x,
            standard_name="longitude",
            units="degrees",
            coord_system=crs,
            circular=True,
        )
        y = shift * 2.5 + np.linspace(-90, -90 + (nlat - 1) * 2.5, nlat)
        y = y.astype("float32")
        y_coord = iris.coords.DimCoord(
            y, standard_name="latitude", units="degrees", coord_system=crs
        )
        ydim, xdim = range(data.ndim)[-2:]
        cube.add_dim_coord(x_coord, xdim)
        cube.add_dim_coord(y_coord, ydim)
        return cube

    def get_ancil_fh(self, cubes):
        """Return filehandle for a temporary ancillary file created from cubes."""
        fh = tempfile.NamedTemporaryFile()
        save.ancil(cubes, fh.name)
        return fh

    def load_mule_ancil_from_disk(self, cubes):
        """Return a mule AncilFile object for testing ancillary saving.

        Uses ANTS file saving to save an F03 ancillary.  This is then loaded
        back as a mule.AncilFile.  The AncilFile is then returned and can be
        used for unittests.  Mule is used to load the file back since it does
        not interpret the data on disk.

        """
        fh = self.get_ancil_fh(cubes)
        return mule.AncilFile.from_file(fh.name)


@ants.tests.skip_mule
class TestAncillaryVersion(_BaseCommon, ants.tests.TestCase):
    def testall(self):
        with mock.patch(
            "ants.fileformats.ancil.template._ancil_version", return_value=3
        ):
            cube = self._make_global_cube(0.5, 2, 2)
            ffv = self.load_mule_ancil_from_disk(cube)
            self.assertEqual(ffv.fixed_length_header.model_version, 3)


@ants.tests.skip_mule
class TestMissingDataUMDefault(_BaseCommon, ants.tests.TestCase):
    def test_mdi_not_um_standard(self):
        expected = mule._REAL_MDI

        cube = self._make_global_cube(0.5, 2, 2)
        self.assertEqual(-99.0, cube.data.fill_value)
        ffv = self.load_mule_ancil_from_disk(cube)
        assert len(ffv.fields) == 1
        actual = ffv.fields[0].bmdi

        self.assertEqual(actual, expected)


@ants.tests.skip_mule
class TestVegPseudoLevels(_BaseCommon, ants.tests.TestCase):
    def _cube_with_pseudo_levels(self):
        nlat, nlon, npseudo = 2, 2, 3
        data = np.arange(nlat * nlon * npseudo).reshape(npseudo, nlat, nlon)
        data = np.ma.array(data, fill_value=-1.0, dtype=np.float64)
        data[:, 0, 0] = np.ma.masked
        cube = self._make_global_cube(0.5, data=data)
        pseudo_level_coord = iris.coords.AuxCoord(
            [101, 102, 2], long_name="pseudo_level"
        )
        cube.add_aux_coord(pseudo_level_coord, 0)
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i216")
        return cube

    def test_pseudo_level(self):
        # Check that the pseudo levels are those expected.
        cube = self._cube_with_pseudo_levels()
        ffv = self.load_mule_ancil_from_disk(cube)
        pseudo_levels = [field.lbuser5 for field in ffv.fields]
        self.assertEqual([101, 102, 2], pseudo_levels)

    def test_level_header(self):
        # Ensure the number of levels is as expected.
        cube = self._cube_with_pseudo_levels()
        ffv = self.load_mule_ancil_from_disk(cube)
        expected = np.ones(7, dtype="int") * -32768
        expected[0] = 1  # P_LEVELS
        # There's 15 integer constants in ancillary files. But only 5 of them
        # are actually used: 3, 6, 7, 8 and 15.  F03 and mule don't assign
        # names to the other 10, so the only way to access the values is via
        # array access on the .raw property.
        self.assertArrayEqual(ffv.integer_constants.raw[8:15], expected)


@ants.tests.skip_mule
class TestHeightModelLevels(_BaseCommon, ants.tests.TestCase):
    def setUp(self):
        # Ensure the number of levels is as expected.
        nlat, nlon, mod_lev = 2, 2, 3
        data = np.arange(nlat * nlon * mod_lev).reshape(mod_lev, nlat, nlon)
        self.cube = self._make_global_cube(0.5, data=data)
        mcoord = iris.coords.DimCoord(
            [0, 1, 2],
            attributes={"positive": "up"},
            standard_name="model_level_number",
        )
        self.cube.add_dim_coord(mcoord, 0)

    def test_level_header(self):
        ffv = self.load_mule_ancil_from_disk(self.cube)
        expected = np.ones(7, dtype="int") * -32768
        expected[0] = 3  # P_LEVELS
        # There's 15 integer constants in ancillary files. But only 5 of them
        # are actually used: 3, 6, 7, 8 and 15.  F03 and mule don't assign
        # names to the other 10, so the only way to access the values is via
        # array access on the .raw property.
        self.assertArrayEqual(ffv.integer_constants.raw[8:15], expected)

    def test_grid_staggering_2_rejected(self):
        # Compare with TestDepthModelLevels.test_grid_staggering_2_accepted
        self.cube.attributes["grid_staggering"] = 2
        with self.assertRaisesRegex(mule.validators.ValidateError, "Unsupported"):
            self.load_mule_ancil_from_disk(self.cube)


class TestDepthModelLevels(_BaseCommon, ants.tests.TestCase):
    def setUp(self):
        # Ensure the number of levels is as expected.
        nlat, nlon, mod_lev = 2, 2, 3
        data = np.arange(nlat * nlon * mod_lev).reshape(mod_lev, nlat, nlon)
        self.cube = self._make_global_cube(0.5, data=data)
        mcoord = iris.coords.DimCoord(
            [0, 1, 2],
            attributes={"positive": "down"},
            standard_name="model_level_number",
        )
        depth = iris.coords.AuxCoord(
            [0.5, 1.5, 2.5],
            attributes={"positive": "down"},
            long_name="depth",
            units=cf_units.Unit("m"),
        )
        self.cube.add_dim_coord(mcoord, 0)
        self.cube.add_aux_coord(depth, data_dims=0)

    @ants.tests.skip_mule
    def test_level_header(self):
        ffv = self.load_mule_ancil_from_disk(self.cube)
        expected = np.ones(7, dtype="int") * -32768
        expected[0] = 3  # P_LEVELS
        # There's 15 integer constants in ancillary files. But only 5 of them
        # are actually used: 3, 6, 7, 8 and 15.  F03 and mule don't assign
        # names to the other 10, so the only way to access the values is via
        # array access on the .raw property.
        self.assertArrayEqual(ffv.integer_constants.raw[8:15], expected)

    @ants.tests.skip_mule
    def test_grid_staggering_2_accepted(self):
        # Compare with TestHeightModelLevels.test_grid_staggering_2_rejected
        self.cube.attributes["grid_staggering"] = 2
        ffv = self.load_mule_ancil_from_disk(self.cube)
        self.assertEqual(ffv.fixed_length_header.grid_staggering, 2)

    @ants.tests.skip_mule
    def test_depth_vertical_coordinate(self):
        ffv = self.load_mule_ancil_from_disk(self.cube)
        self.assertEqual(ffv.fixed_length_header.vert_coord_type, 4)

    def test_unsupported_depth_rejected(self):
        self.cube.coord("depth").attributes = {}
        with self.assertRaisesRegex(ValueError, "Unsupported depth"):
            self.load_mule_ancil_from_disk(self.cube)

    @ants.tests.skip_mule
    def test_invalid_depth_name_skipped(self):
        # Rename the depth coordinate to an invalid name and
        # check that the header is not modified
        self.cube.coord("depth").rename("invalid_depth_name")
        ffv = self.load_mule_ancil_from_disk(self.cube)
        self.assertEqual(ffv.fixed_length_header.vert_coord_type, 1)


@ants.tests.skip_mule
class TestSingleAndMultiLevel(_BaseCommon, ants.tests.TestCase):
    _NLEV = 3

    def _make_cubes(self):
        nlat, nlon, nlev = 2, 2, self._NLEV
        data1 = np.zeros((nlev, nlat, nlon))
        cube1 = self._make_global_cube(0.5, data=data1)
        depth = iris.coords.DimCoord(
            np.arange(nlev), attributes={"positive": "down"}, units=cf_units.Unit("m")
        )
        cube1.add_dim_coord(depth, 0)

        data2 = np.zeros((nlat, nlon))
        cube2 = self._make_global_cube(0.5, data=data2)

        return cube1, cube2

    def test_multi_and_surface(self):
        multi, single = self._make_cubes()
        cubes = iris.cube.CubeList([multi, single])

        ffv = self.load_mule_ancil_from_disk(cubes)

        self.assertEqual(self._NLEV, ffv.integer_constants.num_levels)

    def test_surface_and_multi(self):
        multi, single = self._make_cubes()
        cubes = iris.cube.CubeList([single, multi])

        ffv = self.load_mule_ancil_from_disk(cubes)

        self.assertEqual(self._NLEV, ffv.integer_constants.num_levels)

    def test_mixed_multi_and_single(self):
        multi, single = self._make_cubes()
        cubes = iris.cube.CubeList([single, multi, single.copy(), multi.copy()])

        ffv = self.load_mule_ancil_from_disk(cubes)

        self.assertEqual(self._NLEV, ffv.integer_constants.num_levels)
        self.assertEqual(len(cubes), ffv.integer_constants.num_field_types)


@ants.tests.skip_mule
class TestTimeCoordinates(_BaseCommon, ants.tests.TestCase):
    def assert_time(self, ffv, t1, t2, t3):
        # ffv.fixed_length_header.tX_year through to
        # ffv.fixed_length_header.tX_second for t1, t2 and t3.  Note that
        # tX_year_day_number is not tested.
        self.assertArrayEqual(ffv.fixed_length_header.raw[21:27], t1)
        self.assertArrayEqual(ffv.fixed_length_header.raw[28:34], t2)
        self.assertArrayEqual(ffv.fixed_length_header.raw[35:41], t3)

    def test_that_time_header_does_not_have_to_be_set(self):
        cube = self._make_global_cube(0.5, 72, 96)
        assert self.get_ancil_fh(cube)

    def test_categorised_month_present(self):
        # Ensure that we raise an exception in the presence of categorised time
        # coordinates and no time information.
        # Context: The pplookup should not have zero years to signify
        # periodicity, only the Fixed Length Header.
        # Iris deals with zero year pplookup by
        # creating a 'month_number' coordinate.
        msg = (
            'Categorisation time coordinates found "month_number".  '
            "Underspecified time information, please consider adding a "
            '"time" coordinate if applicable.'
        )
        cube = self._make_global_cube(0.5, 72, 96)
        month_coord = iris.coords.AuxCoord(1, long_name="month_number")
        cube.add_aux_coord(month_coord, None)
        with self.assertRaisesRegex(ValueError, msg):
            self.get_ancil_fh(cube)

    def test_categorised_month_present_with_time(self):
        # Ensure that having a month number coordinate is ignored when there is
        # also time present.
        data = np.arange(2 * 72 * 96).reshape(2, 72, 96)
        cube = self._make_global_cube(0.5, data=data)
        month_coord = iris.coords.AuxCoord([1, 2], long_name="month_number")
        cube.add_aux_coord(month_coord, 0)
        times = [-17011800.0, -17003880.0]
        tunit = cf_units.Unit("hours since 1970-01-01 00:00:00", calendar="360_day")
        time_coord = iris.coords.AuxCoord(times, standard_name="time", units=tunit)
        time_coord.guess_bounds()
        cube.add_aux_coord(time_coord, 0)
        ffv = self.load_mule_ancil_from_disk(cube)

        start = [1, 1, 16, 0, 0, 0]
        end = [1, 12, 16, 0, 0, 0]
        interval = [0, 11, 0, 0, 0, 0]
        self.assert_time(ffv, start, end, interval)

    def test_single_time_data_times(self):
        # Capturing that we currently silently ignore time data for single
        # value time coordinates.
        cube = self._make_global_cube(0.5, 72, 96)
        times = -17011800.0
        bounds = [times - 1, times + 1]
        tunit = cf_units.Unit("hours since 1970-01-01 00:00:00", calendar="360_day")
        time_coord = iris.coords.AuxCoord(
            times, bounds=bounds, standard_name="time", units=tunit
        )

        cube.add_aux_coord(time_coord, None)
        ffv = self.load_mule_ancil_from_disk(cube)

        start = end = interval = [-32768] * 6
        self.assert_time(ffv, start, end, interval)

    def test_single_time_type(self):
        # Capturing that we resolve ambiguity of whether periodic single times
        # are periodic or single time in favour of single time.
        cube = ants.tests.stock.geodetic((1, 2, 2))
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i000")
        times = 180.0
        bounds = [0, 360]
        tunit = cf_units.Unit("days since epoch", calendar="360_day")
        time_coord = iris.coords.DimCoord(
            times, bounds=bounds, standard_name="time", units=tunit
        )

        cube.add_dim_coord(time_coord, 0)
        ffv = self.load_mule_ancil_from_disk(cube)

        expected = 0
        self.assertEqual(ffv.fixed_length_header.time_type, expected)


@ants.tests.skip_mule
class TestRotatedPoleGrid(_BaseCommon, ants.tests.TestCase):
    @property
    def get_crs(self):
        geogcs = iris.coord_systems.GeogCS(6371229.0)
        return iris.coord_systems.RotatedGeogCS(37.5, 177.5, ellipsoid=geogcs)

    def _get_points(self, locations, var_points, npoints):
        # Grid consists of a regular outer area, variable resolution area then
        # a regular inner area.
        out_start = locations[0]
        out_step = 0.036
        out_end = locations[1] + out_step
        out = np.arange(out_start, out_end, out_step)

        in_start = locations[2]
        in_step = 0.0135
        npts = npoints / 2.0 - out.size - var_points.size
        in_end = np.round(in_start + ((npts - 1) * in_step), 8)
        pin = np.arange(in_start, in_end, in_step)

        # Combine the outer, variable res and inner area
        pnts = np.hstack([out, var_points, pin])

        # Derive the second half by the np.diff of the first
        end = locations[3]
        pnts2 = np.cumsum(np.hstack([end, np.diff(pnts) * -1]))[::-1]

        return np.hstack([np.round(pnts, 8), np.round(pnts2, 8)])

    def _get_x_coord(self):
        # Grid consists of a regular outer area, variable resolution area then
        # a regular inner area.
        npoints = 744
        x_var = np.array(
            [
                354.52184184,
                354.55011878,
                354.57736948,
                354.60363117,
                354.62893974,
                354.6533298,
                354.67683466,
                354.69948647,
                354.72131618,
                354.74235363,
                354.76262757,
                354.7821657,
                354.80099474,
                354.81914042,
                354.83662755,
                354.85348001,
                354.86972085,
                354.88537226,
                354.90045564,
                354.91499159,
            ]
        )
        locations = [353.0525, 354.4925, 354.9290, 365.189]

        points = self._get_points(locations, x_var, npoints)
        coord = iris.coords.DimCoord(
            points,
            standard_name="grid_longitude",
            units="degrees",
            coord_system=self.get_crs,
        )
        return coord

    def _get_y_coord(self):
        # Grid consists of a regular outer area, variable resolution area then
        # a regular inner area.
        npoints = 928
        y_var = np.array(
            [
                -4.19377982,
                -4.16359848,
                -4.13460713,
                -4.10675887,
                -4.08000862,
                -4.05431309,
                -4.02963069,
                -4.00592148,
                -3.98314708,
                -3.96127064,
                -3.94025675,
                -3.9200714,
                -3.90068193,
                -3.88205696,
                -3.86416634,
                -3.84698111,
                -3.83047347,
                -3.8146167,
                -3.79938514,
                -3.78475413,
            ]
        )
        locations = [-5.5932, -4.2252, -3.7707, 8.9733]

        points = self._get_points(locations, y_var, npoints)
        coord = iris.coords.DimCoord(
            points,
            standard_name="grid_latitude",
            units="degrees",
            coord_system=self.get_crs,
        )
        return coord

    def _get_ukv_grid(self):
        y = self._get_y_coord()
        x = self._get_x_coord()
        data = (
            np.arange(y.points.size * x.points.size)
            .reshape(y.points.size, x.points.size)
            .astype(np.float64)
        )
        data = np.ma.array(data, fill_value=-1073741824.0)
        data[0, 0] = np.ma.masked
        cube = iris.cube.Cube(data)
        cube.add_dim_coord(y, 0)
        cube.add_dim_coord(x, 1)
        cube.attributes["grid_staggering"] = 3
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i000")
        return cube

    def test_ukv_real_constants_header(self):
        """Array check for first 4 real constants.

        Note mule uses 1 index arrays for consistency with F03.

        These would have data for regular grids but are RMDI for variable
        resolution grids (see F03).

        """
        expected = [mule._REAL_MDI] * 4

        cube = self._get_ukv_grid()
        ffv = self.load_mule_ancil_from_disk(cube)
        actual = ffv.real_constants.raw[1:5]

        self.assertArrayEqual(actual, expected)

    def test_ukv_lookup_headers(self):
        """Array check for BZY, BDY, BZX and BDX in that order.

        Note mule uses 1 index arrays for consistency with F03.

        These would have data for regular grids but are RMDI for variable
        resolution grids (see F03).

        """
        expected = [mule._REAL_MDI] * 4

        cube = self._get_ukv_grid()
        ffv = self.load_mule_ancil_from_disk(cube)
        # Confirm we only have 1 field.
        assert len(ffv.fields) == 1
        actual = ffv.fields[0].raw[59:63]

        self.assertArrayEqual(actual, expected)

    def test_ukv_row_dependent_constants(self):
        """Array check for row dependent constants.

        These would have RMDI for regular grids but have data for variable
        resolution grids (see F03).

        """
        expected = self._get_y_coord().points

        cube = self._get_ukv_grid()
        ffv = self.load_mule_ancil_from_disk(cube)
        # Note that the first dimension is 0-indexed but the second is
        # 1-indexed (as per mule docs for BaseHeaderComponent2D).
        actual = ffv.row_dependent_constants.raw[:, 1]

        self.assertArrayEqual(actual, expected)

    def test_ukv_column_dependent_constants(self):
        """Array check for column dependent constants.

        These would have RMDI for regular grids but have data for variable
        resolution grids (see F03).

        """
        expected = self._get_x_coord().points

        cube = self._get_ukv_grid()
        ffv = self.load_mule_ancil_from_disk(cube)
        # Note that the first dimension is 0-indexed but the second is
        # 1-indexed (as per mule docs for BaseHeaderComponent2D).
        actual = ffv.column_dependent_constants.raw[:, 1]

        self.assertArrayEqual(actual, expected)


@ants.tests.skip_mule
class TestPseudoLevelOrder(_BaseCommon, ants.tests.TestCase):
    # Ensure preservation of pseudo-levels

    def setUp(self):
        self.expected = [1, 2, 100, 103, 102]
        nlat, nlon, npseudo = 2, 2, len(self.expected)
        data = np.arange(nlat * nlon * npseudo).reshape(npseudo, nlat, nlon)
        self.cube = self._make_global_cube(0.5, data=data)

        self.cube.add_aux_coord(AuxCoord(self.expected, long_name="pseudo_level"), 0)

    def test_final_pseudo_level_is_aux_coord(self):
        fh = tempfile.NamedTemporaryFile()
        save.ancil(self.cube, fh.name)
        result = ants.io.load.load_cube(fh.name)
        self.assertTrue("pseudo_level" in [coord.name() for coord in result.aux_coords])

    def test_pseudo_level_order_is_preserved(self):
        ffv = self.load_mule_ancil_from_disk(self.cube)
        pseudo_levels = [field.lbuser5 for field in ffv.fields]
        self.assertArrayEqual(pseudo_levels, self.expected)

    def test_pseudo_level_order_is_preserved_with_time_coord(self):
        cube = iris.cube.CubeList([self.cube.copy(), self.cube.copy()])
        tunits = cf_units.Unit("days since 1970-01-01 00:00:00", calendar="gregorian")
        tcoord = DimCoord(
            [16, 45],
            bounds=[[0.0, 31.0], [31.0, 59.0]],
            units=tunits,
            standard_name="time",
        )
        cube[0].add_aux_coord(tcoord[0], None)
        cube[1].add_aux_coord(tcoord[1], None)
        cube = cube.merge_cube()

        ffv = self.load_mule_ancil_from_disk(cube)
        pseudo_levels = [field.lbuser5 for field in ffv.fields]
        expected = np.hstack([self.expected, self.expected])
        self.assertArrayEqual(pseudo_levels, expected)


@ants.tests.skip_mule
class TestMultipleFields(_BaseCommon, ants.tests.TestCase):
    def _build_cube(self):
        time_unit = cf_units.Unit(
            "days since 0001-01-01 00:00:00", calendar="gregorian"
        )
        tc = DimCoord(
            [1, 3],
            bounds=np.array([[0.0, 2.0], [2.0, 4.0]]),
            standard_name="time",
            units=time_unit,
        )
        mc = iris.coords.DimCoord(np.arange(4), standard_name="model_level_number")
        cube = stock.geodetic((2, 4, 2, 2))
        cube.add_dim_coord(tc, 0)
        cube.add_dim_coord(mc, 1)
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m00s00i000")
        return cube

    def test_number_of_fields(self):
        cube = self._build_cube()
        cubes = iris.cube.CubeList([cube, cube.copy(), cube.copy()])
        ffv = self.load_mule_ancil_from_disk(cubes)
        self.assertEqual(
            ffv.fixed_length_header.lookup_dim2, np.prod(cube.shape[:2]) * 3
        )


class TestExceptions(_BaseCommon, ants.tests.TestCase):
    def setUp(self):
        self.cube = self._make_global_cube(0.5, 2, 2)

    @ants.tests.skip_mule
    def test_not_identical_coordinates_present(self):
        # Where coordinates are not ~identically defined to all cubes being
        # saved.
        cube = self.cube.copy()

        coord = iris.coords.AuxCoord([1, 2], long_name="altitude")
        self.cube.add_aux_coord(coord, 0)

        coord = iris.coords.AuxCoord([1, 3], long_name="altitude")
        cube.add_aux_coord(coord, 0)

        msg = "Currently, only support writing cubes with identical coordinate"
        with self.assertRaisesRegex(RuntimeError, msg):
            self.load_mule_ancil_from_disk(iris.cube.CubeList([self.cube, cube]))

    @ants.tests.skip_mule
    def test_missing_coordinates(self):
        # Where coordinates are not common to all cubes being saved.
        cube = self.cube.copy()

        coord = iris.coords.AuxCoord([1, 2], long_name="some_coord")
        self.cube.add_aux_coord(coord, 0)
        msg = "Currently, only support writing cubes with identical coordinate"
        with self.assertRaisesRegex(RuntimeError, msg):
            self.load_mule_ancil_from_disk(iris.cube.CubeList([self.cube, cube]))

    def test_invalid_coordinates(self):
        coord = iris.coords.AuxCoord([1, 2], long_name="level_pressure")
        self.cube.add_aux_coord(coord, 0)

        coord = iris.coords.AuxCoord([1, 3], long_name="bar")
        self.cube.add_aux_coord(coord, 0)

        msg = r"Coordinates \['level_pressure'\] are presently unsupported."
        with self.assertRaisesRegex(RuntimeError, msg):
            self.load_mule_ancil_from_disk(self.cube)

    def test_no_stash_code(self):
        self.cube.attributes.pop("STASH")

        msg = "Cube .+ does not have a stash code"
        with self.assertRaisesRegex(ValueError, msg):
            self.load_mule_ancil_from_disk(self.cube)

    def test_pressure_coordinate(self):
        coord = iris.coords.AuxCoord([1, 3], long_name="level_pressure")
        self.cube.add_aux_coord(coord, 0)
        msg = r"Coordinates \['level_pressure'\] are presently unsupported."
        with self.assertRaisesRegex(RuntimeError, msg):
            self.load_mule_ancil_from_disk(self.cube)


class TestFieldDtype(_BaseCommon, ants.tests.TestCase):
    UM_TYPE = {"logical": 3, "integer": 2, "float": 1}
    # FFV kind is 8 no matter what we do.
    ITEM_SIZE = {"logical": 8, "integer": 8, "float": 8}
    KIND = {"logical": "i", "integer": "i", "float": "f"}

    def setUp(self):
        data = np.array([[0, 1], [1, 0]])
        self.cube = self._make_global_cube(0.5, data=data)

    def assertFieldType(
        self, src_dtype, target_type, valid_min=None, valid_max=None, valid_range=None
    ):
        # Return whether resulting ancilary has logical type or not.
        self.cube.data = self.cube.data.astype(src_dtype, copy=False)
        for valid_name, valid_x in [
            ["valid_min", valid_min],
            ["valid_max", valid_max],
            ["valid_range", valid_range],
        ]:
            if valid_x is not None:
                self.cube.attributes[valid_name] = valid_x

        ffv = self.load_mule_ancil_from_disk(self.cube)

        rdtype = (ffv.fields[0].get_data()).dtype
        res_itemsize, res_kind = rdtype.itemsize, rdtype.kind
        res_type = ffv.fields[0].lbuser1

        self.assertTrue(
            res_type == self.UM_TYPE[target_type]
            and res_itemsize == self.ITEM_SIZE[target_type]
            and res_kind == self.KIND[target_type]
        )

    @ants.tests.skip_mule
    def test_logical_valid_min_max_int8(self):
        self.assertFieldType("int8", "logical", valid_min=0, valid_max=1)

    @ants.tests.skip_mule
    def test_integer_valid_max_int8(self):
        self.assertFieldType("int8", "integer", valid_max=1)

    @ants.tests.skip_mule
    def test_logical_valid_range_int8(self):
        self.assertFieldType("int8", "logical", valid_range=[0, 1])

    @ants.tests.skip_mule
    def test_logical_valid_range_valid_x_int8_agrees(self):
        # Ensure that valid_range, valid_min and valid_max being specified
        # is accepted when they agree.
        self.assertFieldType(
            "int8", "logical", valid_range=[0, 1], valid_min=0, valid_max=1
        )

    def test_logical_valid_range_valid_x_int8_disagrees(self):
        # Ensure that valid_range, valid_min and valid_max being specified
        # is not accepted if one of them suggests a logical field while the
        # other does not.
        msg = (
            "Cube attribute valid range is overspecified .* "
            r"valid_range:\[0, 1\], valid_min, valid_max: \[10, 100\]"
        )
        with self.assertRaisesRegex(ValueError, msg):
            self.assertFieldType(
                "int8", "logical", valid_range=[0, 1], valid_min=10, valid_max=100
            )

    @ants.tests.skip_mule
    def test_non_logical_valid_range_valid_x_ignore(self):
        # Ensure that the valid_range, valid_min and valid_max are ignored
        # even if they don't agree with oneanother when we don't interpret
        # them i.e. they do not suggest a logical field.
        self.assertFieldType(
            "int8", "integer", valid_range=[1, 2], valid_min=10, valid_max=100
        )

    @ants.tests.skip_mule
    def test_non_logical_valid_range_int8(self):
        # When valid_x indicates that field doesn't represent a logical, ensure
        # that it doesn't end up as a logical.
        self.assertFieldType("int8", "integer", valid_range=[1, 10])

    @ants.tests.skip_mule
    def test_no_valid_range_int8(self):
        # If this fails in future, it will be because valid_range has been
        # derived i.e. valid_range will no longer need to be specified
        # manually for logical fields.
        self.assertFieldType("int8", "integer")

    @ants.tests.skip_mule
    def test_logical_valid_x_int64(self):
        # Ensure that don't ignore valid_x when the source field is not with
        # itemsize 1 i.e. it only has to be of integer type.
        self.assertFieldType("int64", "logical", valid_min=0, valid_max=1)

    @ants.tests.skip_mule
    def test_float64(self):
        self.assertFieldType("float32", "float")


@ants.tests.skip_mule
class TestVariableResGrid(_BaseCommon, ants.tests.TestCase):
    def assert_load_save_cycle(self, grid_staggerring):
        cube = stock.geodetic((3, 3))
        sx = cube.coord(axis="x")
        sy = cube.coord(axis="y")
        points = sx.points.copy()
        points[0] = points[0] - 1
        sx.points = points
        points = sy.points.copy()
        points[0] = points[0] - 1
        sy.points = points
        cube.attributes["grid_staggering"] = grid_staggerring
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i000")
        self.load_mule_ancil_from_disk(cube)

        fh = tempfile.NamedTemporaryFile()
        save.ancil(cube, fh.name)

        # Cube comparison
        ncube = ants.io.load.load_cube(fh.name)
        self.assertArrayEqual(ncube.coord(axis="x").points, sx.points)
        self.assertArrayEqual(ncube.coord(axis="y").points, sy.points)

    def test_newdynamics(self):
        self.assert_load_save_cycle(3)

    def test_endgame(self):
        self.assert_load_save_cycle(6)


@ants.tests.skip_mule
class TestMuleWorkaround(_BaseCommon, ants.tests.TestCase):
    def test_lbuser2_set(self):
        cube1 = stock.geodetic((3, 3))
        cube1.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i000")
        cube2 = cube1.copy()
        cube2.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m01s00i001")
        with mock.patch("ants.io.save._mule_set_lbuser2"):
            ffv = self.load_mule_ancil_from_disk([cube1, cube2])
        lbuser_set = [field.lbuser2 != -99 for field in ffv.fields]
        if any(lbuser_set):
            raise RuntimeError(
                "Mule is populating lbuser2 for us.  Remove " "our workaround."
            )


if __name__ == "__main__":
    ants.tests.main()

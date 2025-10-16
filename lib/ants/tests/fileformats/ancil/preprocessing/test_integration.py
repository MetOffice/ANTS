# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import datetime
import tempfile
import unittest.mock as mock
import warnings

import ants
import ants.tests
import cf_units
import iris
from ants.fileformats.ancil import mule
import numpy as np
from ants.fileformats.ancil.preprocessing import (
    _create_climatology_config,
    correct_lbproc,
    set_climatology_year,
)


def gen_single_field_ffv():
    time_type_single = 0
    fixed_length_header = {
        "time_type": time_type_single,
        "grid_staggering": 6,  # EndGame
        "horiz_grid_type": 0,  # Global file
        "dataset_type": 4,  # Ancillary file
        "data_set_format_version": 20,  # Always fixed
        "sub_model": 1,  # Atmosphere
        "vert_coord_type": 1,  # Hybrid heights
        "model_version": 1000,  # Version of ancillary program
    }

    n_cols, n_rows = 1, 1
    template = {
        "fixed_length_header": fixed_length_header,
        "integer_constants": {"num_cols": n_cols, "num_rows": n_rows, "num_levels": 0},
        "real_constants": {
            "col_spacing": 360.0 / n_cols,
            "row_spacing": 180.0 / n_rows,
            "start_lat": -90.0,
            "start_lon": 0.0,
            "north_pole_lat": 90.0,
            "north_pole_lon": 0.0,
        },
    }
    ancil = mule.AncilFile.from_template(template)

    data = mule.ArrayDataProvider(np.zeros((1, 1)))

    field = mule.Field3.empty()
    field.set_data_provider(data)
    field.lbuser4 = 1000  # STASH
    field.lbcode = 1
    field.lbuser7 = 1  # Atmosphere
    field.lbrel = 3
    field.lbpack = 0
    field.lbuser1 = 1  # Datatype
    field.lbnpt = n_cols
    field.lbrow = n_rows
    field.bdx = ancil.real_constants.col_spacing
    field.bdy = ancil.real_constants.row_spacing
    field.bzx = ancil.real_constants.start_lon - 0.5 * field.bdx
    field.bzy = ancil.real_constants.start_lat - 0.5 * field.bdy

    ancil.fields = [field]
    return ancil


def gen_climatological_ffv():
    ancil = gen_single_field_ffv()
    ancil.integer_constants.num_times = 12
    fields = [ancil.fields[0].copy() for i in range(12)]
    for ind, field in enumerate(fields):
        field.lbproc = 0
        field.lbmin, field.lbmind = 3, 5
        field.lbhr, field.lbhrd = 3, 5
        field.lbdat, field.lbdatd = 3, 5
        field.lbtim = 2
        field.lbmon, field.lbmond = ind + 1, ind + 2
        field.lbyr, field.lbyrd = 1950, 1950
        if ind == 11:
            field.lbyrd = 1951
            field.lbmond = 1

    ancil.fields = fields
    return ancil


class Common(object):
    def gen_cube(self, ancil):
        def dummy_validate(*args, **kwargs):
            pass

        ancil.validate = dummy_validate
        fh = tempfile.NamedTemporaryFile()
        ancil.to_file(fh.name)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            cube = ants.io.load.load_cube(fh.name)
        return cube


@ants.tests.skip_mule
class Test_set_climatology_year(Common, ants.tests.TestCase):
    def assert_climatology(self, ancil, tar):
        set_climatology_year(ancil, 2012)
        with mock.patch("warnings.warn"):
            cube = self.gen_cube(ancil)
        self.assertTrue(ants.utils.coord.relaxed_equality(cube.coord("time"), tar))
        self.assertTrue(ancil.fixed_length_header.time_type, 2)

    def test_360_day(self):
        units = cf_units.Unit("hours since 1970-01-01 00:00:00", calendar="360_day")
        points = [
            363240,
            363960,
            364680,
            365400,
            366120,
            366840,
            367560,
            368280,
            369000,
            369720,
            370440,
            371160,
        ]
        bounds = [
            [362880, 363600],
            [363600, 364320],
            [364320, 365040],
            [365040, 365760],
            [365760, 366480],
            [366480, 367200],
            [367200, 367920],
            [367920, 368640],
            [368640, 369360],
            [369360, 370080],
            [370080, 370800],
            [370800, 371520],
        ]
        tar = iris.coords.DimCoord(points, "time", bounds=bounds, units=units)

        ancil = gen_climatological_ffv()
        self.assert_climatology(ancil, tar)

    def test_gregorian(self):
        units = cf_units.Unit("hours since 1970-01-01 00:00:00", calendar="gregorian")
        points = [
            368532,
            369252,
            369972,
            370704,
            371436,
            372168,
            372900,
            373644,
            374376,
            375108,
            375840,
            376572,
        ]
        bounds = [
            [368160, 368904],
            [368904, 369600],
            [369600, 370344],
            [370344, 371064],
            [371064, 371808],
            [371808, 372528],
            [372528, 373272],
            [373272, 374016],
            [374016, 374736],
            [374736, 375480],
            [375480, 376200],
            [376200, 376944],
        ]
        tar = iris.coords.DimCoord(points, "time", bounds=bounds, units=units)

        ancil = gen_climatological_ffv()
        for field in ancil.fields:
            field.lbdatd = 31
        self.assert_climatology(ancil, tar)


@ants.tests.skip_mule
class Test_correct_lbproc(Common, ants.tests.TestCase):
    def testall(self):
        ancil = gen_single_field_ffv()
        correct_lbproc(ancil)
        self.assertEqual(ancil.fields[0].lbproc, 0)


@ants.tests.skip_mule
class Test__create_climatology_config(Common, ants.tests.TestCase):
    def test_exception_for_not_monthly_mean(self):
        ancil = gen_climatological_ffv()
        with self.assertRaisesRegex(ValueError, "Ancil file does not appear"):
            _create_climatology_config(ancil)

    def test_start_date_in_config(self):
        ancil = gen_climatological_ffv()
        ancil.fixed_length_header.t3_month = 1
        start_date = datetime.datetime(
            ancil.fields[0].lbyr, ancil.fields[0].lbmon, ancil.fields[0].lbdat
        )
        expected = start_date.strftime("%Y-%m-%d")
        config = _create_climatology_config(ancil)
        self.assertEqual(config["climatology"]["start"], expected)

    def test_end_date_in_config(self):
        ancil = gen_climatological_ffv()
        ancil.fixed_length_header.t3_month = 1
        end_date = datetime.datetime(
            ancil.fields[-1].lbyrd, ancil.fields[-1].lbmond, ancil.fields[-1].lbdatd
        )
        expected = end_date.strftime("%Y-%m-%d")
        config = _create_climatology_config(ancil)
        self.assertEqual(config["climatology"]["end"], expected)


if __name__ == "__main__":
    ants.tests.main()

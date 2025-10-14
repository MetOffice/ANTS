# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import tempfile

import ants.io.save as save
import ants.tests
import cf_units
import iris
import mule
import numpy as np
from ants.fileformats.ancil.preprocessing import update_reference_year
from iris.coords import DimCoord


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.source = tempfile.NamedTemporaryFile()
        self.destination = tempfile.NamedTemporaryFile()
        cube = iris.cube.Cube(np.zeros((12, 2, 2)))
        cube.add_dim_coord(DimCoord([0, 1], standard_name="latitude"), 1)
        cube.add_dim_coord(DimCoord([0, 1], standard_name="longitude"), 2)
        cube.attributes["STASH"] = iris.fileformats.pp.STASH.from_msi("m00s00i000")
        points = np.array(
            [
                15.5,
                45.0,
                74.5,
                105.0,
                135.5,
                166.0,
                196.5,
                227.5,
                258.0,
                288.5,
                319.0,
                349.5,
            ]
        )
        units = cf_units.Unit("days since 0001-01-01 00:00:00", calendar="gregorian")
        tc = DimCoord(
            points,
            bounds=np.array(
                [
                    [0.0, 31.0],
                    [31.0, 59.0],
                    [59.0, 90.0],
                    [90.0, 120.0],
                    [120.0, 151.0],
                    [151.0, 181.0],
                    [181.0, 212.0],
                    [212.0, 243.0],
                    [243.0, 273.0],
                    [273.0, 304.0],
                    [304.0, 334.0],
                    [334.0, 365.0],
                ]
            ),
            standard_name="time",
            units=units,
        )
        cube.add_dim_coord(tc, 0)
        # Needed to get correct lbproc/lbtim, which ensures field saving works
        # properly.
        cube.cell_methods = (iris.coords.CellMethod(method="mean", coords="time"),)

        frt_coord = iris.coords.AuxCoord(
            points, standard_name="forecast_reference_time", units=units
        )
        cube.add_aux_coord(frt_coord, 0)

        save.ancil(cube, self.source.name)
        self.ffv = mule.AncilFile.from_file(self.source.name)

    def test_flh_default_year(self):
        update_reference_year(self.ffv)
        self.assertEqual(4, self.ffv.fixed_length_header.t1_year)
        self.assertEqual(4, self.ffv.fixed_length_header.t2_year)

    def test_flh_specified_year(self):
        update_reference_year(self.ffv, 1978)
        self.assertEqual(1978, self.ffv.fixed_length_header.t1_year)
        self.assertEqual(1978, self.ffv.fixed_length_header.t2_year)

    def test_lookup_default_year(self):
        update_reference_year(self.ffv)
        for field in self.ffv.fields[:-1]:
            self.assertEqual(4, field.lbyr)
            self.assertEqual(4, field.lbyrd)
        # Special case for last field: end year should increment
        self.assertEqual(4, self.ffv.fields[-1].lbyr)
        self.assertEqual(5, self.ffv.fields[-1].lbyrd)

    def test_lookup_specified_year(self):
        update_reference_year(self.ffv, 1978)
        for field in self.ffv.fields[:-1]:
            self.assertEqual(1978, field.lbyr)
            self.assertEqual(1978, field.lbyrd)
        # Special case for last field: end year should increment
        self.assertEqual(1978, self.ffv.fields[-1].lbyr)
        self.assertEqual(1979, self.ffv.fields[-1].lbyrd)

    def test_exception_for_invalid_year(self):
        msg = "The provided year must be a positive integer."
        with self.assertRaisesRegex(ValueError, msg):
            update_reference_year(self.ffv, 0)

    def test_exception_for_not_integer_year(self):
        msg = "The provided year must be a positive integer."
        with self.assertRaisesRegex(ValueError, msg):
            update_reference_year(self.ffv, -500)


if __name__ == "__main__":
    ants.tests.main()

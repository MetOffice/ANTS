# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import tempfile

import ants.io.save as save
import ants.tests
import cf_units
import iris
import numpy as np
from ants.fileformats.ancil import mule
from ants.fileformats.ancil.preprocessing import make_time_bounds_contiguous
from iris.coords import DimCoord


@ants.tests.skip_mule
class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.source = tempfile.NamedTemporaryFile()
        self.destination = tempfile.NamedTemporaryFile()
        cube = iris.cube.Cube(np.zeros((12, 2, 2, 3)))
        cube.add_dim_coord(DimCoord([0, 1], standard_name="latitude"), 1)
        cube.add_dim_coord(DimCoord([0, 1], standard_name="longitude"), 2)
        cube.add_dim_coord(DimCoord([0, 1, 2], standard_name="model_level_number"), 3)
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
        # properly:
        cube.cell_methods = (iris.coords.CellMethod(method="mean", coords="time"),)

        # Set forecast reference time to points to avoid error when loading
        # with AncilFV:
        frt_coord = iris.coords.AuxCoord(
            points, standard_name="forecast_reference_time", units=units
        )
        cube.add_aux_coord(frt_coord, 0)
        save.ancil(cube, self.source.name)

        # Make fields non-contiguous by adding one minute to each lower bound.
        ffv = mule.AncilFile.from_file(self.source.name)
        for field in ffv.fields:
            field.lbmin += 1
        ffv.to_file(self.source.name)

        self.ffv = mule.AncilFile.from_file(self.source.name)

    def test_contiguous_time_bounds(self):
        make_time_bounds_contiguous(self.ffv)
        # Comparing each field to the one 3 after it to account for 3 levels
        # per time
        for start, end in zip(self.ffv.fields[3:], self.ffv.fields[0:-3]):
            self.assertContiguousFields(start, end)

    def test_same_bounds_for_all_levels_start_time(self):
        make_time_bounds_contiguous(self.ffv)
        expected = np.array([1, 1, 1, 0, 1, 0, 1, 2, 1, 0, 1, 0])
        for field in self.ffv.fields[:3]:
            self.assertArrayEqual(expected, field.raw[1:13])

    def test_same_bounds_for_all_levels_end_time(self):
        make_time_bounds_contiguous(self.ffv)
        expected = np.array([1, 12, 1, 0, 1, 0, 2, 1, 1, 0, 1, 0])
        for field in self.ffv.fields[-3:]:
            self.assertArrayEqual(expected, field.raw[1:13])

    def test_override_final_bound(self):
        expected = (1, 2, 3, 4, 5, 6)
        make_time_bounds_contiguous(self.ffv, expected)
        self.assertArrayEqual(self.ffv.fields[-1].raw[7:13], expected)

    def test_exception_for_invalid_final_bound(self):
        expected = (1, 2, 3, 4, 5)
        with self.assertRaisesRegex(
            ValueError, "Final bound needs to be a 6 element sequence"
        ):
            make_time_bounds_contiguous(self.ffv, expected)

    def test_exception_for_too_few_fields(self):
        self.ffv.fields = [self.ffv.fields[0]]
        with self.assertRaisesRegex(ValueError, "Need at least"):
            make_time_bounds_contiguous(self.ffv)

    def test_exception_for_missing_field(self):
        self.ffv.fields = self.ffv.fields[0:17] + self.ffv.fields[18:]
        with self.assertRaisesRegex(ValueError, "Need same number"):
            make_time_bounds_contiguous(self.ffv)

    def assertContiguousFields(self, start, end):
        self.assertArrayEqual(start.raw[1:7], end.raw[7:13])


if __name__ == "__main__":
    ants.tests.main()

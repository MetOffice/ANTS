# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants
import ants.tests as tests
import iris
import numpy as np

try:
    from ants.fileformats.raster import _get_crs, load_cubes
except Exception:
    pass


@tests.skip_gdal
class TestAll(tests.TestCase):
    def setUp(self):
        self.dataset = mock.Mock(name="dataset")
        self.dataset.RasterCount = 1
        self.dataset.GetGeoTransform.return_value = (-180, 25, 0, -90, 0, 25)
        self.dataset.RasterXSize = 5
        self.dataset.RasterYSize = 5
        self.dataset.GetProjection.return_value = ""
        getdata = mock.Mock()
        getdata.ReadAsArray.return_value = np.arange(5 * 5, dtype="int16").reshape(5, 5)
        getdata.GetNoDataValue.return_value = -999
        getdata.DataType = 3
        self.dataset.GetRasterBand.return_value = getdata

        # Set WGS84 as our projection
        gdal_projection = (
            'GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",'
            'SPHEROID["WGS_1984",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],UNIT["Degree",'
            "0.017453292519943295],"
            'AXIS["Latitude",NORTH],'
            'AXIS["Longitude",EAST]]'
        )
        self.dataset.GetProjection.return_value = gdal_projection

        # TODO: Patch the module import so that these unittests do not require
        # the gdal library, see http://www.voidspace.org.uk/python/mock/
        # examples.html#mocking-imports-with-patch-dict
        gdal_patch = mock.patch("osgeo.gdal.Open", return_value=self.dataset)
        self.gdal_patch = gdal_patch.start()
        self.addCleanup(gdal_patch.stop)

    def test_dataset_is_none(self):
        self.gdal_patch.return_value = None
        with self.assertRaisesRegex(IOError, "gdal failed to open raster " "image"):
            next(load_cubes("some_filename"))

    def test_incorrectly_formatted_projection(self):
        gdal_projection = (
            'GEOGCS["unnamed ellipse",DATUM["unknown",'
            'SPHEROID["unnamed",6378137]],'
            'PRIMEM["Greenwich",0],UNIT["degree",'
            "0.019]]"
        )
        self.dataset.GetProjection.return_value = gdal_projection
        msg = "not enough children in SPHEROID node"
        with self.assertRaisesRegex(RuntimeError, msg):
            next(load_cubes("some_filename"))

    def test_unsupported_projection(self):
        gdal_projection = (
            'GEOGCS["unnamed ellipse",DATUM["unknown",'
            'SPHEROID["unnamed",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],UNIT["degree",'
            "0.019]]"
            'AXIS["Latitude",NORTH],'
            'AXIS["Longitude",EAST]]'
        )
        self.dataset.GetProjection.return_value = gdal_projection
        msg = "Projection information not currently in lookup table:"
        with self.assertRaisesRegex(RuntimeError, msg):
            next(load_cubes("some_filename"))

    def assertCRS(self, cube, crs):
        for axis in ["x", "y"]:
            coord = cube.coord(axis=axis)
            self.assertEqual(coord.coord_system, crs.crs)
            self.assertEqual(coord.standard_name, getattr(crs, axis).standard_name)
            self.assertEqual(coord.units, getattr(crs, axis).units)

    def test_crs_wgs84_geodetic(self):
        # Ensure that we correctly interpret the crs from igbp source data.
        gdal_projection = (
            'GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",'
            'SPHEROID["WGS_1984",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],UNIT["Degree",'
            "0.017453292519943295],"
            'AXIS["Latitude",NORTH],'
            'AXIS["Longitude",EAST]]'
        )
        self.dataset.GetProjection.return_value = gdal_projection
        cube = next(load_cubes("some_filename"))

        target_crs = ants.coord_systems.WGS84_GEODETIC
        self.assertCRS(cube, target_crs)

    def test_crs_osgb(self):
        # Ensure that we correctly interpret the crs from ite source data.
        gdal_projection = (
            'PROJCS["OSGB 1936 / British National Grid",'
            'GEOGCS["OSGB 1936",DATUM["OSGB_1936",'
            'SPHEROID["Airy_1830",6377563.396,299.3249646]],'
            'PRIMEM["Greenwich",0],UNIT["Degree",'
            "0.017453292519943295]],PROJECTION["
            '"Transverse_Mercator"],PARAMETER['
            '"latitude_of_origin",49],PARAMETER['
            '"central_meridian",-2],PARAMETER["scale_factor",'
            '0.9996012717],PARAMETER["false_easting",400000],'
            'PARAMETER["false_northing",-100000],'
            'UNIT["Meter",1]]'
        )
        self.dataset.GetProjection.return_value = gdal_projection
        cube = next(load_cubes("some_filename"))

        target_crs = ants.coord_systems.OSGB
        self.assertCRS(cube, target_crs)

    def test_multiple_raster_bands(self):
        # Ensure that CubeList of length corresponding to the number of bands
        # is returned and that each has associated coordinates.
        expected = iris.cube.CubeList()
        cube = ants.tests.stock.gen_regular_cube(
            crs=iris.coord_systems.GeogCS(
                semi_major_axis=6378137.0, semi_minor_axis=6356752.314245179
            ),
            shape=(5, 5),
            xlim=(-180.0, -55.0),
            ylim=(35.0, -90.0),
        )
        expected.append(cube)
        expected.append(cube)
        expected.append(cube)

        self.dataset.RasterCount = 3
        actual = list(load_cubes("some_filename"))

        self.assertEqual(len(actual), self.dataset.RasterCount)
        self.assertEqual(actual, expected)

    def test_no_raster_bands(self):
        self.dataset.RasterCount = 0
        with self.assertRaises(StopIteration):
            next(load_cubes("some_filename"))

    def test_rotated_raster(self):
        # Rotated is where a non north-up image is defined.
        # No test data to-hand to develop interpretation of rotation so an
        # exception is raised.
        rotation = [1, 1]
        self.dataset.GetGeoTransform.return_value = (
            -200000,
            50000,
            rotation[0],
            -200000,
            rotation[1],
            50000,
        )
        msg = r"Rotation not supported: \({}, {}\)"
        msg = msg.format(rotation[0], rotation[1])
        with self.assertRaisesRegex(ValueError, msg):
            next(load_cubes("some_filename"))

    def test_no_gdal_library(self):
        # Ensure that we raise a suitable exception when there is no gdal
        # library present.
        msg = "gdal error"
        ants.fileformats.raster._GDAL_IMPORT_ERROR = ImportError("gdal error")
        with mock.patch("ants.fileformats.raster.gdal", new=None):
            with self.assertRaisesRegex(ImportError, msg):
                next(load_cubes("some_filename"))

    def test_projection_with_correct_axis_order(self):
        gdal_projection = (
            'GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",'
            'SPHEROID["WGS_1984",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],UNIT["Degree",'
            "0.017453292519943295],"
            'AXIS["Latitude",NORTH],'
            'AXIS["Longitude",EAST]]'
        )
        crs = _get_crs(gdal_projection)
        self.assertIsInstance(crs, ants.coord_systems.CFCRS)

    def test_projection_with_incorrect_axis_order(self):
        gdal_projection = (
            'GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",'
            'SPHEROID["WGS_1984",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],UNIT["Degree",'
            "0.017453292519943295],"
            'AXIS["Longitude",EAST],'
            'AXIS["Latitude",NORTH]]'
        )
        crs = _get_crs(gdal_projection)
        self.assertIsInstance(crs, ants.coord_systems.CFCRS)

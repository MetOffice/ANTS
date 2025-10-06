# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock
from contextlib import contextmanager

import ants.tests
import iris
import numpy as np
from ants.analysis._merge import KDTreeFill


@contextmanager
def enable_scaling(latitude_scale: float):
    original_latitude_scale = ants.config.CONFIG["ants_fill"]["kdtree_latitude_scale"]
    ants.config.CONFIG["ants_fill"]["kdtree_latitude_scale"] = latitude_scale
    try:
        yield
    finally:
        ants.config.CONFIG["ants_fill"][
            "kdtree_latitude_scale"
        ] = original_latitude_scale


class TestGeodeticSourceOnly(ants.tests.TestCase):
    def setUp(self):
        """Create a geodetic source cube with missing points.

        There are masked points at:
        * -36 latitude -144 longitude, index (1, 0)
        * 0 latitude 0 longitude, index (2, 2)

        The data array is indexed first by latitude, then by longitude,
        both in ascending order.

        Source
        ------
        lat
         72  20  21  22  23  24
         36  15  16  17  18  19
          0  10  11  --  13  14
        -36  --   6   7   8   9
        -72   0   1   2   3   4
            -144 -72  0  72  144 lon

        Filled (no scaling)
        -------------------
        lat
         72  20  21  22  23  24
         36  15  16  17  18  19
          0  10  11   7  13  14
        -36   0   6   7   8   9
        -72   0   1   2   3   4
            -144 -72  0  72  144 lon

        Filled (with scaling)
        ---------------------
        lat
         72  20  21  22  23  24
         36  15  16  17  18  19
          0  10  11  11  13  14
        -36   9   6   7   8   9
        -72   0   1   2   3   4
            -144 -72  0  72  144 lon
        """
        geodetic_cube = ants.tests.stock.geodetic((5, 5))
        ants.utils.cube.fix_mask(geodetic_cube)
        geodetic_cube.data.mask[1, 0] = True
        geodetic_cube.data.mask[2, 2] = True
        self.source = geodetic_cube

    def test_missing_points_identified_no_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(self.source)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_no_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(self.source)
        expected_replacing_indices_y = np.array([0, 1])
        expected_replacing_indices_x = np.array([0, 2])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_no_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 0
        expected_filled_array[2, 2] = 7

        filler = KDTreeFill(self.source)
        filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)

    def test_latitude_scale_set(self):
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source)
        self.assertEqual(filler.latitude_scale, 5.0)

    def test_missing_points_identified_with_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The missing indices should be the same whether or not scaling is enabled.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_with_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The replacing indices will be different to those identified when scaling
        is not enabled. Points of equal latitude will be selected first.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source)
        expected_replacing_indices_y = np.array([1, 2])
        expected_replacing_indices_x = np.array([4, 1])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_with_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 9
        expected_filled_array[2, 2] = 11

        with enable_scaling(5.0):
            filler = KDTreeFill(self.source)
            filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestGeodeticWithSearchMask(ants.tests.TestCase):
    def setUp(self):
        """Create a geodetic source cube with missing points.

        Create a search mask to constrain the acceptable fill candidates.

        There are masked points at:
        * -36 latitude -144 longitude, index (1, 0)
        * 0 latitude 0 longitude, index (2, 2)

        The data array is indexed first by latitude, then by longitude,
        both in ascending order.

        Source
        ------
        lat
         72  20  21  22  23  24
         36  15  16  17  18  19
          0  10  11  --  13  14
        -36  --   6   7   8   9
        -72   0   1   2   3   4
            -144 -72  0  72  144 lon

        Search mask
        -----------
        1 represents invalid fill candidates
        lat
         72   0   0   0   0   0
         36   0   1   1   1   0
          0   0   1   1   1   0
        -36   1   1   1   1   0
        -72   0   0   0   0   0
            -144 -72  0  72  144 lon

        Filled (no scaling)
        -------------------
        lat
         72  20  21  22  23  24
         36  15  16  17  18  19
          0  10  11   2  13  14
        -36   0   6   7   8   9
        -72   0   1   2   3   4
            -144 -72  0  72  144 lon

        Filled (with scaling)
        ---------------------
        lat
         72  20  21  22  23  24
         36  15  16  17  18  19
          0  10  11  10  13  14
        -36   9   6   7   8   9
        -72   0   1   2   3   4
            -144 -72  0  72  144 lon
        """
        geodetic_cube = ants.tests.stock.geodetic((5, 5))
        ants.utils.cube.fix_mask(geodetic_cube)
        geodetic_cube.data.mask[1, 0] = True
        geodetic_cube.data.mask[2, 2] = True
        self.source = geodetic_cube

        search_mask = geodetic_cube.copy()
        search_mask.data = np.zeros((5, 5), dtype=bool)
        search_mask.data[
            (1, 1, 1, 1, 2, 2, 2, 3, 3, 3), (0, 1, 2, 3, 1, 2, 3, 1, 2, 3)
        ] = True
        self.search_mask = search_mask

    def test_missing_points_identified_no_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(source=self.source, search_mask=self.search_mask)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_no_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(source=self.source, search_mask=self.search_mask)
        expected_replacing_indices_y = np.array([0, 0])
        expected_replacing_indices_x = np.array([0, 2])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_no_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 0
        expected_filled_array[2, 2] = 2

        filler = KDTreeFill(source=self.source, search_mask=self.search_mask)
        filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)

    def test_latitude_scale_set(self):
        with enable_scaling(5.0):
            filler = KDTreeFill(source=self.source, search_mask=self.search_mask)
        self.assertEqual(filler.latitude_scale, 5.0)

    def test_missing_points_identified_with_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The missing indices should be the same whether or not scaling is enabled.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(source=self.source, search_mask=self.search_mask)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_with_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The replacing indices will be different to those identified when scaling
        is not enabled. Points of equal latitude will be selected first.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(source=self.source, search_mask=self.search_mask)
        expected_replacing_indices_y = np.array([1, 2])
        expected_replacing_indices_x = np.array([4, 0])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_with_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 9
        expected_filled_array[2, 2] = 10

        with enable_scaling(5.0):
            filler = KDTreeFill(source=self.source, search_mask=self.search_mask)
            filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestGeodeticWithTargetMask(ants.tests.TestCase):
    def setUp(self):
        """Create a geodetic source cube with missing points.

        Create a target mask to be applied to the filled cube.

        There are masked points at:
        * -36 latitude -144 longitude, index (1, 0)
        * 0 latitude 0 longitude, index (2, 2)
        * 0 latitude 144 longitude, index (2, 4)

        The masked point at (2, 4) should not be filled, it should remain masked,
        because it appears in the target mask.

        The data array is indexed first by latitude, then by longitude,
        both in ascending order.

        Source
        ------
        lat
         72  20  21  22  23  24
         36  15  16  17  18  19
          0  10  11  --  13  --
        -36  --   6   7   8   9
        -72   0   1   2   3   4
            -144 -72  0  72  144 lon

        Target mask
        -----------
        lat
         72   0   0   0   0   1
         36   0   1   0   0   1
          0   0   0   0   0   1
        -36   0   0   0   0   1
        -72   1   0   0   0   1
            -144 -72  0  72  144 lon

        Filled (no scaling)
        -------------------
        Note that point (0, 0) fills missing point (1, 0) with value 0,
        even though point (0, 0) ends up masked in the final result.
        lat
         72  20  21  22  23  --
         36  15  --  17  18  --
          0  10  11   7  13  --
        -36   0   6   7   8  --
        -72  --   1   2   3  --
            -144 -72  0  72  144 lon

        Filled (with scaling)
        ---------------------
        Note that point (1, 4) fills missing point (1, 0) with value 9,
        even though point (1, 4) ends up masked in the final result.
        lat
         72  20  21  22  23  --
         36  15  --  17  18  --
          0  10  11  11  13  --
        -36   9   6   7   8  --
        -72  --   1   2   3  --
            -144 -72  0  72  144 lon
        """
        geodetic_cube = ants.tests.stock.geodetic((5, 5))
        ants.utils.cube.fix_mask(geodetic_cube)
        geodetic_cube.data.mask[1, 0] = True
        geodetic_cube.data.mask[2, 2] = True
        self.source = geodetic_cube

        target_mask = geodetic_cube.copy()
        target_mask.data = np.zeros((5, 5), dtype=bool)
        target_mask.data[:, 4] = True
        target_mask.data[0, 0] = True
        target_mask.data[3, 1] = True
        self.target_mask = target_mask

    def test_missing_points_identified_no_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(source=self.source, target_mask=self.target_mask)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_no_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(source=self.source, target_mask=self.target_mask)
        expected_replacing_indices_y = np.array([0, 1])
        expected_replacing_indices_x = np.array([0, 2])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_no_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 0
        expected_filled_array[2, 2] = 7
        expected_filled_array.mask = self.target_mask.data

        filler = KDTreeFill(source=self.source, target_mask=self.target_mask)
        filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)

    def test_latitude_scale_set(self):
        with enable_scaling(5.0):
            filler = KDTreeFill(source=self.source, target_mask=self.target_mask)
        self.assertEqual(filler.latitude_scale, 5.0)

    def test_missing_points_identified_with_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The missing indices should be the same whether or not scaling is enabled.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(source=self.source, target_mask=self.target_mask)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_with_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The replacing indices will be different to those identified when scaling
        is not enabled. Points of equal latitude will be selected first.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(source=self.source, target_mask=self.target_mask)
        expected_replacing_indices_y = np.array([1, 2])
        expected_replacing_indices_x = np.array([4, 1])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_with_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 9
        expected_filled_array[2, 2] = 11
        expected_filled_array.mask = self.target_mask.data

        with enable_scaling(5.0):
            filler = KDTreeFill(source=self.source, target_mask=self.target_mask)
            filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestGeodeticWithSearchAndTargetMask(ants.tests.TestCase):
    def setUp(self):
        """Create a geodetic source cube with missing points.

        Create a search mask to constrain the acceptable fill candidates.

        Create a target mask to be applied to the filled cube.

        There are masked points at:
        * -36 latitude -144 longitude, index (1, 0)
        * 0 latitude 0 longitude, index (2, 2)
        * 0 latitude 144 longitude, index (2, 4)

        The masked point at (2, 4) should not be filled, it should remain masked,
        because it appears in the target mask.

        The data array is indexed first by latitude, then by longitude,
        both in ascending order.

        Source
        ------
        lat
         72  20  21  22  23  24
         36  15  16  17  18  19
          0  10  11  --  13  --
        -36  --   6   7   8   9
        -72   0   1   2   3   4
            -144 -72  0  72  144 lon

        Search mask
        -----------
        1 represents invalid fill candidates
        lat
         72   0   0   0   0   0
         36   0   1   1   1   0
          0   0   1   1   1   0
        -36   1   1   1   1   0
        -72   0   0   0   0   0
            -144 -72  0  72  144 lon

        Target mask
        -----------
        lat
         72   0   0   0   0   1
         36   0   0   0   0   1
          0   0   0   0   0   1
        -36   0   1   1   1   1
        -72   1   0   0   0   1
            -144 -72  0  72  144 lon

        Filled (no scaling)
        -------------------
        Note that point (0, 0) fills missing point (1, 0) with value 0,
        even though point (0, 0) ends up masked in the final result.
        lat
         72  20  21  22  23  --
         36  15  16  17  18  --
          0  10  11   2  13  --
        -36   0  --  --  --  --
        -72  --   1   2   3  --
            -144 -72  0  72  144 lon

        Filled (with scaling)
        ---------------------
        Note that point (1, 4) fills missing point (1, 0) with value 9,
        even though point (1, 4) ends up masked in the final result.
        lat
         72  20  21  22  23  --
         36  15  16  17  18  --
          0  10  11  10  13  --
        -36   9  --  --  --  --
        -72  --   1   2   3  --
            -144 -72  0  72  144 lon
        """
        geodetic_cube = ants.tests.stock.geodetic((5, 5))
        ants.utils.cube.fix_mask(geodetic_cube)
        geodetic_cube.data.mask[1, 0] = True
        geodetic_cube.data.mask[2, 2] = True
        self.source = geodetic_cube

        search_mask = geodetic_cube.copy()
        search_mask.data = np.zeros((5, 5), dtype=bool)
        search_mask.data[
            (1, 1, 1, 1, 2, 2, 2, 3, 3, 3), (0, 1, 2, 3, 1, 2, 3, 1, 2, 3)
        ] = True
        self.search_mask = search_mask

        target_mask = geodetic_cube.copy()
        target_mask.data = np.zeros((5, 5), dtype=bool)
        target_mask.data[:, 4] = True
        target_mask.data[1, 1:] = True
        target_mask.data[0, 0] = True
        self.target_mask = target_mask

    def test_missing_points_identified_no_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(
            source=self.source,
            search_mask=self.search_mask,
            target_mask=self.target_mask,
        )
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_no_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(
            source=self.source,
            search_mask=self.search_mask,
            target_mask=self.target_mask,
        )
        expected_replacing_indices_y = np.array([0, 0])
        expected_replacing_indices_x = np.array([0, 2])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_no_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 0
        expected_filled_array[2, 2] = 2
        expected_filled_array.mask = self.target_mask.data

        filler = KDTreeFill(
            source=self.source,
            search_mask=self.search_mask,
            target_mask=self.target_mask,
        )
        filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)

    def test_latitude_scale_set(self):
        with enable_scaling(5.0):
            filler = KDTreeFill(
                source=self.source,
                search_mask=self.search_mask,
                target_mask=self.target_mask,
            )
        self.assertEqual(filler.latitude_scale, 5.0)

    def test_missing_points_identified_with_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The missing indices should be the same whether or not scaling is enabled.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(
                source=self.source,
                search_mask=self.search_mask,
                target_mask=self.target_mask,
            )
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_with_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The replacing indices will be different to those identified when scaling
        is not enabled. Points of equal latitude will be selected first.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(
                source=self.source,
                search_mask=self.search_mask,
                target_mask=self.target_mask,
            )
        expected_replacing_indices_y = np.array([1, 2])
        expected_replacing_indices_x = np.array([4, 0])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_with_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 9
        expected_filled_array[2, 2] = 10
        expected_filled_array.mask = self.target_mask.data

        with enable_scaling(5.0):
            filler = KDTreeFill(
                source=self.source,
                search_mask=self.search_mask,
                target_mask=self.target_mask,
            )
            filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestOSGBSourceOnly(ants.tests.TestCase):
    def setUp(self):
        """Create a source on the OSGB projection with missing points.

        The source domain spans the same distance in the x and y directions, but
        is higher resolution in the y dimension. Therefore, with no latitude scaling,
        neighbouring rows are closer than neighbouring columns. With latitude scaling
        enabled, neighbouring columns are closer than neighbouring rows.

        Source
        ------
        25  26  27  28  29
        20  21  22  23  24
        15  16  17  18  19
        10  11  --  13  14
        --   6   7   8   9
         0   1   2   3   4

        Filled (no scaling)
        -------------------
        25  26  27  28  29
        20  21  22  23  24
        15  16  17  18  19
        10  11   7  13  14
         0   6   7   8   9
         0   1   2   3   4

        Filled (with scaling)
        ---------------------
        25  26  27  28  29
        20  21  22  23  24
        15  16  17  18  19
        10  11  13  13  14
         6   6   7   8   9
         0   1   2   3   4
        """
        osgb_cube = ants.tests.stock.osgb((6, 5), xlim=(0, 700_000), ylim=(0, 700_000))
        ants.utils.cube.fix_mask(osgb_cube)
        osgb_cube.data.mask[1, 0] = True
        osgb_cube.data.mask[2, 2] = True
        self.source = osgb_cube

    def test_missing_points_identified_no_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(self.source)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_no_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(self.source)
        expected_replacing_indices_y = np.array([0, 1])
        expected_replacing_indices_x = np.array([0, 2])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_no_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 0
        expected_filled_array[2, 2] = 7

        filler = KDTreeFill(self.source)
        filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)

    def test_latitude_scale_set(self):
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source)
        self.assertEqual(filler.latitude_scale, 5.0)

    def test_missing_points_identified_with_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The missing indices should be the same whether or not scaling is enabled.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_with_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The replacing indices will be different to those identified when scaling
        is not enabled. Points of equal latitude will be selected first.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source)
        expected_replacing_indices_y = np.array([1, 2])
        expected_replacing_indices_x = np.array([1, 3])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_with_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 6
        expected_filled_array[2, 2] = 13

        with enable_scaling(5.0):
            filler = KDTreeFill(self.source)
            filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestOSGBWithSearchMask(ants.tests.TestCase):
    def setUp(self):
        """Create a source on the OSGB projection with missing points.

        The source domain spans the same distance in the x and y directions, but
        is higher resolution in the y dimension. Therefore, with no latitude scaling,
        neighbouring rows are closer than neighbouring columns. With latitude scaling
        enabled, neighbouring columns are closer than neighbouring rows.

        Note that since this is a regional domain, there is no wraparound, i.e. column
        0 does not neighbour column 4.

        Source
        ------
        25  26  27  28  29
        20  21  22  23  24
        15  16  17  18  19
        10  11  --  13  14
        --   6   7   8   9
         0   1   2   3   4

        Search mask
        -----------
        0   0   0   0   0
        0   0   0   0   0
        0   1   1   1   0
        0   1   1   1   0
        1   1   1   1   0
        0   0   0   0   0

        Filled (no scaling)
        -------------------
        25  26  27  28  29
        20  21  22  23  24
        15  16  17  18  19
        10  11   2  13  14
         0   6   7   8   9
         0   1   2   3   4

        Filled (with scaling)
        ---------------------
        25  26  27  28  29
        20  21  22  23  24
        15  16  17  18  19
        10  11  14  13  14
        10   6   7   8   9
         0   1   2   3   4
        """
        osgb_cube = ants.tests.stock.osgb((6, 5), xlim=(0, 700_000), ylim=(0, 700_000))
        ants.utils.cube.fix_mask(osgb_cube)
        osgb_cube.data.mask[1, 0] = True
        osgb_cube.data.mask[2, 2] = True
        self.source = osgb_cube

        search_mask = osgb_cube.copy()
        search_mask.data = np.zeros((6, 5), dtype=bool)
        search_mask.data[1, 0] = True
        search_mask.data[1:4, 1:4] = True
        self.search_mask = search_mask

    def test_missing_points_identified_no_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(self.source, self.search_mask)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_no_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(self.source, self.search_mask)
        expected_replacing_indices_y = np.array([0, 0])
        expected_replacing_indices_x = np.array([0, 2])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_no_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 0
        expected_filled_array[2, 2] = 2

        filler = KDTreeFill(self.source, self.search_mask)
        filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)

    def test_latitude_scale_set(self):
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source, self.search_mask)
        self.assertEqual(filler.latitude_scale, 5.0)

    def test_missing_points_identified_with_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The missing indices should be the same whether or not scaling is enabled.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source, self.search_mask)
        expected_missing_indices_y = np.array([1, 2])
        expected_missing_indices_x = np.array([0, 2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_with_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The replacing indices will be different to those identified when scaling
        is not enabled. Points of equal latitude will be selected first.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source, self.search_mask)
        expected_replacing_indices_y = np.array([2, 2])
        expected_replacing_indices_x = np.array([0, 4])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_with_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[1, 0] = 10
        expected_filled_array[2, 2] = 14

        with enable_scaling(5.0):
            filler = KDTreeFill(self.source, self.search_mask)
            filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestOSGBWithSearchAndTargetMask(ants.tests.TestCase):
    def setUp(self):
        """Create a source on the OSGB projection with missing points.

        The source domain spans the same distance in the x and y directions, but
        is higher resolution in the y dimension. Therefore, with no latitude scaling,
        neighbouring rows are closer than neighbouring columns. With latitude scaling
        enabled, neighbouring columns are closer than neighbouring rows.

        Note that since this is a regional domain, there is no wraparound, i.e. column
        0 does not neighbour column 4.

        Source
        ------
        25  26  27  28  29
        20  21  22  23  24
        15  16  17  18  19
        10  11  --  13  14
        --   6   7   8   9
         0   1   2   3   4

        Search mask
        -----------
        0   0   0   0   0
        0   0   0   0   0
        0   1   1   1   0
        0   1   1   1   0
        1   1   1   1   0
        0   0   0   0   0

        Target mask
        -----------
        0   0   0   1   1
        0   0   0   1   1
        0   0   0   0   0
        1   0   0   0   0
        1   0   0   0   0
        1   0   0   0   0

        Filled (no scaling)
        -------------------
        25  26  27  --  --
        20  21  22  --  --
        15  16  17  --  --
        --  11   2  13  14
        --   6   7   8   9
        --   1   2   3   4

        Filled (with scaling)
        ---------------------
        25  26  27  --  --
        20  21  22  --  --
        15  16  17  --  --
        --  11  14  13  14
        --   6   7   8   9
        --   1   2   3   4
        """
        osgb_cube = ants.tests.stock.osgb((6, 5), xlim=(0, 700_000), ylim=(0, 700_000))
        ants.utils.cube.fix_mask(osgb_cube)
        osgb_cube.data.mask[1, 0] = True
        osgb_cube.data.mask[2, 2] = True
        self.source = osgb_cube

        search_mask = osgb_cube.copy()
        search_mask.data = np.zeros((6, 5), dtype=bool)
        search_mask.data[1, 0] = True
        search_mask.data[1:4, 1:4] = True
        self.search_mask = search_mask

        target_mask = osgb_cube.copy()
        target_mask.data = np.zeros((6, 5), dtype=bool)
        target_mask.data[:3, 0] = True
        target_mask.data[3:, 3:] = True
        self.target_mask = target_mask

    def test_missing_points_identified_no_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(self.source, self.search_mask, self.target_mask)
        expected_missing_indices_y = np.array([2])
        expected_missing_indices_x = np.array([2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_no_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        filler = KDTreeFill(self.source, self.search_mask, self.target_mask)
        expected_replacing_indices_y = np.array([0])
        expected_replacing_indices_x = np.array([2])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_no_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[2, 2] = 2
        expected_filled_array.mask = self.target_mask.data

        filler = KDTreeFill(self.source, self.search_mask, self.target_mask)
        filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)

    def test_latitude_scale_set(self):
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source, self.search_mask, self.target_mask)
        self.assertEqual(filler.latitude_scale, 5.0)

    def test_missing_points_identified_with_scaling(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The missing indices should be the same whether or not scaling is enabled.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source, self.search_mask, self.target_mask)
        expected_missing_indices_y = np.array([2])
        expected_missing_indices_x = np.array([2])
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_replacing_points_identified_with_scaling(self):
        """Test that the points to replace the missing ones are identified.

        The _replacing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.

        The replacing indices will be different to those identified when scaling
        is not enabled. Points of equal latitude will be selected first.
        """
        with enable_scaling(5.0):
            filler = KDTreeFill(self.source, self.search_mask, self.target_mask)
        expected_replacing_indices_y = np.array([2])
        expected_replacing_indices_x = np.array([4])
        self.assertArrayEqual(
            filler._replacing_indices_2d[0], expected_replacing_indices_y
        )
        self.assertArrayEqual(
            filler._replacing_indices_2d[1], expected_replacing_indices_x
        )

    def test_filled_with_scaling(self):
        """Test that the missing points are filled."""
        expected_filled_array = self.source.data.copy()
        expected_filled_array[2, 2] = 14
        expected_filled_array.mask = self.target_mask.data

        with enable_scaling(5.0):
            filler = KDTreeFill(self.source, self.search_mask, self.target_mask)
            filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestNoMissing(ants.tests.TestCase):
    """Test case where there is no missing data in the source."""

    def setUp(self):
        self.source = ants.tests.stock.geodetic((3, 3))
        ants.utils.cube.fix_mask(self.source)

        target_mask = np.zeros(self.source.shape, dtype=bool)
        target_mask[1:, 2] = True
        self.target_mask = self.source.copy(target_mask)

    def test_no_fill(self):
        """Test that the 'filled' cube is identical to the source."""
        self.assertFalse(np.ma.is_masked(self.source.data))
        expected = self.source.data.copy()
        filler = KDTreeFill(self.source)
        filler(self.source)
        self.assertArrayEqual(self.source.data, expected)

    def test_mask_inherited(self):
        """Test that the target mask is inherited by the filled cube."""
        self.assertFalse(np.ma.is_masked(self.source.data))
        expected_filled_array = self.source.data.copy()
        expected_filled_array.mask = self.target_mask.data

        filler = KDTreeFill(self.source, target_mask=self.target_mask)
        filler(self.source)
        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestNaNFilled(ants.tests.TestCase):
    """Test that NaNs are also treated as missing data points."""

    def setUp(self):
        """
        Source
        ------
        ma   1   2

         3  na  ma

        na   7   8

        Notes:
        Source domain is limited to x = (0, 10) and y = (0, 30), so there should
        be no longitude wrapping. Also, since points are spaced further in the y
        dimension, filling should be primarily row based.
        """
        self.source = ants.tests.stock.geodetic((3, 3), xlim=(0, 10), ylim=(0, 30))
        self.source.data = self.source.data.astype(float)
        ants.utils.cube.fix_mask(self.source)
        self.source.data.mask[0, 0] = True
        self.source.data.mask[1, 2] = True
        self.source.data[1, 1] = np.nan
        self.source.data[2, 0] = np.nan

    def test_missing_points_identified(self):
        """Test that missing points are identified.

        The _missing_indices_2d attribute of the filler is a tuple of integer
        arrays representing the y and x indices of the missing points.
        """
        expected_missing_indices_y = np.array([0, 1, 1, 2])
        expected_missing_indices_x = np.array([0, 1, 2, 0])
        filler = KDTreeFill(self.source)
        self.assertArrayEqual(filler._missing_indices_2d[0], expected_missing_indices_y)
        self.assertArrayEqual(filler._missing_indices_2d[1], expected_missing_indices_x)

    def test_missing_points_filled(self):
        expected_filled_array = self.source.data.copy()
        expected_filled_array[0, 0] = 1
        expected_filled_array[1, 1] = 3
        expected_filled_array[1, 2] = 3
        expected_filled_array[2, 0] = 7

        filler = KDTreeFill(self.source)
        filler(self.source)
        self.assertMaskedArrayEqual(self.source.data, expected_filled_array)


class TestCaching(ants.tests.TestCase):
    def setUp(self):
        """
        Source 0
        --------
        m   1   2

        3   4   m

        6   7   8

        Notes:
        Source domain is limited to x = (0, 10) and y = (0, 30), so there should
        be no longitude wrapping. Also, since points are spaced further in the y
        dimension, filling should be primarily row based.
        Sources 1 and 2 are identical to source 0 but with each data value
        incremented by 1 and 2 respectively. The same points are masked.
        """
        source = ants.tests.stock.geodetic((3, 3), xlim=(0, 10), ylim=(0, 30))
        ants.utils.cube.fix_mask(source)
        source.data.mask[0, 0] = True
        source.data.mask[1, 2] = True
        self.source0 = source.copy()
        self.source1 = source.copy()
        self.source1.data += 1
        self.source2 = source.copy()
        self.source2.data += 2

        self.assertArrayEqual(self.source0.data.mask, self.source1.data.mask)
        self.assertArrayEqual(self.source0.data.mask, self.source2.data.mask)

    def test_all_points_filled(self):
        expected_filled0 = self.source0.data.copy()
        expected_filled0[0, 0] = 1
        expected_filled0[1, 2] = 4

        expected_filled1 = self.source1.data.copy()
        expected_filled1[0, 0] = 2
        expected_filled1[1, 2] = 5

        expected_filled2 = self.source2.data.copy()
        expected_filled2[0, 0] = 3
        expected_filled2[1, 2] = 6

        filler = KDTreeFill(self.source0)
        filler(self.source0)
        filler(self.source1)
        filler(self.source2)

        self.assertMaskedArrayEqual(self.source0.data, expected_filled0)
        self.assertMaskedArrayEqual(self.source1.data, expected_filled1)
        self.assertMaskedArrayEqual(self.source2.data, expected_filled2)

    def test_kdtree_query(self):
        """Test that the KDTree is only queried once."""
        with mock.patch("ants.analysis._merge.KDTree") as mock_kdtree:
            # set a dummy return value for the query method
            mock_kdtree_instance = mock_kdtree.return_value
            mock_kdtree_instance.query.return_value = (None, [0])
            filler = KDTreeFill(self.source0)
            filler(self.source0)
            filler(self.source1)
            filler(self.source2)
        mock_kdtree_instance.query.assert_called_once()


class TestNDSupport(ants.tests.TestCase):
    def setUp(self):
        """Create a source with two horizontal dimensions and a third dimension.
        Source 0
        --------
        m   1   2

        3   4   m

        6   7   8

        Source 1
        --------
        m   2   3

        4   5   m

        7   8   9
        """
        base_source = ants.tests.stock.geodetic((3, 3), xlim=(0, 10), ylim=(0, 30))
        ants.utils.cube.fix_mask(base_source)
        base_source.data.mask[0, 0] = True
        base_source.data.mask[1, 2] = True

        source0 = base_source.copy()
        source0.add_aux_coord(iris.coords.AuxCoord(0, long_name="bing"), None)
        source1 = base_source.copy() + 1
        source1.add_aux_coord(iris.coords.AuxCoord(1, long_name="bing"), None)
        self.source = iris.cube.CubeList([source0, source1]).merge_cube()

    def test_all_points_filled(self):
        expected_filled = self.source.data.copy()
        expected_filled[0, 0, 0] = 1
        expected_filled[0, 1, 2] = 4
        expected_filled[1, 0, 0] = 2
        expected_filled[1, 1, 2] = 5

        filler = KDTreeFill(self.source)
        filler(self.source)

        self.assertMaskedArrayEqual(self.source.data, expected_filled)

    def test_kdtree_query(self):
        """Test that the KDTree is only queried once."""
        with mock.patch("ants.analysis._merge.KDTree") as mock_kdtree:
            # set a dummy return value for the query method
            mock_kdtree_instance = mock_kdtree.return_value
            mock_kdtree_instance.query.return_value = (None, [0])
            filler = KDTreeFill(self.source)
            filler(self.source)
        mock_kdtree_instance.query.assert_called_once()


class TestExceptions(ants.tests.TestCase):
    def setUp(self):
        # Intentionally limit ourselves to the simplest case where distance
        # constraints and cyclic behaviour is not observed.

        self.source = ants.tests.stock.geodetic((3, 3), xlim=(3, 5), ylim=(3, 5))
        source_mask = np.array(
            [[True, False, False], [False, False, False], [True, True, False]]
        )
        self.source.data = np.ma.array(self.source.data, mask=source_mask)

        target_mask = np.array(
            [[False, False, True], [True, False, False], [False, True, True]]
        )
        self.target_mask = self.source.copy(target_mask)

    def test_target_mask_not_2dim(self):
        # Make a 3dim target mask.
        self.target_mask = iris.cube.CubeList(
            [self.target_mask.copy(), self.target_mask.copy()]
        )
        self.target_mask[0].add_aux_coord(
            iris.coords.AuxCoord(0, long_name="bing"), None
        )
        self.target_mask[1].add_aux_coord(
            iris.coords.AuxCoord(1, long_name="bing"), None
        )
        self.target_mask = self.target_mask.merge_cube()

        msg = "Expecting a 2-dimensional target_mask, got 3-dimensions."
        with self.assertRaisesRegex(ValueError, msg):
            KDTreeFill(self.source, target_mask=self.target_mask)

    def test_target_mask_coords_incompatible_with_source(self):
        points = self.target_mask.coord(axis="y").points.copy()
        points[0] = points[0] + 1e-6
        self.target_mask.coord(axis="y").points = points

        msg = (
            "The provided target_mask's y coordinates do not match "
            "those of the source."
        )
        with self.assertRaisesRegex(ValueError, msg):
            KDTreeFill(self.source, target_mask=self.target_mask)

    def test_search_mask_coords_incompatible_with_source(self):
        points = self.target_mask.coord(axis="x").points.copy()
        points[0] = points[0] + 1e-6
        self.target_mask.coord(axis="x").points = points

        msg = (
            "The provided search_mask's x coordinates do not match "
            "those of the source."
        )
        with self.assertRaisesRegex(ValueError, msg):
            KDTreeFill(self.source, search_mask=self.target_mask)

    def test_source_coords_incompatibility_with_cache(self):
        nfiller = KDTreeFill(self.source, target_mask=self.target_mask)
        points = self.source.coord(axis="x").points.copy()
        points[0] = points[0] + 1e-6
        self.source.coord(axis="x").points = points
        msg = (
            "The provided destination cube's x coordinates do not "
            "match those of the source."
        )
        with self.assertRaisesRegex(ValueError, msg):
            nfiller(self.source)

    def test_source_mask_incompatibility_with_cache(self):
        nfiller = KDTreeFill(self.source, target_mask=self.target_mask)
        self.source.data.mask = ~self.source.data.mask
        msg = "Destination mask is not compatible with the cached nearest neighbours."
        with self.assertRaisesRegex(ValueError, msg):
            nfiller(self.source)

    def test_no_valid_data(self):
        # When no valid data is present, the spiral search returns a negative
        # index.  The spiral search can cause segmentation faults
        # in this case so we capture the case ourselves.
        # Ensure we provide additional context to users to help users.
        self.source.data[:] = np.ma.masked
        self.target_mask.data[:] = False
        msg = ".*any valid data."
        with self.assertRaisesRegex(ValueError, msg):
            KDTreeFill(self.source, target_mask=self.target_mask)


if __name__ == "__main__":
    ants.tests.main()

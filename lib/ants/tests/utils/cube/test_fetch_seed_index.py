# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
from ants.utils.cube import fetch_seed_index


class TestAll(ants.tests.TestCase):
    def test_seed_outside_domain_raises_ValueError(self):
        """
        Test that when the seed point is outside of the domain of the source,
        a ValueError is raised.
        """
        source = ants.tests.stock.gen_regular_cube(
            crs=ants.coord_systems.UM_SPHERE.crs,
            shape=(10, 10),
            xlim=(-10, 10),
            ylim=(-10, 10),
        )
        # Note: xlim and ylim above refer to the bounds of the coords, so the
        # source cube has coords with points:
        # x.points = [-9, -7, -5, -3, -1, 1, 3, 5, 7, 9]
        # y.points = [-9, -7, -5, -3, -1, 1, 3, 5, 7, 9]
        seed_point = (11, 11)
        expected_msg = (
            r"Seed value x,y:\(11, 11\) is not contained within the extent of the "
            r"extracted domain: xlim \[-9.0, 9.0\], ylim \[-9.0, 9.0\]"
        )
        with self.assertRaisesRegex(ValueError, expected_msg):
            fetch_seed_index(source, seed_point)

    def test_seed_inside_regional_domain(self):
        """
        Test that the correct seed index is identified when using a regional source.
        """
        source = ants.tests.stock.gen_regular_cube(
            crs=ants.coord_systems.UM_SPHERE.crs,
            shape=(10, 10),
            xlim=(-10, 10),
            ylim=(-10, 10),
        )
        # index    = [ 0,  1,  2,  3,  4, 5, 6, 7, 8, 9]
        # x.points = [-9, -7, -5, -3, -1, 1, 3, 5, 7, 9]
        # y.points = [-9, -7, -5, -3, -1, 1, 3, 5, 7, 9]
        seed_point = (2.5, -5.5)
        # seed_y =  2.5 is closest to source y point of  3, which has index of 6
        # seed_x = -5.5 is closest to source x point of -5, which has index of 2
        expected_index_x = 2
        expected_index_y = 6

        seed_index = fetch_seed_index(source, seed_point)
        self.assertEqual(seed_index, (expected_index_x, expected_index_y))

    def test_seed_inside_global_domain(self):
        """
        Test that the correct seed index is identified when using a global source.
        """
        source = ants.tests.stock.geodetic(shape=(18, 36))
        # Coordinate arrays are at odd multiples of 5, i.e.
        # x.points = [-175, -165, -155, ..., 155, 165, 175]
        # y.points = [-85., -75., ..., 75., 85.]
        seed_point = (-61.0, 151.0)
        # seed_y = -61 is closest to source y point -65, which has index of 2
        # seed_x = 151 is closest to source x point 155, which has index of 33
        expected_index_x = 33
        expected_index_y = 2

        seed_index = fetch_seed_index(source, seed_point)
        self.assertEqual(seed_index, (expected_index_x, expected_index_y))

    def test_seed_inside_osgb_domain(self):
        """
        Test that the correct seed index is identified when using an OSGB source.
        """
        source = ants.tests.stock.osgb(shape=(20, 20))
        # Coordinate arrays look like:
        # x.points = [-19000000.0, -17000000.0, -15000000.0, ..., 19000000.0]
        # y.points = [-9500000.0, -8500000.0, -7500000.0, ..., 9500000.0]
        seed_point = (7500001.0, -15000001.0)
        expected_index_x = 2
        expected_index_y = 17

        seed_index = fetch_seed_index(source, seed_point)
        self.assertEqual(seed_index, (expected_index_x, expected_index_y))

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import ants.tests
from ants.utils.cube import _is_ugrid as is_ugrid


class TestAll(ants.tests.TestCase):
    # Want to be careful not to test the implementation here (i.e. can't just
    # mock something with the right 'Conventions' attribute), because we're
    # not committed yet on how to identify UGrid meshes.

    def test_regular_grid(self):
        self.assertFalse(is_ugrid(ants.tests.stock.geodetic((1, 1))))

    def test_mesh(self):
        ugrid_cube = ants.tests.stock.geodetic((1, 1))
        ugrid_cube.attributes["Conventions"] = "UGRID"
        self.assertTrue(is_ugrid(ugrid_cube))

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
import numpy as np
from ants.analysis._merge import horizontal_grid_reorder


class Common(object):
    def custom_assert(self, data, tdata, mask, tmask):
        if tmask is False:
            # horizontal_grid_reorder expands the mask
            tmask = np.zeros(mask.shape, dtype="bool")

        self.assertArrayEqual(data, tdata)
        if isinstance(tmask, bool):
            self.assertIs(mask, tmask)
        else:
            self.assertArrayEqual(mask, tmask)
        # Ensure that views are returned (i.e. they share the same memory).
        self.assertTrue(np.may_share_memory(data, self.source.data))
        if np.ma.isMaskedArray(self.source.data):
            self.assertTrue(np.may_share_memory(mask, self.source.data.mask))


class Test2D(Common, ants.tests.TestCase):
    def setUp(self):
        self.source = ants.tests.stock.geodetic((5, 6))

    def test_no_reorder(self):
        tdata = self.source.data.copy()
        data, mask = horizontal_grid_reorder(self.source)
        self.custom_assert(data, tdata, mask, False)

    def test_reorder(self):
        tdata = self.source.data.copy()
        self.source.transpose((1, 0))
        data, mask = horizontal_grid_reorder(self.source)
        self.custom_assert(data, tdata, mask, False)

    def test_masked_reorder(self):
        self.source.data = np.ma.array(self.source.data)
        self.source.data[::2] = np.ma.masked
        tdata = self.source.data.copy()
        self.source.transpose((1, 0))
        data, mask = horizontal_grid_reorder(self.source)
        self.custom_assert(data, tdata.data, mask, tdata.mask)


class Test3D(Common, ants.tests.TestCase):
    def setUp(self):
        source = ants.tests.stock.geodetic((5, 6))
        source2 = source.copy()
        source.add_aux_coord(iris.coords.DimCoord(0, long_name="bla"), None)
        source2.add_aux_coord(iris.coords.DimCoord(1, long_name="bla"), None)
        self.source = iris.cube.CubeList([source, source2]).merge_cube()
        self.source.transpose((1, 2, 0))

    def test_no_reorder(self):
        tdata = self.source.data.copy()
        data, mask = horizontal_grid_reorder(self.source)
        self.custom_assert(data, tdata, mask, False)

    def test_reorder(self):
        tdata = self.source.data.copy()
        self.source.transpose((1, 2, 0))
        data, mask = horizontal_grid_reorder(self.source)
        self.custom_assert(data, tdata, mask, False)

    def test_masked_reorder(self):
        self.source.data = np.ma.array(self.source.data)
        self.source.data[::2] = np.ma.masked
        tdata = self.source.data.copy()
        self.source.transpose((1, 2, 0))
        data, mask = horizontal_grid_reorder(self.source)
        self.custom_assert(data, tdata.data, mask, tdata.mask)


class Test4D(ants.tests.TestCase):
    def test_raise_exception(self):
        cube = mock.Mock(name="cube")
        cube.ndim = 4
        msg = (
            "Grid re-ordering has yet to support cubes of dimensionality "
            "greater then 3"
        )
        with self.assertRaisesRegex(RuntimeError, msg):
            horizontal_grid_reorder(cube)


if __name__ == "__main__":
    ants.tests.main()

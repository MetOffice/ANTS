# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.fileformats.namelist.umgrid import _NamelistGrid as NamelistGrid


class DummyGrid(NamelistGrid):
    defaults = {"a": {"aa": mock.sentinel.aa, "bb": mock.sentinel.bb}}

    def x(self):
        pass

    def y(self):
        pass

    def attributes(self):
        pass

    def shape(self):
        pass

    def coord_system(self):
        pass


class Test___init__(ants.tests.TestCase):
    def test_passing_arguments(self):
        sample = {"a": {"aa": mock.sentinel.cus_aa}}
        grid = DummyGrid(sample)

        for group in grid._raw:
            for subkey in sample[group]:
                self.assertIs(grid._raw[group][subkey], sample[group][subkey])

    def test_missing_group(self):
        sample = {"dummy_group": None}
        msg = r"Cannot deduce grid, the following groups as missing: \['a'\]"
        with self.assertRaisesRegex(IOError, msg):
            DummyGrid(sample)

    def test_unused_group(self):
        # Ensure that the class is not sensitive to unexpected groups
        sample = {"a": {}, mock.sentinel.group: {}}
        DummyGrid(sample)

    def test_defaults_parameters(self):
        # Check that default parameters are set as expected.
        sample = {"a": {}}
        grid = DummyGrid(sample)
        for group in grid._raw:
            for subkey in grid._raw[group]:
                self.assertEqual(grid._raw[group][subkey], grid.defaults[group][subkey])


if __name__ == "__main__":
    ants.tests.main()

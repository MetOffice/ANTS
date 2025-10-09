# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.utils.cube import inherit_metadata


class TestAll(ants.tests.TestCase):
    def testall(self):
        source = mock.Mock(attributes={})
        target = mock.Mock(attributes={})
        target.name.return_value = mock.sentinel.name
        target.units = mock.sentinel.units
        target.attributes["grid_staggering"] = mock.sentinel.grid_staggering

        inherit_metadata(source, target)
        self.assertTrue(source.rename.called_once_with(mock.sentinel.name))
        self.assertIs(source.units, target.units)
        self.assertIs(
            source.attributes["grid_staggering"], target.attributes["grid_staggering"]
        )


if __name__ == "__main__":
    ants.tests.main()

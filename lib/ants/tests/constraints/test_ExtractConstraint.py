# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris
from ants._constraints import ExtractConstraint


class TestAll(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants._constraints._extract_overlap")
        self.patch_eo = patch.start()
        self.addCleanup(patch.stop)

    def test_extract(self):
        target = iris.cube.Cube(0, long_name="target")
        source = iris.cube.Cube(0, long_name="source")
        constraint = ExtractConstraint(
            target,
            fix_period=mock.sentinel.fix_period,
            pad_width=mock.sentinel.pad_width,
        )
        source.extract(constraint)

        self.patch_eo.assert_called_once_with(
            source,
            target,
            fix_period=mock.sentinel.fix_period,
            pad_width=mock.sentinel.pad_width,
        )

    def test_default_args(self):
        target = iris.cube.Cube(0, long_name="target")
        source = iris.cube.Cube(0, long_name="source")
        constraint = ExtractConstraint(target)
        source.extract(constraint)

        self.patch_eo.assert_called_once_with(
            source, target, fix_period=False, pad_width=1
        )


if __name__ == "__main__":
    ants.tests.main()

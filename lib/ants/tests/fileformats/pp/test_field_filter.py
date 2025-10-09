# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris.fileformats.pp as ipp
from ants.fileformats.pp import field_filter


class TestAll(ants.tests.TestCase):
    def test_unsupported(self):
        stash = ipp.STASH(1, 3, 1)
        ppfield = 3
        msg = ".*not a recognised valid field type"
        with self.assertRaisesRegex(TypeError, msg):
            field_filter(ppfield, stash)


class TestPPField(ants.tests.TestCase):
    """Ensure that we support pp file field objects."""

    def test_filter_stash(self):
        stash = ipp.STASH(1, 3, 1)
        ppfield1 = mock.Mock(
            name="ppfield1", spec=ipp.PPField, lbuser=[100, 101, 102, 3001, 104, 105, 1]
        )
        ppfield2 = mock.Mock(
            name="ppfield2", spec=ipp.PPField, lbuser=[100, 101, 102, 3004, 104, 105, 1]
        )
        ppfield3 = mock.Mock(
            name="ppfield3", spec=ipp.PPField, lbuser=[100, 222, 102, 3001, 104, 105, 1]
        )

        result = field_filter([ppfield1, ppfield2, ppfield3], stash)
        self.assertEqual(result, [ppfield1, ppfield3])


if __name__ == "__main__":
    ants.tests.main()

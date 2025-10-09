# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import iris.fileformats.pp as ipp
from ants.fileformats.pp import field_filter_strict


class TestAll(ants.tests.TestCase):
    def test_no_fields_sound(self):
        stash = ipp.STASH(1, 3, 3)
        ppfield1 = mock.Mock(
            name="ppfield1", spec=ipp.PPField, lbuser=[100, 101, 102, 3001, 104, 105, 1]
        )
        ppfield2 = mock.Mock(
            name="ppfield2", spec=ipp.PPField, lbuser=[100, 101, 102, 3004, 104, 105, 1]
        )
        msg = "No fields found matching the filter parameters"
        with self.assertRaisesRegex(RuntimeError, msg):
            field_filter_strict([ppfield1, ppfield2], stash)

    def test_more_than_one_match(self):
        stash = ipp.STASH(1, 3, 1)
        ppfield1 = mock.Mock(
            name="ppfield1", spec=ipp.PPField, lbuser=[100, 101, 102, 3001, 104, 105, 1]
        )
        ppfield2 = mock.Mock(
            name="ppfield2", spec=ipp.PPField, lbuser=[100, 101, 102, 3001, 104, 105, 1]
        )
        msg = "More than one field matches the desired filter parameters"
        with self.assertRaisesRegex(RuntimeError, msg):
            field_filter_strict([ppfield1, ppfield2], stash)

    def test_single_match(self):
        stash = ipp.STASH(1, 3, 1)
        ppfield1 = mock.Mock(
            name="ppfield1", spec=ipp.PPField, lbuser=[100, 101, 102, 3001, 104, 105, 1]
        )
        ppfield2 = mock.Mock(
            name="ppfield2", spec=ipp.PPField, lbuser=[100, 101, 102, 3002, 104, 105, 1]
        )
        result = field_filter_strict([ppfield1, ppfield2], stash)
        self.assertEqual(result, ppfield1)


if __name__ == "__main__":
    ants.tests.main()

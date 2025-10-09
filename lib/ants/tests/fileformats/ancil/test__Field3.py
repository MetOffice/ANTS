# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.fileformats.ancil import _Field3


def mock_field():
    int_headers = np.empty(shape=45, dtype=np.dtype(">u4"))
    int_headers.fill(12345)
    real_headers = np.empty(shape=19, dtype=np.dtype(">f4"))
    return _Field3(
        int_headers=int_headers, real_headers=real_headers, data_provider=None
    )


class Test_is_rotated(ants.tests.TestCase):
    def setUp(self):
        self.field = mock_field()

    def test_true(self):
        self.field.lbcode = 100
        self.assertTrue(self.field.is_rotated)

    def test_false(self):
        self.field.lbcode = 0
        self.assertFalse(self.field.is_rotated)


class Test_is_regular(ants.tests.TestCase):
    def setUp(self):
        self.field = mock_field()

    def test_false_irregular_x(self):
        self.field.x = 0
        self.assertEqual(self.field.is_regular, (False, True))

    def test_false_irregular_y(self):
        self.field.y = 0
        self.assertEqual(self.field.is_regular, (True, False))

    def test_true_no_setting(self):
        # Ensure that we return True when no x or y have been set.
        self.assertEqual(self.field.is_regular, (True, True))

    def test_true(self):
        # Ensure that explicitly assigning x and y to None still returns True.
        self.field.x = None
        self.field.y = None
        self.assertEqual(self.field.is_regular, (True, True))


if __name__ == "__main__":
    ants.tests.main()

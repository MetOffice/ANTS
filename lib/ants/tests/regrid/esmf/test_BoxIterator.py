# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import ants.tests
from ants.regrid.esmf import _BoxIterator as BoxIterator


class Test_1d(ants.tests.TestCase):
    def test_call_args(self):
        dims = (3,)
        count = 0
        for it in BoxIterator(dims):
            it.get_indices()
            count += 1
        self.assertEqual(count, 3)


class Test_2d(ants.tests.TestCase):
    def test_call_args(self):
        dims = (4, 3)
        count = 0
        for it in BoxIterator(dims):
            it.get_indices()
            count += 1
        self.assertEqual(count, 4 * 3)


class Test_3d(ants.tests.TestCase):
    def test_call_args(self):
        dims = (4, 3, 2)
        count = 0
        for it in BoxIterator(dims):
            it.get_indices()
            count += 1
        self.assertEqual(count, 4 * 3 * 2)


class Test_4d(ants.tests.TestCase):
    def test_call_args(self):
        dims = (5, 4, 3, 2)
        count = 0
        for it in BoxIterator(dims):
            it.get_indices()
            count += 1
        self.assertEqual(count, 5 * 4 * 3 * 2)


if __name__ == "__main__":
    ants.tests.main()

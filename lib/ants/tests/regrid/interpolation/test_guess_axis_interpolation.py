# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import ants.tests.stock as stock
from ants.regrid.interpolation import _guess_axis_interpolation


class TestAll(ants.tests.TestCase):
    def check_axis(self, source, target):
        # Perform a double check to ensure no false positive.
        res = _guess_axis_interpolation(source)
        self.assertEqual(res, (target,))

        transpose = [1, 0, 3, 2]
        source.transpose(transpose)
        res = _guess_axis_interpolation(source)
        self.assertEqual(res, (transpose.index(target),))

    def test_model_level_number(self):
        source = stock.simple_4d_with_hybrid_height()
        self.check_axis(source, 1)


if __name__ == "__main__":
    ants.tests.main()

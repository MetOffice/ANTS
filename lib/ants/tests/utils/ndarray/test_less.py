# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
import numpy as np
from ants.utils.ndarray import less


class TestAll(ants.tests.TestCase):
    def test_return(self):
        x1 = np.array([2, 2], dtype="float64")
        x2 = x1.copy()
        x2[0] -= 1e-13
        x2[1] -= 1e-3
        self.assertArrayAlmostEqual(less(x1, x2), [True, False])


if __name__ == "__main__":
    ants.tests.main()

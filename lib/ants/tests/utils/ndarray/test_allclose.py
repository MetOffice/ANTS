# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.utils.ndarray import allclose


class TestAll(ants.tests.TestCase):
    def test_call_without_tolerance(self):
        with mock.patch("numpy.allclose") as pclose:
            with mock.patch("ants.config.TOLERANCE", new=mock.sentinel.tol):
                allclose(mock.sentinel.x1, mock.sentinel.x2)
        pclose.assert_called_once_with(
            mock.sentinel.x1, mock.sentinel.x2, mock.sentinel.tol
        )

    def test_call_with_tolerance(self):
        with mock.patch("numpy.allclose") as pclose:
            allclose(mock.sentinel.x1, mock.sentinel.x2, tolerance=0.1)
        pclose.assert_called_once_with(mock.sentinel.x1, mock.sentinel.x2, 0.1)


if __name__ == "__main__":
    ants.tests.main()

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.fileformats.ancil.template import _ancil_version


class TestAll(ants.tests.TestCase):
    def test_numeric(self):
        with mock.patch("ants.__version__", new="10.2"):
            version = _ancil_version()
        self.assertEqual(version, 1002)

    def test_mixed(self):
        # Ensure that we cope with for example 10.2dev.
        with mock.patch("ants.__version__", new="10.2dev"):
            version = _ancil_version()
        self.assertEqual(version, 1002)


if __name__ == "__main__":
    ants.tests.main()

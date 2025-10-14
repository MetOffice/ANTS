# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import numpy as np
from ants.analysis._merge import FillMissingPoints


class Common(object):
    def setUp(self):
        # Intentionally limit ourselves to the simplest case where distance
        # constraints and cyclic behaviour is not observed.

        self.source = ants.tests.stock.geodetic((3, 3), xlim=(3, 5), ylim=(3, 5))
        source_mask = np.array(
            [[True, False, False], [False, False, False], [True, True, False]]
        )
        self.source.data = np.ma.array(self.source.data, mask=source_mask)

        target_mask = np.array(
            [[False, False, True], [True, False, False], [False, True, True]]
        )
        self.target_mask = self.source.copy(target_mask)
        patch = mock.patch("warnings.warn")
        self.mock_warning = patch.start()
        self.addCleanup(patch.stop)


class TestAll(Common, ants.tests.TestCase):
    def test_UMSpiralSearch_called(self):
        spiral_func = mock.patch(
            "ants.analysis._merge.spiral",
            return_value=np.ones(2, dtype="int"),
        )
        with spiral_func as spiral_patch:
            FillMissingPoints(self.source)
        spiral_patch.assert_called_once()

    def test_deprecation_warning_raised(self):
        FillMissingPoints(self.source)
        self.mock_warning.assert_called_once_with(
            "'ants.analysis.FillMissingPoints' is deprecated as of ANTS 2.0. "
            "The functionality of 'ants.analysis.FillMissingPoints' has been "
            "moved to 'ants.analysis.UMSpiralSearch'.",
            FutureWarning,
        )


if __name__ == "__main__":
    ants.tests.main()

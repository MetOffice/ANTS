# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.config import GlobalConfiguration, _populate_config


class TestAll(ants.tests.TestCase):
    def test_file_parse_order(self):
        mock_config = mock.Mock(GlobalConfiguration)

        with mock.patch(
            "ants.config._DEFAULT_CONFIG_PATHS",
            new=[mock.sentinel.path1, mock.sentinel.path2],
        ):
            _populate_config(mock_config)
        self.assertEqual(
            mock_config.parse_configuration.call_args_list,
            [mock.call(mock.sentinel.path1), mock.call(mock.sentinel.path2)],
        )


if __name__ == "__main__":
    ants.tests.main()

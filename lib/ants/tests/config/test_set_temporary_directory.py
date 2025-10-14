# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import os
import tempfile
from unittest import mock

import ants.tests
from ants.config import set_temporary_directory


@mock.patch.dict(os.environ, {"ANTS_TEMPORARY_DIR": "my/fake/path"})
class TestSetTemporaryDirectory(ants.tests.TestCase):
    def test_set_temporary_configuration_file(self):
        set_temporary_directory()
        self.assertEqual(tempfile.tempdir, "my/fake/path")

    def test_logging_for_temporary_directory(self):
        with self.assertLogs("ants.config", level="INFO") as context_manager:
            set_temporary_directory()
            self.assertEqual(
                context_manager.output,
                ["INFO:ants.config:ANTS_TEMPORARY_DIR is set to: my/fake/path"],
            )


class TestNoTempDirEnvironmentVariableSet(ants.tests.TestCase):
    def test_no_temp_dir_env_var_set(self):
        set_temporary_directory()
        self.assertEqual(tempfile.tempdir, None)


if __name__ == "__main__":
    ants.tests.main()

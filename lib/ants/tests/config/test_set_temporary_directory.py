# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
#
# Parts of this code have been modified with the assistance of
# Met Office Github Copilot.

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
    def setUp(self):
        self._original_ants_dir = os.environ.get("ANTS_TEMPORARY_DIR")
        self._original_tempdir = tempfile.tempdir
        # unset ANTS_TEMPORARY_DIR if it has been set
        os.environ.pop("ANTS_TEMPORARY_DIR", None)

    def tearDown(self):
        # restore ANTS_TEMPORARY_DIR
        if self._original_ants_dir is None:
            os.environ.pop("ANTS_TEMPORARY_DIR", None)
        else:
            os.environ["ANTS_TEMPORARY_DIR"] = self._original_ants_dir
        # restore tempdir
        tempfile.tempdir = self._original_tempdir

    def test_no_temp_dir_env_var_set(self):
        set_temporary_directory()
        self.assertIsNone(tempfile.tempdir)

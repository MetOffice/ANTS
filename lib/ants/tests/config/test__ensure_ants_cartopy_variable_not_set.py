# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import os
from unittest import mock

import ants.tests
import pytest
from ants.config import _ensure_ants_cartopy_variable_not_set


class TestAll(ants.tests.TestCase):
    def test_error_when_variable_set(self):
        """Test that an error is raised when ANTS_CARTOPY_CACHE is set to
        a non-trivial value."""
        expected_message = (
            "The ANTS_CARTOPY_CACHE environment variable is no longer supported "
            "in ANTS from version 2.2. For guidance on configuring cartopy, see "
            "https://cartopy.readthedocs.io/stable/reference/config.html. "
            "ANTS_CARTOPY_CACHE is currently set to 'some/directory'. "
            "To use ants, unset ANTS_CARTOPY_CACHE."
        )
        with mock.patch.dict(os.environ, {"ANTS_CARTOPY_CACHE": "some/directory"}):
            with pytest.raises(EnvironmentError, match=expected_message):
                _ensure_ants_cartopy_variable_not_set()

    def test_error_when_variable_set_null(self):
        """Test that an error is raised when ANTS_CARTOPY_CACHE is set to
        a null value."""
        expected_message = (
            "The ANTS_CARTOPY_CACHE environment variable is no longer supported "
            "in ANTS from version 2.2. For guidance on configuring cartopy, see "
            "https://cartopy.readthedocs.io/stable/reference/config.html. "
            "ANTS_CARTOPY_CACHE is currently set to ''. "
            "To use ants, unset ANTS_CARTOPY_CACHE."
        )
        with mock.patch.dict(os.environ, {"ANTS_CARTOPY_CACHE": ""}):
            with pytest.raises(EnvironmentError, match=expected_message):
                _ensure_ants_cartopy_variable_not_set()

    def test_no_error_raised_when_variable_not_set(self):
        """Test that no error is raised when ANTS_CARTOPY_CACHE is not set."""
        self.assertNotIn("ANTS_CARTOPY_CACHE", os.environ)
        _ensure_ants_cartopy_variable_not_set()

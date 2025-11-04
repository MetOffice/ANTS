# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
from unittest import mock

import ants.tests
from ants.fileformats.ancil import _fetch_grid_staggering_from_file


class TestOptionalMule(ants.tests.TestCase):
    """Tests for behaviour around mule being an optional dependency."""

    def test_error_without_mule(self):
        """No mule implies getting grid staggering results in an error."""
        expected_error = (
            "Mule cannot be imported, but an attempt has been "
            "made to use mule functionality through loading"
            "an F03 ancillary file."
        )
        with self.assertRaisesRegex(ValueError, expected_error):
            _ = _fetch_grid_staggering_from_file(None, False)

    @ants.tests.skip_mule
    def test_get_staggering_from_flh_with_mule(self):
        """Mule implies using the grid staggering from the fixed length header."""
        expected = {"foo": 6}
        with mock.patch(
            "ants.fileformats.ancil.mule.AncilFile.from_file",
            return_value=_FakeAncilFile,
        ):
            actual = _fetch_grid_staggering_from_file(("foo",), True)

        self.assertEqual(actual, expected)


class _FakeFixedLengthHeader:
    grid_staggering = 6


class _FakeAncilFile:
    fixed_length_header = _FakeFixedLengthHeader()

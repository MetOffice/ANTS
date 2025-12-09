# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
from ants.fileformats.ancil import _get_Field3


class TestOptionalMule(ants.tests.TestCase):
    """Tests for behaviour around mule being an optional dependency."""

    def test_error_instantiating_Field3_without_mule(self):
        """No mule implies using the _Field3 version that results in an error."""
        expected_error = (
            "Mule cannot be imported, but an attempt has been "
            "made to use mule functionality through the "
            "_Field3 class"
        )
        actual = _get_Field3(None)

        with self.assertRaisesRegex(ValueError, expected_error):
            actual("foo", "bar", "baz")

    @ants.tests.skip_mule
    def test_instantiating_Field3_with_mule(self):
        """Mule implies using the _Field3 that inherits from mule."""
        assert issubclass(
            ants.fileformats.ancil._Field3, ants.fileformats.ancil.mule.Field3
        )

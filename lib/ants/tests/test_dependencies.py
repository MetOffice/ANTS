# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""Tests for optional dependency installs.

If you are using an installation of ANTS without one or more of these optional
dependencies, the test suite should be configured to exclude the relevant tests.

For example, to run the tests without an install of mule and um_spiral_search,
use:

  pytest --deselect=lib/ants/tests/test_dependencies.py::test_mule --deselect=lib/ants/tests/test_dependencies.py::test_um_spiral_search

See https://docs.pytest.org/en/stable/example/pythoncollection.html#deselect-tests-during-test-collection

All tests that make use of the optional dependencies should be configured to be
skipped if the import fails via the appropriate decorator @ants.tests.skip_<dependency>,
e.g. @ants.tests.skip_mule.
"""  # noqa: E501
import ants  # noqa: F401


def test_mule():
    """Test that mule can be imported within ants."""
    import mule  # noqa: F401


def test_um_spiral_search():
    """Test that the UM spiral search can be imported within ants."""
    from um_spiral_search.um_spiral_search import spiral_search  # noqa: F401


def test_gdal():
    """Test that GDAL can be imported within ants."""
    from osgeo import gdal, osr  # noqa: F401


def test_esmpy():
    """Test that ESMPy can be imported within ants."""
    import esmpy  # noqa: F401


def test_f90nml():
    """Test that f90nml can be imported within ants."""
    import f90nml  # noqa: F401


def test_stratify():
    """Test that stratify can be imported within ants."""
    import stratify  # noqa: F401

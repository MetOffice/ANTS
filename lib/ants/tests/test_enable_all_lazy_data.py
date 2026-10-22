# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
# Some of the contents of this file have been written using Met Office
# Github Copilot Enterprise.
import ants.tests
import pytest
from iris.fileformats.netcdf import loader


def _min_bytes():
    return ants.utils.cube.iris.fileformats.netcdf.loader._LAZYVAR_MIN_BYTES


def test_all_data_lazy_during_function():
    @ants.tests.enable_all_lazy_data
    def function():
        return _min_bytes()

    assert function() == 0
    assert loader._LAZYVAR_MIN_BYTES == 5000


def test_default_restored_when_function_raises():
    @ants.tests.enable_all_lazy_data
    def function():
        raise ValueError("test failure")

    with pytest.raises(ValueError, match="test failure"):
        function()
    assert loader._LAZYVAR_MIN_BYTES == 5000

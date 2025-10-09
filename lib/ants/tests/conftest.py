# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.


import pytest


# Filters warnings
# Ignores download warnings from cartopy
# Other filtered warnings can be found in the pyproject.toml file
def pytest_runtestloop(session):
    session.add_marker(
        pytest.mark.filterwarnings("ignore:Downloading:cartopy.io.DownloadWarning")
    )

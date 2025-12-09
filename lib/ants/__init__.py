# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
from . import analysis, config, coord_systems, exceptions, utils
from ._constraints import ExtractConstraint
from .command_parse import AntsArgParser
from .fileformats import load, load_cube, load_cubes, load_grid, load_raw

# Restrict imports when 'from ants import *' and document functions.
__all__ = [
    "analysis",
    "config",
    "coord_systems",
    "exceptions",
    "utils",
    "load_grid",
    "load_cube",
    "load",
    "load_cubes",
    "load_raw",
    "AntsArgParser",
    "ExtractConstraint",
]


import warnings
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ANTS")
except PackageNotFoundError as exc:
    warnings.warn(
        f"{exc}. Unknown ANTS version. "
        "Consider installing ANTS into your environment. See the installation "
        "instructions in the documentation for more details.",
        stacklevel=0,
    )

    __version__ = "unknown"
config._ensure_ants_cartopy_variable_not_set()

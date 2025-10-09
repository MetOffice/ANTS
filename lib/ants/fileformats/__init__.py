# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
The `ants` package provides access to the fileformats commonly used in
ancillary generation. These include those supported by iris and additional
formats such as grid namelists and raster files.
"""
import warnings

import ants
import ants.io.load


def load_landsea_mask(filename, land_threshold=None):
    """
    .. deprecated:: 2.1
        Use :func:`ants.io.load.load_landsea_mask` instead.
    """
    warnings.warn(
        "ants.fileformats.load_landsea_mask has been deprecated. Please use "
        "ants.io.load.load_landsea_mask instead",
        FutureWarning,
    )
    return ants.io.load.load_landsea_mask(filename, land_threshold)


def load_grid(filenames, *args, **kwargs):
    """
    .. deprecated:: 2.1
        Use :func:`ants.io.load.load_grid` instead.
    """
    warnings.warn(
        "ants.load_grid has been deprecated. Please use "
        "ants.io.load.load_grid instead.",
        FutureWarning,
    )
    return ants.io.load.load_grid(filenames, *args, **kwargs)


def load(*args, **kwargs):
    """
    .. deprecated:: 2.1
        Use :func:`ants.io.load.load` instead.
    """
    warnings.warn(
        "ants.load has been deprecated. Please use ants.io.load.load instead.",
        FutureWarning,
    )
    return ants.io.load.load(*args, **kwargs)


def load_cube(*args, **kwargs):
    """
    .. deprecated:: 2.1
        Use :func:`ants.io.load.load_cube` instead.
    """
    warnings.warn(
        "ants.load_cube has been deprecated. Please use ants.io.load.load_cube "
        "instead.",
        FutureWarning,
    )
    return ants.io.load.load_cube(*args, **kwargs)


def load_cubes(*args, **kwargs):
    """
    .. deprecated:: 2.1
        Use :func:`ants.io.load.load_cubes` instead.
    """
    warnings.warn(
        "ants.load_cubes has been deprecated. Please use ants.io.load.load_cubes "
        "instead.",
        FutureWarning,
    )
    return ants.io.load.load_cubes(*args, **kwargs)


def load_raw(*args, **kwargs):
    """
    .. deprecated:: 2.1
        Use :func:`ants.io.load.load_raw` instead.
    """
    warnings.warn(
        "ants.load_raw has been deprecated. Please use ants.io.load.load_raw "
        "instead.",
        FutureWarning,
    )
    return ants.io.load.load_raw

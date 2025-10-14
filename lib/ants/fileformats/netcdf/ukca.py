# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import warnings

import ants
import dask
import numpy as np

LOCAL_ATTS = [
    "tracer_name",
    "vertical_scaling",
    "lowest_level",
    "highest_level",
    "hourly_scaling",
]
"""list: Local attributes for UKCA netCDF saving.

Atrributes to be saved locally per variable rather than globally.
This is used by :func:`ants.io.save.ukca_netcdf` to override
the default iris behaviour."""


def _update_conventions(cubes):
    """
    Update old UKCA conventions used by the cubes.

    This is only needed where we are regridding older master files which use
    the previous conventions. The convention changes are:
        1. Replace emission_type with update_type
        2. Encode integers as netcdf ints (32-bit) instead of strings

    """
    for cube in cubes:
        # Replace emission type with update type attribute.
        if "emission_type" in cube.attributes:
            if "update_type" not in cube.attributes:
                cube.attributes["update_type"] = cube.attributes["emission_type"]
            del cube.attributes["emission_type"]

        # convert all UKCA numeric attributes to 32-bit integers.
        int_attrib = [
            "update_type",
            "update_freq_in_hours",
            "lowest_level",
            "highest_level",
        ]
        for attrib in int_attrib:
            if attrib in cube.attributes:
                cube_attrib = cube.attributes[attrib]
                cube.attributes[attrib] = np.int32(cube_attrib)


def _ukca_conventions(cubes):
    cubes = ants.utils.cube.as_cubelist(cubes)
    _update_conventions(cubes)
    for cube in cubes:
        if cube.dtype != np.int32:
            cube.data = cube.core_data().astype(np.float32, copy=False)
        # If the data hasn't been realised, check whether the array contained in the
        # dask.array is a np.ma.MaskedArray to avoid realising the data.
        if ants.utils._dask.is_lazy_data(cube.core_data()):
            if ants.utils._dask._is_masked_array(cube.core_data()):
                warnings.warn(
                    "Cube has masked points. Filling with zeros as per UKCA convention."
                )
                cube.data = dask.array.ma.filled(cube.core_data(), fill_value=0)
        # If the data is already realised, can directly check the data for a mask.
        else:
            if np.ma.is_masked(cube.data):
                warnings.warn(
                    "Cube has masked points. Filling with zeros as per UKCA convention."
                )
                cube.data = cube.data.filled(fill_value=0)

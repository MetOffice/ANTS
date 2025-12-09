# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import logging

import ants.utils
import numpy as np
from ants.config import CONFIG

_LOGGER = logging.getLogger(__name__)


def _coerce_netcdf_classic_dtypes(cubes):
    """
    Coerce cube data dtype to a netCDF classic compatible and CF compliant type.

    NetCDF classic types include:
        ['S1', 'i1', 'u1', 'i2', 'u2', 'i4', 'u4', 'i8', 'u8', 'f4', 'f8']
    We also ensure CF compliance by coercing unsigned types to signed types.

    Raises
    ------
    OverflowError
        If the array cannot be safely cast to the corresponding netCDF-classic
        type.

    .. warning::

        Coercing the data of the cube will load it into memory.

    """

    def _recast(array, target_type):
        if not np.can_cast(array.dtype, target_type):
            # Not generally cast safe so check whether we can coerce based on
            # the values actually present.
            maxval = array.max()
            minval = array.min()
            if (
                np.can_cast(maxval, target_type) is False
                or np.can_cast(minval, target_type) is False
            ):
                msg = (
                    "Cannot safely re-cast {} array to {} for writing to a "
                    "netCDF classic file"
                )
                raise OverflowError(msg.format(array.dtype, target_type))
        return array.astype(target_type)

    dconv = {
        "bool": "i1",  # byte
        "uint8": "i2",  # short
        "uint16": "i4",  # int
        "uint32": "i8",
        "uint64": "i8",
        "float16": "f4",
    }

    cubes = ants.utils.cube.as_cubelist(cubes)
    for cube in cubes:
        if cube.dtype.name in dconv:
            if (
                "valid_range" not in cube.attributes
                and "valid_min" not in cube.attributes
            ):
                if cube.dtype.kind == "b":
                    cube.attributes["valid_range"] = [0, 1]
                elif cube.dtype.kind == "u":
                    cube.attributes["valid_range"] = [0, np.iinfo(cube.dtype).max]

            target_type = dconv[cube.dtype.name]
            cube.data = _recast(cube.lazy_data(), target_type)

        for coord in cube.coords():
            if coord.dtype.name in dconv:
                target_type = dconv[coord.dtype.name]
                coord.points = _recast(coord.lazy_points(), target_type)
            if coord.has_bounds() and coord.bounds_dtype.name in dconv:
                target_type = dconv[coord.bounds_dtype.name]
                coord.bounds = _recast(coord.lazy_bounds(), target_type)


def _rechunk(cube):
    """
    Rechunks cube data in place such that innermost dimension is a single chunk.

    All other dimensions are automatically chunked.

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube`

    Returns
    -------
    : None
    Operates on cube in place.
    """
    innermost_dimension = len(cube.shape) - 1
    rechunking = {i: "auto" for i in range(len(cube.shape))}
    rechunking[innermost_dimension] = -1
    cube.data = cube.core_data().rechunk(rechunking)


def _iris_dask_chunking_workaround(cubes):
    # If the innermost dimension is chunked, the netCDF save performance is
    # unacceptably slow.  We work around this by rechunking the innermost
    # dimension such that the entire dimension is a single chunk.  See
    # https://github.com/SciTools/iris/issues/4448 for more details.
    # This behaviour can be disabled via configuration.
    cubes = ants.utils.cube.as_cubelist(cubes)
    for cube in cubes:
        # Default for CONFIG["ants_tuning"]["disable_rechunking"] is None, to
        # which we cannot apply the `.lower` string method.  So convert that
        # default to a string so we can be tolerant of users using "True",
        # "true", etc to disable rechunking:
        disable_rechunking_config = CONFIG["ants_tuning"]["disable_rechunking"]
        if disable_rechunking_config is None:
            disable_rechunking_config = "false"
        enable_rechunking = (
            disable_rechunking_config.lower() != "true" and cube.has_lazy_data()
        )
        _LOGGER.info(
            f"Rechunking is: {enable_rechunking} for cube {cube.name()}.  "
            f'Config setting was {CONFIG["ants_tuning"]["disable_rechunking"]}'
            ", which evaluated to an enable_rechunking of "
            f'{disable_rechunking_config.lower() != "true"}'
            f" and lazy data was {cube.has_lazy_data()}."
        )

        if enable_rechunking:
            # Can assume that core_data is a dask array here, since
            # enable_rechunking is false if the data is realised.
            _LOGGER.info(
                f"Before rechunking, cube {cube.name()} has chunks of "
                f"{cube.core_data().chunks}"
            )
            _rechunk(cube)
            _LOGGER.info(
                f"After rechunking, cube {cube.name()} has chunks of "
                f"{cube.core_data().chunks}"
            )

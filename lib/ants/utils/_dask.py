# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import logging

import dask
import iris

_LOGGER = logging.getLogger(__name__)


def is_lazy_data(data):
    """
    Return whether the argument is a 'lazy' data array.

    At present, this means a Dask array.
    For now, this utilises the private iris function for this.

    Parameters
    ----------
    data : array-like
        An array-like object to query its lazy status.

    Returns
    -------
    : bool
        Returning True for lazy and False not.

    Warning
    -------
    This is for ants core library usage ONLY!

    """
    return iris._lazy_data.is_lazy_data(data)


def as_lazy_data(data, chunks=None, asarray=False):
    """
    Convert the input array `data` to a dask array.

    This is a placeholder for requesting lazy versions of an array-like objects.
    For now, this utilises the private iris function for this.

    Parameters
    ----------
    data : array-like
        An array. This will be converted to a dask array.
    chunks : int or (int, int, ...) or ((int, ...), (int, ...), ...), optional
        Describes how the created dask array should be split up. Defaults to a
        value first defined in biggus (being `8 * 1024 * 1024 * 2`).
        For more information see
        http://dask.pydata.org/en/latest/array-creation.html#chunks.
    asarray : bool
        If True, then chunks will be converted to instances of `ndarray`.
        Set to False (default) to pass passed chunks through unchanged.

    Returns
    -------
    : :class:`dask.array.array`
        The input array converted to a dask array.

    Warning
    -------
    This is for ants core library usage ONLY!

    """
    return iris._lazy_data.as_lazy_data(data, chunks=chunks, asarray=asarray)


def _is_masked_array(dask_array):
    """
    Return whether the input array (from cube.core_data()) is masked.

    This uses dask.array.any to determine if any of the values
    returned by dask.array.ma.getmaskarray are masked (True).
    Unmasked values are False by default.

    This does not realise the data.

    Documentation:
    https://docs.dask.org/en/stable/generated/dask.array.ma.getmaskarray.html

    Parameters
    ----------
    dask_array : :class:`~dask.array.Array`
        A dask array to evaluate its mask.

    Returns
    -------
    : bool
        Returns True for a masked (True) value in return
        from dask.array.ma.getmaskarray. False if no values
        are masked.

    Warning
    -------
    This is for ants core library usage ONLY!

    """
    mask_array = dask.array.ma.getmaskarray(dask_array)

    return dask.array.any(mask_array)

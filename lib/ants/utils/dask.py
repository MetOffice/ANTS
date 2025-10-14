# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import dask.array as da


def deferred_data_update(data, overwrite_data, slices):
    """
    Assign new data to the specified slices of data lazily.

    With the benefits of dask, override 'data' with 'overwrite_data' at the
    specified slices without realising any data.

    Parameters
    ----------
    data : :term:`array_like`
        2D array like object which includes numpy arrays or dask arrays.
        This represents the arrays which the other is transplanted onto.
    new_data : :term:`array_like`
        2D array like object which includes numpy arrays or dask arrays.
        This represents the array which is transplanted into the other.
    slices : tuple(slice, slice)
        Slices object representing the 2D slicing of 'data' to transplant the
        'overwrite_data'.

    Returns
    -------
    : :class:`dask.array.Array`
        Lazy array representing the original array with the new data
        transplanted onto it.

    Note
    ----
    This function serves the purpose of replacing part of a dask array with
    some changes.

    """
    if data.ndim != 2:
        message = "Expected 2D source data, got {} instead".format(data.ndim)
        raise ValueError(message)
    if overwrite_data.ndim != 2:
        message = "Expected 2D target data, got {} instead".format(overwrite_data.ndim)
        raise ValueError(message)

    # convert to dask arrays or pass through if input is already a dask array
    try:
        data = da.from_array(data)
    except ValueError:
        data = data

    try:
        inserted_data = da.from_array(overwrite_data)
    except ValueError:
        inserted_data = overwrite_data

    # use slices to cut shape of new data into original
    sliced_data = data[slice(slices[0].stop, None), slices[1]]
    if 0 not in sliced_data.shape:
        inserted_data = da.concatenate([inserted_data, sliced_data], 0)

    sliced_data = data[slice(slices[0].start, None), slice(slices[1].stop, None)]
    if 0 not in sliced_data.shape:
        inserted_data = da.concatenate([inserted_data, sliced_data], 1)

    sliced_data = data[slice(slices[0].start, None), slice(None, slices[1].start)]
    if 0 not in sliced_data.shape:
        inserted_data = da.concatenate([sliced_data, inserted_data], 1)

    sliced_data = data[slice(None, slices[0].start), :]
    if 0 not in sliced_data.shape:
        inserted_data = da.concatenate([sliced_data, inserted_data], 0)
    return inserted_data

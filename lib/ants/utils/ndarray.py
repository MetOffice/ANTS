# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants
import iris
import numpy as np


def transposed_view(array, axes=None):
    """
    Return a transposed view of the provided array.

    A wrapper for numpy transpose which supports taking a transposed view of
    the mask where present (unlike with numpy transpose).

    Parameters
    ----------
    array : :class:`numpy.ndarray`
    axes : :obj:`list` of :obj:`int`, optional
        By default, reverse the dimensions, otherwise permute the axes
        according to the values given.

    Returns
    -------
    : (:class:`numpy.ndarray`, :class:`numpy.ndarray`)
        Data array and masked arrays with their axes permuted.  A view is
        returned whenever possible.

    Note
    ----
    This wrapper exists to overcome the limitations of numpy when dealing with
    masked arrays, in that a masked array view is not returned but a copy
    within numpy.  See https://github.com/numpy/numpy/issues/7483 for further
    details.

    """
    if np.ma.isMaskedArray(array):
        data = array.data.transpose(axes)
        mask = np.ma.getmask(array)
        if np.ma.is_masked(array):
            mask = np.ma.getmaskarray(array).transpose(axes)
        data = np.ma.array(data, mask=mask)
    else:
        data = array.transpose(axes)
    return data


def group_indices(array):
    """
    Group an array representing indices into an iterable of slice objects.

    Parameters
    ----------
    array : :class:`numpy.ndarray`
        Numpy array representing indices.

    Returns
    -------
    : iterable of slice objects

    >>> indices = np.array([0, 1, 2, 4, 5, 6, 8, 9])
    >>> group_indices(indices)
    [slice(0, 3, None), slice(4, 7, None), slice(8, 10, None)]

    """
    diff = np.diff(array)
    diff = np.hstack([np.where(diff != 1)[0], diff.size])
    ref = 0
    slices = []
    for dd in range(len(diff)):
        slices.append(slice(array[ref], array[diff[dd]] + 1))
        ref = diff[dd] + 1
    return slices


def isclose(x1, x2):
    """
    Return the truth value of (x1 == x2) element-wise with tolerance defined
    by ants.config.TOLERANCE.

    """
    return np.isclose(x1, x2, atol=ants.config.TOLERANCE)


def wrap_lons(points, base, period, endpoint=True):
    """
    Wrap longitudinal points into the closed interval of base to base + period.

    The interval includes base and base + period.  This differs from
    :func:`iris.analysis.cartography.wrap_lons` which wraps onto a longitude
    interval including the base but excluding base + period (in the iris
    version base + period are mapped to base).  See examples.

    Parameters
    ----------
    points : :class:`numpy.ndarray`
        Points to wrap.
    base : int or float
        Base of wrap range.
    period : int or float
        Period of wrap range.

    Returns
    -------
    : :class:`numpy.ndarray`
        Points array wrapped to the specified [base, base+period] range at
        64bit float.

    Examples
    --------

    This wrap_lons will not wrap points at base + period but will leave them as
    is:

    >>> import numpy as np
    >>> wrap_lons(np.linspace(-180, 180, 4), -180, 360)
    array([-180.,  -60.,   60.,  180.])

    This contrasts with iris' wrap_lons which will wrap points at base + period
    to base:

    >>> from iris.analysis.cartography import wrap_lons as iwrap_lons
    >>> iwrap_lons(np.linspace(-180, 180, 4), -180, 360)
    array([-180.,  -60.,   60., -180.])

    """
    res = iris.analysis.cartography.wrap_lons(points, base, period)
    if endpoint:
        mask = isclose(points, base + period)
        res[mask] = points[mask]
    if allclose(points, res):
        # Don't unnecessarily add precision differences where not necessary.
        # 64-bit precision ensures consistent behaviour.
        res = points.astype("float64")
    return res


def _numpy_arithmetic_handling(x1, x2):
    x1 = np.asarray(x1)
    x2 = np.asarray(x2)
    ttype = np.promote_types(x1.dtype, x2.dtype)
    use_tolerance = False
    if ttype == np.float64:
        use_tolerance = True
    return x1, x2, use_tolerance


def greater(x1, x2):
    """
    Return the truth value of (x1 > x2) element-wise with tolerance defined
    by ants.config.TOLERANCE.

    """
    x1, x2, use_tolerance = _numpy_arithmetic_handling(x1, x2)
    x3 = x2
    if use_tolerance:
        x3 = x2 - ants.config.TOLERANCE
    return np.greater(x1, x3)


def less(x1, x2):
    """
    Return the truth value of (x1 < x2) element-wise with tolerance defined
    by ants.config.TOLERANCE.

    """
    x1, x2, use_tolerance = _numpy_arithmetic_handling(x1, x2)
    x3 = x2
    if use_tolerance:
        x3 = x2 + ants.config.TOLERANCE
    return np.less(x1, x3)


def allclose(x1, x2, tolerance=None):
    """
    Returns True if two arrays are element-wise equal within
    ants.config.TOLERANCE.

    """
    if tolerance is None:
        tolerance = ants.config.TOLERANCE

    return np.allclose(x1, x2, tolerance)


def _tolerant_array(array1, array2):
    """
    Returns arrays rounded to the same number of decimal places.
    The number of decimal places is defined by ants.config.TOLERANCE.

    This function is to be used on those algorithms where we have no direct
    control over the tolerance, as such we truncate instead.

    """
    decimals = int(abs(np.floor(np.log10(np.abs(ants.config.TOLERANCE)))))
    dtype = np.promote_types(array1.dtype, array2.dtype)
    array1 = np.around(array1.astype(dtype, copy=False), decimals)
    array2 = np.around(array2.astype(dtype, copy=False), decimals)
    return array1, array2


def in1d(array1, array2):
    """
    Return boolean array that is True where an element of array1 is in array2.
    The comparison of elements is within a tolerance defined by
    ants.config.TOLERANCE.

    """
    array1, array2 = _tolerant_array(array1, array2)
    return np.in1d(array1, array2)


def merge_array(array1, array2):
    """
    Merge overlapping arrays.

    This strictly works by stitching compatible arrays together.  Compatible
    arrays are those considered an extension or a subset of one another.
    Arrays must also be monotonically increasing/decreasing and currently in
    the same direction as one another.

    Parameters
    ----------
    array1 : numpy.ndarray
        Input array.
    array2 : numpy.ndarray
        Input array.

    Returns
    -------
    : numpy.ndarray
        Merged array containing the values of both supplied arrays.

    >>> arr = np.array([4, 5, 6])
    >>> arr2 = np.array([1, 2, 3, 4, 5])
    >>> merge_array(arr, arr2)
    array([1, 2, 3, 4, 5, 6])

    """

    def _not_strictly_monotonic(array):
        arr_diff = np.diff(array1)
        return 0 in arr_diff or len(np.unique(arr_diff > 0)) > 1

    def _increasing(array):
        return array[-1] > array[0]

    if _not_strictly_monotonic(array1) or _not_strictly_monotonic(array2):
        raise ValueError(
            "Arrays must be strictly monotonically increasing or " "decreasing in value"
        )

    if _increasing(array1) != _increasing(array2):
        raise ValueError(
            "Currently, arrays must be of the same direction to "
            "be considered compatible"
        )

    # Truncate the precision of the arrays to cater for differing sources or
    # derivation of values.
    array1, array2 = _tolerant_array(array1, array2)
    diff = np.setdiff1d(array2, array1)
    if ((diff < array1.max()) * (diff > array1.min())).any():
        raise ValueError("Arrays are not compatible for merging")

    result = np.union1d(array1, array2)
    if not _increasing(array1):
        result = result[::-1]
    return result

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Many of the routines you will need to perform the processing of
source data into an ancillary field are found in :mod:`ants.analysis`.
You can also call iris routines to help your ancillary field
processing. Some ANTS functions are relatively minimal wrappers around
iris functions.  Where appropriate, call the ANTS functions as these
provide additional benefits such as updating meta-data on the cubes.

Some of the most common routines you will want to use are:

* Calculating the area weighted mean of a field
  using :func:`~ants.analysis.mean`
* Filling a field to ensure it has values on every
  land/ocean/both point using :func:`~ants.analysis.UMSpiralSearch`.
* Merging two datasets using :func:`~ants.analysis.merge`.

Note, ANTS merge is used in a different context to iris.  In ANTS it means
combining two data sources either

1. to build a larger coverage than the source data or
2. to embed a high quality local source within a dataset with greater
   coverage.

The meaning in iris is discussed in the `iris documentation
<https://scitools-iris.readthedocs.io/en/latest/userguide/merge_and_concat.html>`_.

"""
import warnings

import ants
import ants.regrid
import ants.utils
import iris
import iris.analysis.calculus
import numpy as np

from . import _merge
from ._merge import (
    FillABC,
    FillMissingPoints,
    KDTreeFill,
    MooreNeighbourhood,
    UMSpiralSearch,
    horizontal_grid_reorder,
)

# Ensures documentation is promoted from _cover_mapping to this module (as a
# consequence, also have to define remaining public methods):
__all__ = [
    "MooreNeighbourhood",
    "UMSpiralSearch",
    "calc_grad",
    "mean",
    "merge",
    "standard_deviation",
    "floodfill",
    "find_similar_region",
    "make_consistent_with_lsm",
    "horizontal_grid_reorder",
    "FillABC",
    "KDTreeFill",
    "FillMissingPoints",
    "find_small_feature_seed_points",
]


def calc_grad(source):
    """
    .. attention::
       The calc_grad routine has been removed from the core ants library at version 2.2.
       It has been moved to Apps/Orography/orography_utils.py in the contrib
       repository.
       Attempting to use this function will result in an ImportError.
    """
    raise ImportError(
        "The calc_grad routine has been removed from the core ants library. It has been"
        " moved to Apps/Orography/orography_utils.py in the contrib repository."
    )


def _update_metadata(source, cube, operation):
    """
    Set the cell_methods on cube for an area weighted 'operation' and
    inherit certain metadata from source.

    """
    if source.long_name is not None:
        cube.long_name = "{} {}".format(operation.replace("_", " "), source.long_name)
    if "grid_staggering" in source.attributes:
        cube.attributes["grid_staggering"] = source.attributes["grid_staggering"]
    cube.add_cell_method(
        iris.coords.CellMethod("area: {} (area-weighted)".format(operation))
    )


def mean(source, target):
    """
    Calculate the source mean :math:`\\bar{x}` from the area mean of the
    source :math:`(x_i)` over each target grid box.

    .. math::
       \\bar{x} = \\sum_i {x_i}{w_i}

    where :math:`w_i` is the area of the source grid box (given an index i)
    that overlaps the target grid box divided by the area of the target grid
    box.

    Parameters
    ----------
    source : :class:`~iris.cube.Cube`
             Source cube.
    target : :class:`~iris.cube.Cube`
             Target cube.

    Returns
    -------
    : :class:`~iris.cube.Cube`
             The area-weighted mean of the source over the target grid.

    """
    mean_cube = source.regrid(
        target, ants.regrid.GeneralRegridScheme(horizontal_scheme="TwoStage")
    )
    _update_metadata(source, mean_cube, "mean")
    return mean_cube


def standard_deviation(source, src_mean):
    """
    Calculate the standard deviation of the source within the target grid box.

    This is calculated as the square root of the variance.  The variance is
    defined here as the mean of the squares minus the square of the mean.

    .. math::
       \\sigma^2 = \\sum_i {x_i}^2{w_i} - \\bar{x}^2

    Parameters
    ----------
    source : :class:`~iris.cube.Cube`
             Source cube.
    src_mean : :class:`~iris.cube.Cube`
             Mean of the source field on the target grid.

    Returns
    -------
    : :class:`~iris.cube.Cube`
           The sub-grid standard deviation of the source over the target grid.

    Notes
    -----
    There is no correction for biases in the standard deviation (Bessel's
    correction).  This could be an issue when the target grid
    is much lower resolution than the source grid.

    """

    src_meta = source.metadata

    if "grid_staggering" in src_mean.attributes:
        src_meta.attributes["grid_staggering"] = src_mean.attributes["grid_staggering"]
    source **= 2
    src_mean **= 2
    awm = source.regrid(
        src_mean, ants.regrid.GeneralRegridScheme(horizontal_scheme="TwoStage")
    )
    awm -= src_mean
    # Account for precision issues resulting in negative values.
    awm.data = np.abs(awm.data)
    awm **= 1 / 2.0

    _update_metadata(src_meta, awm, "standard_deviation")

    # History attribute gets removed during processing - add it back from the original
    # source metadata.
    if "history" in src_meta.attributes and "history" not in awm.attributes:
        ants.utils.cube.update_history(
            awm, src_meta.attributes["history"], add_date=False
        )

    return awm


def merge(primary_cube, alternate_cube, validity_polygon=None):
    """
    Merges data from the alternative cube into the primary cube.

    The primary cube data is used as a base, then cells from the alternate
    cube which lay outside the provided polygon, override the values of the
    primary at those locations.  Containment is defined as any cell corner
    which lies within the polygon.  "Within" explicitly does not include
    those points which exactly lay on the polygon boundary.  Where multiple
    primary and alternate cubes are provided, then these are paired
    appropriately where possible.  Where these datasets are not defined on the
    same grid, the user should consider a regrid first to then utilise merge.

    Parameters
    ----------
    primary_cube : :class:`~iris.cube.Cube` or :class:`~iris.cube.CubeList`
        The primary dataset which has a highest priority i.e. overriding values
        in the alternate dataset.
    alternate_cube : :class:`~iris.cube.Cube` or :class:`~iris.cube.CubeList`
        The alternate data set which is to be merged, taking a lower priority
        to values contained within the primary dataset.
    validity_polygon : :class:`~collections.abc.Iterable` or \
        :class:`shapely.Polygon` instance, optional
        Polygon defining the region of valid data within the primary dataset.
        Data defined outside this region will not take preference of the
        alternate dataset.  The crs of the polygon is assumed to be the same as
        the primary dataset to which it describes.  If an iterable is provided,
        then each item should correspond to the x, y point definition.
        If not provided, the entire primary_cube dataset is considered valid
        (including masked value).  This means that the two datasets are
        stacked together with the primary_cube taking priority over
        alternate_cube in the case of an overlap. A runtime error will be
        raised if the primary_cube is wholly within the validity_polygon.

    Returns
    -------
    :  :class:`~iris.cube.CubeList`
        One or more :class:`~iris.cube.Cube` objects

    Raises
    ------
    RuntimeError
        If the primary cube is wholly within a provided ``validity_polygon``.

    """
    primary_cubes = ants.utils.cube.as_cubelist(primary_cube)
    alternate_cubes = ants.utils.cube.as_cubelist(alternate_cube)

    # Group (sort) cubes so they are ordered in a way suitable for merging.
    primary_cubes, alternate_cubes = ants.utils.cube.sort_cubes(
        primary_cubes, alternate_cubes
    )
    result = iris.cube.CubeList([])
    for src1, src2 in zip(primary_cubes, alternate_cubes):
        nsource = _merge.merge(src1, src2, validity_polygon)
        result.append(nsource)
    if isinstance(primary_cube, iris.cube.Cube):
        result = result[0]
    return result


def _floodfill_neighbour_identify(
    shape, coords, seed_point, extended_neighbourhood, wraparound
):
    (yy, xx) = seed_point
    if yy > 0:
        coords.add((yy - 1, xx))
    if yy < (shape[0] - 1):
        coords.add((yy + 1, xx))
    if xx > 0 or wraparound:
        coords.add((yy, (xx - 1) % shape[1]))
    if xx < (shape[1] - 1) or wraparound:
        coords.add((yy, (xx + 1) % shape[1]))

    if extended_neighbourhood:
        if yy > 0 and (xx > 0 or wraparound):
            coords.add((yy - 1, (xx - 1) % shape[1]))
        if yy > 0 and (xx < (shape[1] - 1) or wraparound):
            coords.add((yy - 1, (xx + 1) % shape[1]))
        if yy < (shape[0] - 1) and (xx > 0 or wraparound):
            coords.add((yy + 1, (xx - 1) % shape[1]))
        if yy < (shape[0] - 1) and (xx < (shape[1] - 1) or wraparound):
            coords.add((yy + 1, (xx + 1) % shape[1]))


def floodfill(
    array, seed_point, fill_value, extended_neighbourhood=False, wraparound=False
):
    """
    Floodfill via an iterative algorithm.

    Parameters
    ----------
    array : :class:`~numpy.ndarray`
        The array to apply the floodfill.
    seed_point : tuple
        The starting (y, x) index (the seed point).
    fill_value : int or float
        The value which results in the 'flooded area'.
    extended_neighbourhood : :obj:`bool`, optional
        In the extended neighbourhood case, also consider the diagonals in
        each locations neighbourhood:

        | Default neighbourhood:
        | [False, True, False]
        | [True,  True, True ]
        | [False, True, False]

        | Extended Neighbourhood:
        | [True, True, True]
        | [True, True, True]
        | [True, True, True]

    wraparound : :obj:`bool`, optional
        When True, support wraparound in 'x', otherwise stop at the boundary.

    """
    (y, x) = seed_point
    if array.ndim != 2:
        msg = "The provided array should be 2D but that provided is {}D"
        raise ValueError(msg.format(array.ndim))
    if array[y, x] == fill_value:
        raise ants.exceptions.FloodfillError(
            "The value at location {}x{} already has this fill " "value.".format(y, x)
        )
    value_at_seed = array[y, x]

    coords = set(((y, x),))
    while coords:
        yy, xx = coords.pop()
        if array[yy, xx] == value_at_seed:
            array[yy, xx] = fill_value
            _floodfill_neighbour_identify(
                array.shape, coords, (yy, xx), extended_neighbourhood, wraparound
            )


def find_small_feature_seed_points(
    array,
    min_feature_size,
    land_features=False,
    extended_neighbourhood=False,
    wraparound=False,
):
    """
    Return a set of indices for seed points for filling regions of less than a
    specified number of points in a provided land sea mask.

    .. deprecated:: 2.2
       Planned for removal due to no known use cases.  Please contact
       miao@metoffice.gov.uk if you do need this functionality.

    Parameters
    ----------
    array : :class:`~numpy.ndarray`
        The array to search.

    min_feature_size : int
        Find features with fewer grid boxes than this

    land_features : bool
        Set to True to identify land seed points, False (default) for sea seed points.

    extended_neighbourhood : :obj:`bool`, optional
        In the extended neighbourhood case, also consider the diagonals in
        each locations neighbourhood:

        | Default neighbourhood:
        | [False, True, False]
        | [True,  True, True ]
        | [False, True, False]

        | Extended Neighbourhood:
        | [True, True, True]
        | [True, True, True]
        | [True, True, True]

    wraparound : :obj:`bool`, optional
        When True, support wraparound in 'x', otherwise stop at the boundary.

    Returns
    -------
    : :class:`~numpy.ndarray`
        2D array containing the row and column indices of those locations
        identified as potential fill seed points for features smaller than the
        specified feature_size.
    """

    message = (
        "This function does not appear to be used, and hence has been "
        "deprecated.  Please contact miao@metoffice.gov.uk if you do "
        "require this function, and we can discuss options (potentially "
        "including keeping this function and removing the deprecation)."
    )
    warnings.warn(message, FutureWarning)

    # candidate indices to evaluate
    if land_features:
        candidate_inds = np.where(array == 1)
    else:
        candidate_inds = np.where(array == 0)

    # covert to list of pairs for convenience
    candidate_inds = list(zip(list(candidate_inds[0]), list(candidate_inds[1])))

    # list for holding set of seed point tuples to use
    seed_points = []

    # set fill value as outside data range
    fill_value = np.min(array) - 1
    while candidate_inds:
        seed_point = candidate_inds.pop()
        filled = array.copy()
        floodfill(filled, seed_point, fill_value, extended_neighbourhood, wraparound)

        filled_inds = np.where(filled == fill_value)
        filled_inds = list(zip(list(filled_inds[0]), list(filled_inds[1])))

        # if the number of points that has been filled is less than the min
        # feature size then record the seed point used
        if len(filled_inds) < min_feature_size:
            seed_points.append(seed_point)

        # remove points from the list so we don't reconsider them again
        filled_inds.remove(seed_point)
        for point in filled_inds:
            candidate_inds.remove(point)

    return seed_points


def find_similar_region(
    array, seed_point, extended_neighbourhood=False, wraparound=False
):
    """
    Return a set of indices where the connecting neighbours have the same value

    This function is functionaly equivelent :func:`floodfill`, except that
    here the fill locations are returned rather than filled.

    Parameters
    ----------
    array : :class:`~numpy.ndarray`
        The array to search.
    seed_point : tuple
        The starting (y, x) index (the seed point).
    extended_neighbourhood : :obj:`bool`, optional
        In the extended neighbourhood case, also consider the diagonals in
        each locations neighbourhood:

        | Default neighbourhood:
        | [False, True, False]
        | [True,  True, True ]
        | [False, True, False]

        | Extended Neighbourhood:
        | [True, True, True]
        | [True, True, True]
        | [True, True, True]

    wraparound : :obj:`bool`, optional
        When True, support wraparound in 'x', otherwise stop at the boundary.

    Returns
    -------
    : :class:`~numpy.ndarray`
        2D array containing the row and column indices of those locations
        identified as similar.

    """
    (y, x) = seed_point
    if array.ndim != 2:
        msg = "The provided array should be 2D but that provided is {}D"
        raise ValueError(msg.format(array.ndim))
    visited = np.zeros(array.shape, dtype="bool")
    src_value = array[y, x]

    indices = set(((y, x),))
    coords = set(((y, x),))
    while coords:
        yy, xx = coords.pop()
        if not visited[yy, xx] and array[yy, xx] == src_value:
            visited[yy, xx] = True
            indices.add((yy, xx))
            _floodfill_neighbour_identify(
                array.shape, coords, (yy, xx), extended_neighbourhood, wraparound
            )
    return tuple([[ind[i] for ind in list(indices)] for i in range(array.ndim)])


def make_consistent_with_lsm(sources, lsm, invert_mask, method="spiral"):
    """
    Make the provided source(s) consistent with the provided land sea mask.

    Replaces missing data values with valid data, where missing is defined as
    data that is either masked or NaN.  Missing land points are filled with
    nearest valid land values, and missing sea points are filled with nearest
    valid sea values.  Land and sea points are defined by the provided
    landsea mask.

    Additional coordinates on the source(s), such as time and pseudo levels are
    handled. However, if the dimensions are not already in the order of
    (<other dimensions>, y, x), they will be rearranged to this order.

    Parameters
    ----------
    sources : :class:`~collections.abc.Iterable` of :class:`~iris.cube.Cube` objects
        Source cubes.
    lsm : :class:`~iris.cube.Cube`
        Landsea mask field.
    invert_mask : bool
        Invert the mask (land field) or not (ocean field).  The landsea mask
        has True values to denote land.
    method : :obj:`str`, optional
        Select the search method to be used when filling missing points. The methods
        currently supported are "spiral" and "kdtree".

    Returns
    -------
    : None
        In-place operation.

    Raises
    ------
    NotImplementedError
        If an unsupported search method is specified.

    See Also
    --------
    :class:`ants.analysis.UMSpiralSearch` : for more details on how the
        nearest valid points are determined when the "spiral" method is used.
    :class:`ants.analysis.KDTreeFill` : for more details on how the
        nearest valid points are determined when the "kdtree" method is used.

    """
    # Check whether there are any values in the lsm that are masked or are not 0 or 1.
    # (This can occur where there is missing data in the source used to derive the
    # lsm.)
    if np.ma.is_masked(lsm.data):
        warnings.warn(
            "The land sea mask has values that are masked. These may cause unexpected "
            "results when calling ants.analysis.make_consistent_with_lsm."
        )
    if np.any(np.isin(lsm.data, [0, 1], invert=True)):
        warnings.warn(
            "The land sea mask has values that are not 0 or 1. These may cause "
            "unexpected results when calling ants.analysis.make_consistent_with_lsm."
        )
    if ants.utils.cube._is_ugrid(lsm):
        raise ValueError("ANTS doesn't support ugrid data. Please use UG-ANTS instead.")

    mask = lsm.copy(lsm.data.astype("bool", copy=False))
    ants.utils.cube.guess_horizontal_bounds(mask)
    if invert_mask:
        mask.data = np.logical_not(mask.data)
    sources = ants.utils.cube.as_cubelist(sources)
    match method.lower():
        case "spiral":
            DefaultFiller = UMSpiralSearch
        case "kdtree":
            DefaultFiller = KDTreeFill
        case _:
            raise RuntimeError(f"Unknown search method: {method}")
    for cube in sources:
        if ants.utils.cube._is_ugrid(cube):
            raise ValueError(
                "ANTS doesn't support ugrid data. Please use UG-ANTS instead."
            )
        else:
            Filler = DefaultFiller
            ants.utils.cube.guess_horizontal_bounds(cube)
        filler = Filler(cube, target_mask=mask)
        filler(cube)

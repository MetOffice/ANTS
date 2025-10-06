# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import warnings

import ants
import numpy as np


def fetch_lct_slices(source, um_tile_ids):
    """
    Fetch the slices corresponding to the specified JULE tile ID.

    Given an iris cube, derive a set of slices for this cube corresponding to
    this JULE tile ID.  That is, indexing the pseudo_level mapped dimension.

    Parameters
    ----------
    source : :class:`~iris.cube.Cube`
        Source cube which has land cover types as defined by a pseudo level
        coordinate.
    um_tile_ids : int | list[int]
        JULES tile IDs.  This corresponds to the pseudo_level value(s) desired.

    Returns
    -------
    tuple
        A tuple containing slice objects.

    Example
    -------

    >>> c3_grass = 3
    >>> c3_grass_slices = fetch_veg_slice(cube, c3_grass)
    >>> c3_grass.data[c3_grass] = ...

    """
    um_tile_ids_iter = um_tile_ids
    if not hasattr(um_tile_ids, "__iter__"):
        um_tile_ids_iter = [um_tile_ids]
    pseudo_level = source.coord("pseudo_level")
    pseudo_level_points = pseudo_level.points.tolist()
    index = [pseudo_level_points.index(um_tile_id) for um_tile_id in um_tile_ids_iter]

    # iris requires tuples...
    index = tuple(index)
    if not hasattr(um_tile_ids, "__iter__"):
        # If we supply a single index we don't want to return an iterable slice
        # as that means that the object being sliced will have an extra
        # dimension which the user would not expect.
        index = index[0]

    slices = [slice(None)] * source.ndim
    ps_dim = source.coord_dims(pseudo_level)
    if len(ps_dim) != 1:
        msg = (
            "Expecting 1D pseudo level coordinate describing JULES "
            "classes, got {}D coord."
        ).format(len(ps_dim))
        raise RuntimeError(msg)
    slices[source.coord_dims(pseudo_level)[0]] = index
    return tuple(slices)


def normalise_fractions(source):
    """
    Normalisation of fractions, ensuring the sum of the fractions is 1.

    Normalisation effectively works by filling missing data by dividing equally
    amongst all types where data > 0 such that the ratios between fractions
    remain the same.  Where there are no class fractions at a given point, it
    will remain 0.  Fractions outside the range [0, 1] are considered anomalous
    and pulled into that range before normalisation occurs.

    Parameters
    ----------
    source : :class:`iris.cube.Cube`
        Source land cover type fraction, with pseudo-level coordinate
        representing the classes.

    Warning
    -------
    Mask is not altered by this function.

    """
    # Ensure fractions are within a suitable range
    # Ignore numpy invalid value warnings due to presence of nans which we
    # expect after a regrid.
    with np.errstate(invalid="ignore"):
        source.data[source.data < 0] = 0
        source.data[source.data > 1] = 1

    pseudo_level = source.coord("pseudo_level")
    if pseudo_level.ndim != 1:
        msg = "Expecting a 1D pseudo_level coordinate not {}D."
        raise RuntimeError(msg.format(pseudo_level.ndim))

    pdim = source.coord_dims(pseudo_level)[0]

    transpose_indx = [pdim] + [x for x in range(source.ndim) if x != pdim]
    data = np.asarray(ants.utils.ndarray.transposed_view(source.data, transpose_indx))

    with np.errstate(invalid="ignore"):
        non_zero = (data > 0).sum(axis=0) > 0
    if not non_zero.all():
        warnings.warn(
            "Locations present with no classification fraction, "
            "ignoring such locations."
        )
    non_zero_data = data[..., non_zero]
    source_sum = non_zero_data.sum(axis=0)
    adjustments = 1.0 - source_sum
    data[..., non_zero] = (
        adjustments / (1 - adjustments) * non_zero_data
    ) + non_zero_data


class CoverMapper(object):
    """
    .. versionchanged:: 2.2
       The CoverMapper class has been removed from core ANTS.
       The code has been relocated to the LCT app in Contrib.
    """

    def __init__(self, *args, **kwargs):
        raise ImportError(
            "ants.analysis.cover_mapping.CoverMapper has been removed from core ANTS "
            "in version 2.2. The code has been relocated to the LCT app in Contrib."
        )


class SCTTransformer(object):
    """
    .. versionchanged:: 2.2
       The SCTTransformer class has been removed from core ANTS.
       The code has been relocated to the LCT app in Contrib.
    """

    def __init__(self, *args, **kwargs):
        raise ImportError(
            "ants.analysis.cover_mapping.SCTTransformer has been removed from core "
            "ANTS in version 2.2. "
            "The code has been relocated to the LCT app in Contrib."
        )

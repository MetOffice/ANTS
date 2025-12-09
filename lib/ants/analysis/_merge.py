# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Various tools are available at our disposal for performing analysis on data.
The metadata is also updated to reflect the analysis made.

"""
import abc
import logging
import warnings

import ants
import ants.regrid
import ants.stats
import ants.utils
import iris
import numpy as np
import numpy.lib.stride_tricks as stride
import shapely
from pykdtree.kdtree import KDTree
from shapely.geometry import Polygon
from shapely.vectorized import contains

try:
    from um_spiral_search.um_spiral_search import spiral_search as spiral
except Exception as _SPIRAL_IMPORT_ERROR:
    spiral = None
    _SPIRAL_IMPORT_ERROR_MESSAGE = (
        f'{str(_SPIRAL_IMPORT_ERROR)}\nUnable to import "spiral", proceeding without '
        "the capabilities it provides.  See install.rst"
    )
    warnings.warn(_SPIRAL_IMPORT_ERROR_MESSAGE)


_LOGGER = logging.getLogger(__name__)


def _merge_compatible(cube1, cube2):
    if cube1.attributes.get("STASH", None) != cube2.attributes.get("STASH", None):
        msg = "STASH attributes are not equal, {} != {}"
        raise ValueError(
            msg.format(
                cube1.attributes.get("STASH", None), cube2.attributes.get("STASH", None)
            )
        )
    if cube1.units != cube2.units:
        msg = 'Cube "units" do not match, {} != {}'
        raise ValueError(msg.format(cube1.units, cube2.units))

    std_name_1 = getattr(cube1, "standard_name", None)
    std_name_2 = getattr(cube2, "standard_name", None)
    if std_name_1 != std_name_2:
        msg = "Cube standard_name do not match, {} != {}"
        raise ValueError(msg.format(std_name_1, std_name_2))


def horizontal_grid_reorder(cube):
    """
    Return a transposed view of the cube's data, so that the outermost dimension
    corresponds to 'y' while the next corresponds to 'x'.

    Parameters
    ----------
    cube : :class:`~iris.cube.Cube`
        Cube to transpose.

    Returns
    -------
    tuple(:class:`~numpy.ndarray`, :class:`~numpy.ndarray`)
        A tuple of arrays, both transposed as [y, x, ...]:

        - The first array corresponds to the cube's data.
        - The second array corresponds to the cube's mask.


    .. note::

        Both array view and mask views are returned. This minimises
        memory use by ensuring the mask is a view.  We can not
        take the mask from the masked array view as this mask is not
        a view.

    .. warning::

        Care should be taken when reordering when there are more than three
        dimensions as the order of the dimension which are not mapped to
        the horizontal grid might not agree but be of the same length.

    """
    if cube.ndim > 3:
        raise RuntimeError(
            "Grid re-ordering has yet to support cubes of "
            "dimensionality greater then 3"
        )
    sx, sy = ants.utils.cube.horizontal_grid(cube)
    dsx, dsy = cube.coord_dims(sx)[0], cube.coord_dims(sy)[0]
    transpose = [dsy, dsx]
    transpose += [i for i in range(cube.ndim) if i not in transpose]

    if not np.ma.isMaskedArray(cube.data):
        cube.data = np.ma.array(cube.data)
    cube.data.mask = np.ma.getmaskarray(cube.data)

    data = cube.data.data.transpose(transpose)
    mask = cube.data.mask.transpose(transpose)
    return data, mask


def _add_halo(source, fill_value=None, halo_width=[1, 1]):
    """Return numpy array by adding halo points to source data."""
    if fill_value is None:
        fill_value = getattr(
            source.data, "fill_value", np.ma.array(0, source.data.dtype).fill_value
        )
    data = np.empty(
        np.array(source.shape) + np.array(halo_width) * 2, dtype=source.dtype
    )
    data.fill(fill_value)
    # Fill interior with original array.
    data[halo_width[0] : -halo_width[0], halo_width[1] : -halo_width[1]] = source.data
    if np.ma.count_masked(source.data) != 0:
        data[halo_width[0] : -halo_width[0], halo_width[1] : -halo_width[1]][
            source.data.mask
        ] = fill_value

    # Handle wraparound if supported
    x_coord, y_coord = ants.utils.cube.horizontal_grid(source)
    circular = getattr(x_coord, "circular", False)
    if circular:
        xdim, ydim = source.coord_dims(x_coord), source.coord_dims(y_coord)
        if len(xdim) != 1 or len(ydim) != 1:
            warnings.warn(
                "Currently wraparound only supported for regular "
                "grids.  Continuing without considering "
                "wraparound."
            )
        else:
            xdim, ydim = xdim[0], ydim[0]
            # Set the longitude very left and very right-hand-side edges
            if xdim == 1:
                bounds = source.data[:, -halo_width[1] :]
                unmasked = ~np.ma.getmaskarray(bounds)
                data[halo_width[0] : -halo_width[0], 0 : halo_width[1]][unmasked] = (
                    bounds[unmasked]
                )
                bounds = source.data[:, 0 : halo_width[1]]
                unmasked = ~np.ma.getmaskarray(bounds)
                data[halo_width[0] : -halo_width[0], -halo_width[1] :][unmasked] = (
                    bounds[unmasked]
                )
            else:
                bounds = source.data[-halo_width[0] :, :]
                unmasked = ~np.ma.getmaskarray(bounds)
                data[0 : halo_width[0], halo_width[1] : -halo_width[1]][unmasked] = (
                    bounds[unmasked]
                )
                bounds = source.data[0 : halo_width[0], :]
                unmasked = ~np.ma.getmaskarray(bounds)
                data[-halo_width[0] :, halo_width[1] : -halo_width[1]][unmasked] = (
                    bounds[unmasked]
                )
    return data


def _neighbourhoods(data, window_shape=(3, 3), window_step=(1, 1)):
    """
    Generate neighbourhood views of the data.

    This function is a convenience wrapper around
    :func:`numpy.lib.stride_tricks` which returns an ndarray representing
    the neighbourhood views of the data.

    By default, the default window size (ergo neighbourhood) is 3x3.  That is,
    the neighbourhood is the 8 points around any one point (though in this case
    the neighbourhood includes the point itself).  The first and last rows and
    columns of the input data do not have neighbourhoods as they are the
    'edges'.

    Parameters
    ----------
    data : 2darray
        Grid on which to stride.
    window_shape : tuple
        Shape of each points neighbourhood.
    window_step : tuple
        Window element step, corresponding to window center.

    Returns
    -------
    ndarray
        Neighbourhood views of the grid.

    The simplest case is of data with shape (3, 3). Only the
    central point has a complete neighbourhood, made up of all the points.

    This means only one point (the central point) has a neighbourhood - and
    this neighbourhood is the entire input data.

    >>> import numpy as np
    >>> a = np.arange(3 * 3).reshape((3, 3))
    >>> b = _neighbourhoods(a)
    >>> b.shape
    (1, 1, 3, 3)

    >>> b[0, 0, :, :]
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])

    When there are more points the index [i, j, :, :] of the returned
    neighbourhoods is the neighbourhood of the i+1, j+1 location in the input
    data, and has values data[i:i+2, j:j+2].

    >>> c = np.arange(4 * 5).reshape((4, 5))
    >>> d = _neighbourhoods(c)
    >>> d.shape
    (2, 3, 3, 3)

    >>> np.all(d[0, 0, :, :] == c[0:3, 0:3])
    True

    >>> np.all(d[1, 2, :, :] == c[1:4, 2:5])
    True

    """
    if data.ndim != len(window_shape):
        msg = (
            "Window shape specified {} does not match the dimensionality "
            "of the specified data {}".format(window_shape, data.ndim)
        )
        raise ValueError(msg)
    if len(window_step) != len(window_shape):
        msg = (
            "Window shape length ({}) and the window step size length ({}) "
            "does not match".format(len(window_shape), len(window_step))
        )
    dstrides = np.asarray(data.strides)
    strides = np.hstack([dstrides * window_step, dstrides])
    window = np.hstack(
        [
            (np.asarray(data.shape) - (np.array(window_shape) - 1)) // window_step,
            window_shape,
        ]
    )
    views = stride.as_strided(data, window, strides)
    return views


class MooreNeighbourhood(object):
    """Operations on the Moore Neighbourhood of points in a cube."""

    def __init__(self, acube, window_mask=None):
        """
        Each grid box in a cube has a Moore Neighbourhood: the 8 grid boxes
        around it on the grid.  An instance of this class can be used to
        calculate some of the properties of the neighbourhood of the grid
        boxes of a single cube.

        Parameters
        ----------
        acube : :class:`~iris.cube.Cube`
                Calculations of the Moore neighbourhood will be done
                on this cube.
        window_mask : bool :class:`~numpy.ndarray` object, optional
            Mask array which defines the Moore neighbourhood of each in the
            window of each grid point.  The provided mask must have an odd
            length for each dimension.  If not provided, this is assumed to be
            a 3x3 with all surrounding points considered.

        Raises
        ------
        ValueError
            If the provided mask does not have an odd length for each
            dimension.

        ValueError
            If the cube is not 2 dimensional.  This is could be relaxed
            with a more advanced implementation.

        ValueError
            If the axes of the cube are not contiguous, and so do not look
            like they are neighbours.

        References
        ----------
        https://en.wikipedia.org/wiki/Moore_neighborhood

        """
        self._exception_on_bad_cube_arg(acube)
        self._fill_value = getattr(
            acube.data, "fill_value", np.ma.array(0, acube.data.dtype).fill_value
        )
        if window_mask is not None:
            self._mask = window_mask.astype(dtype="bool", copy=False)
        else:
            self._mask = np.array(
                [[True, True, True], [True, False, True], [True, True, True]]
            )
        odd_shape = np.array(self._mask.shape) % 2
        if not odd_shape.all():
            msg = (
                "Expecting the provided mask to have an odd length for "
                "each dimension."
            )
            raise ValueError(msg)
        halo_width = (np.array(self._mask.shape) - 1) // 2
        self._data = _add_halo(
            acube, fill_value=self._fill_value, halo_width=halo_width
        )
        self._neighbours = self._mask.sum()
        self._views = _neighbourhoods(self._data, self._mask.shape)

    def _exception_on_bad_cube_arg(self, acube):
        if acube.ndim != 2:
            raise ValueError("current implementation supports only 2d cubes")
        sx, sy = ants.utils.cube.horizontal_grid(acube)
        if not (sx.is_contiguous() and sy.is_contiguous()):
            raise ValueError("axes must be contiguous")

    def all_equal_value(self, value):
        """
        Returns True for grid boxes where all neighbouring grid
        boxes have the specified value.

        Parameters
        ----------
        value : ~numbers.Number
            Choosing a type that can be compared to the cube data type, the
            value is compared to neighbourhood values.

        Returns
        -------
        : 2d :obj:`bool` type :class:`~numpy.ndarray`
           True where the neighbours are all equal to value.

        Notes
        -----
        The comparison is exact; a tolerance isn't currently supported.

        """

        missing = self._count_missing()
        return ((self._views[..., self._mask] == value).sum(2)) == (
            self._neighbours - missing
        )

    def _count_missing(self):
        # Boundary points are included in this
        missing = 0
        if self._fill_value is not None:
            missing = (self._views[..., self._mask] == self._fill_value).sum(2)
        return missing

    def all_missing(self):
        """
        Returns True for grid boxes where the neighbourhood
        contains only the missing value.

        """

        return self._count_missing() == self._neighbours

    def any_non_missing(self):
        """
        Returns True for grid boxes where the Moore neighbourhood
        contains any valid data.

        """

        return self._count_missing() < self._neighbours

    def any_equal_value(self, value):
        """
        Return True for grid boxes where any of the Moore neighbours
        have the specified value.

        Parameters
        ----------
        value : :class:`~numbers.Number` or :class:`~numpy.ndarray`
              The value(s) to compare neighbourhood to.  If an
              :class:`~numpy.ndarray`, this should match the mask shape.

        Returns
        -------
        : 2d :obj:`bool` type :class:`~numpy.ndarray`
           True where the neighbours are all equal to value.

        Notes
        -----
        The comparison is exact; a tolerance isn't currently supported.

        """
        if hasattr(value, "shape"):
            value = value.astype(self._views.dtype, copy=False)
            res = self._views[..., self._mask] == value[self._mask]
            res = res.sum(2) > 0
        else:
            res = (self._views[..., self._mask] == value).sum(2) > 0
        return res

    def neighbourhood_mean(self):
        """
        Return the mean of the values in the Moore neighbourhood.

        If the neighbourhood contains missing data then the mean is
        taken over only the neighbours that are not missing.

        """

        value = self._fill_value
        nn_coasts = (self._views[..., self._mask] != value).sum(2)

        # Temporarily remove 'value' for the sake of determining the sum
        mod_mask = self._data == value
        self._data[mod_mask] = 0
        # Capture runtime warnings (where there are no neighbours)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            coasts_masks = self._views[..., self._mask].sum(2) / nn_coasts.astype(
                "float", copy=False
            )
        self._data[mod_mask] = value
        return coasts_masks


def _unified_grid(cube, cube2):
    """Return a cube which has horizontal grid coverage of both cubes."""
    sx, sy = ants.utils.cube.horizontal_grid(cube)
    tx, ty = ants.utils.cube.horizontal_grid(cube2)

    if sx == tx and sy == ty:
        ex = sx.copy()
        ey = sy.copy()
    else:
        # Create a unifying grid which covers the area of both sources
        try:
            ex = sx.copy(ants.utils.ndarray.merge_array(sx.points, tx.points))
            ey = sy.copy(ants.utils.ndarray.merge_array(sy.points, ty.points))
        except ValueError as err:
            msg = (
                "Unable to define a unified grid covering the domain of "
                "both supplied cubes: "
            )
            err.args = tuple([msg + err.args[0]])
            raise err
    dsx, dsy = cube.coord_dims(sx)[0], cube.coord_dims(sy)[0]
    shape = list(cube.shape)
    shape[dsx] = ex.points.size
    shape[dsy] = ey.points.size

    # Initialise unified grid as masked.  This means that in the case where
    # both sources have points which do not overlapped, these will remain
    # masked.
    data = np.ma.empty(shape, dtype=cube.dtype)
    try:
        data.fill(np.nan)
    except ValueError:
        # Not all data types accept nan as a fill value. Fill with 0 instead.
        data.fill(0)

    data.mask = True
    merged_cube = iris.cube.Cube(data)

    merged_cube.add_dim_coord(ex, dsx)
    merged_cube.add_dim_coord(ey, dsy)
    ants.utils.cube.guess_horizontal_bounds(merged_cube)

    # Add any coordinates which are not mapped to the horizontal dimensions
    dimensions = list(range(cube.ndim))
    dimensions.pop(dimensions.index(dsx))
    dimensions.pop(dimensions.index(dsy))
    for dimension in dimensions:
        for coord in cube.coords(dimensions=(dimension)):
            try:
                merged_cube.add_dim_coord(coord, dimension)
            except ValueError:
                merged_cube.add_aux_coord(coord, dimension)

    # copy the rest of the meta data across to the new cube
    merged_cube.cell_methods = cube.cell_methods
    merged_cube.metadata = cube.metadata

    return merged_cube


def merge(primary_cube, alternate_cube, validity_polygon=None):
    """
    Merges data from the alternative cube into the primary cube.

    The primary cube data is used as a base, then cells from the alternate
    cube which lay outside the provided polygon, override the values of the
    primary at those locations.  Containment is defined as any cell corner
    which lies within the polygon.  "Within" explicitly does not include
    those points which exactly lay on the polygon boundary.
    Points with numpy.NAN values in the source are also overridden by the
    corresponding alternate cube data values.  The presence of a numpy.NAN
    in the primary cube dataset, overrides that elements validity defined in
    the cases of a specified validity polygon.

    Parameters
    ----------
    primary_cube : `~iris.cube.Cube`
        The primary dataset which has a highest priority i.e. overriding values
        in the alternate dataset.
    alternate_cube : `~iris.cube.Cube`
        The alternate data set which is to be merged, taking a lower priority
        to values contained within the primary dataset.
    validity_polygon : iterable or :class:`shapely.Polygon` instance, optional
        Polygon defining the region of valid data within the primary dataset.
        Data defined outside this region will not take preference of the
        alternate dataset.  The crs of the polygon is assumed to be the same as
        the primary dataset to which it describes.  If an iterable is provided,
        then each item should correspond to the x, y point definition.
        If not provided, the entire primary_cube dataset is considered valid
        (including masked value).  This means that the two datasets are
        stacked together with the primary_cube taking priority over
        alternate_cube in the case of an overlap.
        If a validity polygon is provided and the entire primary_cube dataset
        is within the polygon then a Runtime error will be raised.

    Raises
    ------
    RuntimeError
        If the primary cube is wholly within a provided validity_polygon.

    .. note::

        Limited to datasets on the same grid.

    .. warning::

        Currently assumes that mask and numpy.NAN values are consistent across
        all horizontal slices i.e. a form of broadcasting is utilised.  The
        first horizontal grid slice is used as reference.

    """

    def _coord_intersect(coord, coord2):
        """Return a slice object where coord2 intersects coord"""
        x_cont = ants.utils.ndarray.in1d(coord.points, coord2.points)
        x_inside = np.where(np.equal(x_cont, True))[0]
        x_ind = slice(x_inside[0], x_inside[-1] + 1)
        return x_ind

    def _overwrite_data(cube, cube2):
        """
        Override the data of cube with that of cube2, where the horizontal
        domain of cube should contain that of cube2.

        """
        sx, sy = ants.utils.cube.horizontal_grid(cube)
        sdx, sdy = cube.coord_dims(sx)[0], cube.coord_dims(sy)[0]
        tx, ty = ants.utils.cube.horizontal_grid(cube2)

        slices = [slice(None)] * cube.ndim
        slices[sdx] = _coord_intersect(sx, tx)
        slices[sdy] = _coord_intersect(sy, ty)

        # Ensure that both cubes have the same dimension mapping.
        coord_names = [cube.coord(dimensions=(i)).name() for i in range(cube.ndim)]
        transpose = [cube2.coord_dims(name)[0] for name in coord_names]
        cube.data[tuple(slices)] = cube2.data.astype(cube.dtype).transpose(transpose)

    # Ensure consistency between cube metadata (do they both describe the same
    # phenomena).
    _merge_compatible(primary_cube, alternate_cube)

    ants.utils.cube.guess_horizontal_bounds([primary_cube, alternate_cube])
    sx, sy = ants.utils.cube.horizontal_grid(primary_cube)
    tx, ty = ants.utils.cube.horizontal_grid(alternate_cube)
    if sy.coord_system != ty.coord_system or sx.coord_system != tx.coord_system:
        raise RuntimeError("Currently only same coordinate system merging " "supported")

    # define a polygon for the domain we're merging into
    domain_polygon = [
        [sx.bounds.min(), sy.bounds.min()],
        [sx.bounds.max(), sy.bounds.min()],
        [sx.bounds.max(), sy.bounds.max()],
        [sx.bounds.min(), sy.bounds.max()],
    ]
    domain_polygon = Polygon(domain_polygon)

    if validity_polygon:
        if isinstance(validity_polygon, (tuple, list)):
            # Instantiate polygon from x, y pairs.
            validity_polygon = Polygon(validity_polygon)
        if validity_polygon.contains(domain_polygon):
            raise RuntimeError("Target domain is wholly within the provided polygon")
    else:
        # Workaround for supporting different shaped sources.
        validity_polygon = domain_polygon

    if not np.isreal(primary_cube.dtype):
        warnings.warn(
            "The source provided is not of dtype float and cannot "
            "store nan values, unable to distinguish between "
            "missing and no values in the case of an overlap"
        )

    merged_cube = _unified_grid(primary_cube, alternate_cube)
    # Fill the merged cube data with the primary cube data
    _overwrite_data(merged_cube, primary_cube)
    # Migrate the alternate cube data to the full grid version
    full_alternate_cube = merged_cube.copy()
    _overwrite_data(full_alternate_cube, alternate_cube)

    if validity_polygon:
        # Take only the values from the primary cube which are within the
        # provided polygon.
        corners = (
            (sx.bounds[:, i], sy.bounds[:, j])
            for i, j in ((0, 0), (0, 1), (1, 1), (1, 0))
        )

        # Test all four corners for overlap for containment within polygon
        mask_inside = np.zeros((sy.points.size, sx.points.size), dtype="bool")
        for corner in corners:
            xx, yy = np.meshgrid(corner[0], corner[1])
            mask_inside |= contains(validity_polygon, xx, yy)
        mask_outside = ~mask_inside

        # Upscale mask to the full-size grid
        ex, ey = ants.utils.cube.horizontal_grid(merged_cube)
        x_ind = _coord_intersect(ex, sx)
        y_ind = _coord_intersect(ey, sy)
        full_mask_outside = np.ones((ey.points.size, ex.points.size), dtype="bool")
        full_mask_outside[y_ind, x_ind] = mask_outside

        # Apply data which is outside of the polygon to the other.
        # Transpose the data (view) to allow broadcasting
        pdata, pmask = horizontal_grid_reorder(merged_cube)
        adata, amask = horizontal_grid_reorder(full_alternate_cube)
        pdata[full_mask_outside] = adata[full_mask_outside]
        pmask[full_mask_outside] = amask[full_mask_outside]

    # Identify overlap priority using np.nan values (these are assigned
    # when source cells are beyond the extent of the target grid whilst
    # regridding).
    pdata, pmask = horizontal_grid_reorder(merged_cube)
    adata, amask = horizontal_grid_reorder(full_alternate_cube)
    slices = [slice(None)] * pdata.ndim
    slices[2:] = [0] * (pdata.ndim - 2)
    nan_mask = np.isnan(pdata[tuple(slices)])
    pdata[nan_mask] = adata[nan_mask]
    pmask[nan_mask] = amask[nan_mask]

    # Clear some memory if we can
    np.ma.MaskedArray.shrink_mask(merged_cube.data)

    if np.isnan(merged_cube.data).any():
        raise RuntimeError(
            "Coverage of provided sources is not complete, unable to merge datasets."
        )
    return merged_cube


def _spiral_wrapper(
    unresolved_mask,
    to_fill_mask,
    lats,
    lons,
    target_mask,
    invert_mask=False,
    constrained=False,
    cyclic=False,
):
    """
    Call the underlying UM spiral search.

    Parameters
    ----------
    unresolved_mask : :class:`~numpy.ndarray`
        A 2D boolean array representing the missing data values (y, x).
    to_fill_mask : :class:`~numpy.ndarray`
        A 2D boolean array representing the input mask (y, x).  This often
        represents the missing data and ocean values in the case of land only
        fields for example.
    lats : :class:`~numpy.ndarray`
        1D array of latitude values.
    lons : :class:`~numpy.ndarray`
        1D array of longitude values.
    target_mask : :class:`~numpy.ndarray`
        A 2D boolean array for type indentification (y, x).
        'invert_mask' determines whether True or False is denoted as masked.
        More often than not, this is the land binary mask field.  This maps to
        the 'lsm' variable of the spiral search algorithm.
    invert_mask : bool, optional
        Behavioural modifier for whether the target_mask represent True for
        masked elements or False for masked elements.  This actually maps to
        'is_land_field' in the spiral search.  By default (False), True denotes
        masked elements.
    constrained : bool, optional
        Constrained search behavioural modifier (200km).
    cyclic : bool, optional
        Specifying the field as being cyclic, allows both latitudinal and
        longitudinal wrap around in distance evaluation.

    Returns
    -------
    : tuple(:class:`~numpy.ndarray`, :class:`~numpy.ndarray`)
        First item corresponds to indices of missing data point, while the
        second item corresponds to indices of those elements which are to
        populate these missing data points.

    See Also
    --------
    `<https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_S11.pdf>`_

    .. note::

        See the reconfiguration spiral search module for further details on
        these parameters.

    .. warning::

        Performing a spiral search when 'cyclic' is True, may have significant
        performance implications.

    """
    unresolved_mask = unresolved_mask.reshape(-1)
    to_fill_mask = to_fill_mask.reshape(-1)
    target_mask = target_mask.reshape(-1)

    _missing_index = np.where(np.equal(to_fill_mask, True))[0]
    missing_index = _missing_index.astype("int64", copy=False)
    unresolved_mask = unresolved_mask.astype("bool", copy=False)
    target_mask = target_mask.astype("bool", copy=False)
    lats = lats.astype("float64", copy=False)
    lons = lons.astype("float64", copy=False)
    planet_radius = float(ants.coord_systems.EARTH_RADIUS)

    # Default constraint distance taken from reconfiguration (this became a
    # parameter in shumlib).
    constrained_max_dist = 200000.0
    # Default step size modifier for search taken from reconfiguration (this
    # became a parameter in shumlib).
    dist_step = 3

    msg = "Calling spiral search, with {} missing points to be resolved."
    _LOGGER.info(msg.format(missing_index.size))
    with ants.stats.TimeIt() as timer:
        replacing_index = spiral(
            target_mask,
            missing_index,
            unresolved_mask,
            lats,
            lons,
            planet_radius,
            bool(cyclic),
            bool(invert_mask),
            bool(constrained),
            constrained_max_dist,
            dist_step,
        )
    msg = "{} took {}".format("Spiral search", timer.time_taken)
    _LOGGER.info(msg)

    return missing_index, replacing_index


class FillABC(abc.ABC):
    """An abstract base class which provides an interface for fill operations.

    A custom fill class may be created by inheriting this base class,
    providing a concrete implementation of the
    :meth:`~ants.analysis.FillABC._calculate_fill_lookup` method.

    See Also
    --------
    :class:`~ants.analysis.UMSpiralSearch`
    :class:`~ants.analysis.KDTreeFill`
    """

    def __init__(self, source, search_mask=None, target_mask=None):
        """
        Fill missing data in the source with their nearest acceptable
        neighbours.  Nearest acceptable neighbours include all locations in
        the source which are unmasked.  Optionally, we can provide a
        ``search_mask`` to further constrain the search (thereby not having to
        override the source mask).  Missing data is those masked source
        locations which are unmasked in the target (``target_mask``).  All masked
        source locations which are masked in the target mask, will remain
        masked.

        Return a callable which applies pre-calculated (cached) results to the
        destination, calculated at the point of instantiation of this object with
        the provided source-target pair.

        Parameters
        ----------
        source : :class:`~iris.cube.Cube`
            Source dataset with unresolved points.  That is, missing points or
            perhaps coastlines which do not match a provided target landsea
            mask.
        search_mask : :class:`~iris.cube.Cube`, optional
            A mask used to constrain the set of points which are considered
            valid by the search in the input source.
        target_mask : :class:`~iris.cube.Cube`, optional
            Target mask field.  The source will inherit this mask.
            Often this represents a land or ocean mask.

        Returns
        -------
        ~collections.abc.Callable
            Callable object for applying the spiral search algorithm.

        Raises
        ------
        ValueError
            Where no suitable neighbour has been found.
        ValueError
            Where source, search_mask or target_mask are incompatible (not
            defined on identical horizontal grids).
        """
        # Cache a copy of the source horizontal grid to protect
        # against changes to the copied object from outside the class
        source_x, source_y = ants.utils.cube.horizontal_grid(source)
        self._source_x = source_x.copy()
        self._source_y = source_y.copy()

        if target_mask:
            self._validate_mask("target_mask", target_mask)
        if search_mask:
            self._validate_mask("search_mask", search_mask)

        inherit_mask = True
        if target_mask is None:
            inherit_mask = False
            # Create a target with all unmasked points.
            target_mask = next(source.slices((self._source_y, self._source_x)))
            target_mask = target_mask.copy(np.zeros(target_mask.shape, dtype="bool"))

        # Generate cache
        self._source = source.copy()
        self._target_mask = target_mask
        self._inherit_mask = inherit_mask
        self._missing_indices_2d = self._replacing_indices_2d = None
        self._source_mask = None
        self._search_mask = search_mask
        self.search(source)

    def _validate_mask(self, mask_name, mask):
        """Check a provided mask is consistent with the ``source`` cube.

        The ``mask`` is validated according to the following criteria:

        - The ``mask`` must be 2-dimensional.
        - The ``mask``'s horizontal grid must be consistent with that
          of the ``source`` cube used to instantiate the class.

        Parameters
        ----------
        mask_name : str
            Name to be used in the error message.
        mask : :class:`~iris.cube.Cube`
            Mask to validate.

        Raises
        ------
        ValueError
            If the ``mask`` is not 2-dimensional.
        ValueError
            If the ``mask``'s horizontal grid is inconsistent with that
            of the ``source`` cube.


        :meta public:
        """
        if mask.ndim != 2:
            msg = f"Expecting a 2-dimensional {mask_name}, got {mask.ndim}-dimensions."
            raise ValueError(msg)
        self._validate_horizontal_grids(mask_name, mask)

    def _validate_horizontal_grids(self, cube_name, cube):
        """Check a cube's horizontal grid is consistent with that of
        the ``source`` cube.

        Parameters
        ----------
        cube_name : str
            Name to be used in the error message.
        cube : :class:`~iris.cube.Cube`
            Cube to validate. The cube's x and y coordinates are compared against
            those of the ``source`` cube used to initialise the class.

        Raises
        ------
        ValueError
            If either the x or y coordinates do not match those of the
            original ``source`` cube.


        :meta public:
        """
        x_coord, y_coord = ants.utils.cube.horizontal_grid(cube)
        if not ants.utils.coord.relaxed_equality(self._source_x, x_coord):
            msg = (
                f"The provided {cube_name}'s x coordinates do not match "
                "those of the source."
            )
            raise ValueError(msg)

        if not ants.utils.coord.relaxed_equality(self._source_y, y_coord):
            msg = (
                f"The provided {cube_name}'s y coordinates do not match "
                "those of the source."
            )
            raise ValueError(msg)

    def _validate_destination(self, destination):
        destination_data, destination_mask_nd = horizontal_grid_reorder(destination)
        slices = [slice(None), slice(None)] + ([0] * (destination_data.ndim - 2))
        destination_mask = np.isnan(destination_data[tuple(slices)])
        destination_mask += destination_mask_nd[tuple(slices)]

        self._validate_horizontal_grids("destination cube", destination)
        if not (self._source_mask == destination_mask).all():
            raise ValueError(
                "Destination mask is not compatible with the "
                "cached nearest neighbours."
            )

    @abc.abstractmethod
    def _calculate_fill_lookup(self, unresolved_mask, to_fill_mask, target_mask):
        """Calculate the cached lookup arrays to be used to fill the destination cube.

        Parameters
        ----------
        unresolved_mask : :class:`~numpy.ndarray`
            A 2-dimensional boolean array representing the unresolved points in
            the source cube. These points are not considered valid fill candidates.
            Unresolved points are those which are masked in the source, or have
            been specified as points to ignore in the ``search_mask``.

            - ``True`` if point is unresolved (not valid fill candidate)
            - ``False`` if point is resolved (valid fill candidate)

            The array must be of the same shape as the horizontal dimensions
            of the source cube.
        to_fill_mask : :class:`~numpy.ndarray`
            A 2-dimensional boolean array representing the missing points in
            the source cube that require filling. Missing points are those which
            are masked in the source and not masked in the ``target_mask``.

            - ``True`` if point is missing (requires filling)
            - ``False`` if point is not missing (does not require filling)

            The array must be of the same shape as the horizontal dimensions
            of the source cube.
        target_mask : :class:`~numpy.ndarray`
            A 2-dimensional boolean array representing the target mask.
            The array must be of the same shape as the horizontal dimensions
            of the source cube.

        Returns
        -------
        tuple(:class:`~numpy.ndarray`, :class:`~numpy.ndarray`)
            First item corresponds to indices of missing data point, while the
            second item corresponds to indices of those elements which are to
            populate these missing data points.

        Raises
        ------
        ValueError
            If the provided source contains no valid data.
        ValueError
            If the algorithm cannot identify any valid neighbours for an
            unresolved point.



        :meta public:
        """
        pass

    def search(self, source):
        """Search for points to fill the missing data in the ``source``.

        Perform pre-calculation steps up front, independent of which underlying
        search algorithm is used:

        - Reshape data
        - Identify points to be filled (``to_fill_mask``)
        - Identify points that should be excluded from the search (``unresolved_mask``)
        - Call :meth:`~ants.analysis.FillABC._calculate_fill_lookup`, which wraps the
          specific underlying search algorithm
        - Cache the resulting lookup arrays, to be applied when the filler is called


        Parameters
        ----------
        source : :class:`~iris.cube.Cube`
            Source cube with unresolved points, identified by being masked or NaN.

        Raises
        ------
        ValueError
            If the provided source contains no valid data.
        ValueError
            If no valid neighbours can be identified for any cell.
        """
        # Transpose as necessary.
        source_data, mask = horizontal_grid_reorder(source)
        target_mask, _ = horizontal_grid_reorder(self._target_mask)
        target_mask = target_mask.astype("bool", copy=False)
        if self._search_mask:
            search_mask, _ = horizontal_grid_reorder(self._search_mask)
            search_mask = search_mask.astype("bool", copy=False)

        # Difference between the source and target_mask defines which points
        # are truly missing data points (NaN values are also considered
        # missing).
        # Assumes consistency across all horizontal slices.
        slices = [slice(None), slice(None)] + ([0] * (source_data.ndim - 2))
        source_mask = np.isnan(source_data[tuple(slices)])
        source_mask += mask[tuple(slices)]

        # Cache the source mask.
        self._source_mask = source_mask

        to_fill_mask = source_mask & ~target_mask  # Points we want resolving
        if self._search_mask:
            unresolved_mask = source_mask | search_mask  # Points we want excluding.
        else:
            unresolved_mask = source_mask

        if unresolved_mask.any():
            if unresolved_mask.all():
                msg = "The provided source doesn't appear to have any valid data."
                raise ValueError(msg)
            missing_indices_1d, replacing_indices_1d = self._calculate_fill_lookup(
                unresolved_mask, to_fill_mask, target_mask
            )
            # Unravel indices across horizontal domain so that broadcasting
            # occurs over all remaining dimensions.
            self._missing_indices_2d = np.unravel_index(
                missing_indices_1d, source_data.shape[:2]
            )
            try:
                self._replacing_indices_2d = np.unravel_index(
                    replacing_indices_1d, source_data.shape[:2]
                )
            except ValueError as err:
                original_msg = "".join(list(err.args))
                new_msg = f"{original_msg}. Are there any valid neighbours?"
                err.args = [new_msg]
                raise

    def __call__(self, destination):
        """
        Apply the cached results of the search algorithm to resolve points
        in the ``destination``.

        Parameters
        ----------
        destination : :class:`~iris.cube.Cube`
            Destination dataset with unresolved points.  That is, missing points or
            perhaps coastlines which do not match a provided target landsea
            mask.  This destination need not be the same as the source used to
            instantiate the class, however it must be compatible (the same
            grid and with the same points requiring filling).

        Returns
        -------
        : None
            In-place operation.

        Raises
        ------
        ValueError
            When the provided destination coordinates do not match those cached for
            the nearest neighbour search.
        ValueError
            If the destination mask is not compatible with the cached nearest
            neighbours.

        """
        self._validate_destination(destination)

        destination_data, destination_mask = horizontal_grid_reorder(destination)

        # Apply nearest neighbour cache to the provided source.
        if self._missing_indices_2d is not None:
            destination_data[
                self._missing_indices_2d[0], self._missing_indices_2d[1]
            ] = destination_data[
                self._replacing_indices_2d[0], self._replacing_indices_2d[1]
            ]
            destination_mask[
                self._missing_indices_2d[0], self._missing_indices_2d[1]
            ] = False

        # Inherit mask from final_mask (reorder dimensions to perform true
        # broadcasting)
        transpose_axes = [0, 1]
        transpose_axes = [
            i for i in range(destination_data.ndim) if i not in transpose_axes
        ] + transpose_axes
        if self._inherit_mask:
            target_mask, _ = horizontal_grid_reorder(self._target_mask)
            target_mask = target_mask.astype("bool", copy=False)
            destination_mask.transpose(transpose_axes)[:] = target_mask
        if not (destination.data.mask).any():
            destination.data = destination.data.data

    def __repr__(self):
        """Provide a string representation of the class instance."""
        return self.__class__.__name__


class UMSpiralSearch(FillABC):
    """Spiral search missing data fill and coastal adjustment algorithm.

    This uses the spiral search algorithm or ``coast_adj_method=3``
    as it is known in the community.

    See Also
    --------

    `<https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_S11.pdf>`_ :
    for details of the spiral search method.


    .. warning::

        Performing a spiral search for circular fields (wraparound) is
        known to have performance implications.
    """

    # Constrained search behavioural modifier (200km).  See reference.
    # This is useful in the case where the source has resolved
    # points over both masked and unmasked points as identified by the
    # target mask.  For example, source fields with resolved points over
    # both ocean and land.  That is, the target mask is also used for type
    # identification when performing a constrained search.  This
    # constrained search is most commonly done when the target field
    # represents a landsea mask, while the source has valid values over
    # both ocean and land.
    # - Caution should be taken when utilising the constrained search
    #   behaviour.  Types identification (land/ocean for example) is
    #   identified by the target mask.  This means that the target mask
    #   is assumed to be relevant to the source type identification.
    #
    # Dev note: Consider plugging this into the class initialisation if we are
    # presented with a usecase for using it.
    _CONSTRAINED = False

    def __init__(self, source, search_mask=None, target_mask=None):
        super().__init__(source, search_mask, target_mask)

    def __call__(self, destination):
        return super().__call__(destination)

    def _calculate_fill_lookup(self, unresolved_mask, to_fill_mask, target_mask):
        """Call the spiral search algorithm to calculate the fill lookup.

        :meta public:
        """
        if spiral is None:
            raise ValueError(_SPIRAL_IMPORT_ERROR_MESSAGE)

        cyclic = self._source_x.circular

        # When not constrained, ensure that all source points are
        # considered the same 'type' (all ocean or all land etc.).
        if not self._CONSTRAINED:
            target_mask = np.zeros(target_mask.shape, "bool")

        # We set land_field to False as masks are interpreted as True to
        # denote land and false to denote ocean (which is generally the
        # other way around to mask fields).
        missing_ind, replacing_ind = _spiral_wrapper(
            unresolved_mask,
            to_fill_mask,
            self._source_y.points,
            self._source_x.points,
            target_mask,
            False,
            self._CONSTRAINED,
            cyclic,
        )
        return missing_ind, replacing_ind


class FillMissingPoints(UMSpiralSearch):
    """
    Warning
    -------
    This class is deprecated as of ANTS 2.0. The functionality has been
    moved to :class:`~ants.analysis.UMSpiralSearch`.
    """

    def __init__(self, source, search_mask=None, target_mask=None):
        warnings.warn(
            "'ants.analysis.FillMissingPoints' is deprecated as of ANTS 2.0. "
            "The functionality of 'ants.analysis.FillMissingPoints' has been "
            "moved to 'ants.analysis.UMSpiralSearch'.",
            FutureWarning,
        )
        super().__init__(source, search_mask, target_mask)


class KDTreeFill(FillABC):
    """K-D tree missing data fill and coastal adjustment algorithm.

    See Also
    --------
    `<https://en.wikipedia.org/wiki/K-d_tree>`_ :
        for details of the K-D tree search method.
    """

    _default_latitude_scale = 1.0

    def __init__(self, source, search_mask=None, target_mask=None):
        config_latitude_scale = ants.config.CONFIG["ants_fill"]["kdtree_latitude_scale"]
        if config_latitude_scale is not None:
            self.latitude_scale = float(config_latitude_scale)
        else:
            self.latitude_scale = self._default_latitude_scale
        super().__init__(source, search_mask, target_mask)

    def __call__(self, destination):
        return super().__call__(destination)

    def _calculate_fill_lookup(self, unresolved_mask, to_fill_mask, target_mask):
        """Call the K-D tree search algorithm to calculate the fill lookup.

        :meta public:
        """
        cartesian_coordinates = ants.utils.convert_to_cartesian(self._source)
        # Scale z coordinate by latitude scale factor,
        # to give higher weight to points of similar latitudes
        cartesian_coordinates[..., 2] *= self.latitude_scale
        fill_candidates_coordinates = cartesian_coordinates[~unresolved_mask]
        points_to_fill_coordinates = cartesian_coordinates[to_fill_mask]
        kdtree = KDTree(fill_candidates_coordinates)
        _, valid_index = kdtree.query(points_to_fill_coordinates)

        to_fill_mask_1D = to_fill_mask.reshape(-1)
        missing_ind = np.where(to_fill_mask_1D)[0]
        missing_ind = missing_ind.astype("int64")

        valid_replacing_indices = np.where(~unresolved_mask.reshape(-1))[0]
        replacing_ind = valid_replacing_indices[valid_index]

        return missing_ind, replacing_ind


def moore_neighbourhood_search(source, land_binary_mask, value=None):
    """
    Updates the source cube data, where necessary, to make it consistent
    with the land_binary_mask.

    This function is used to ensure that the source has data present on
    all land points specified by the land_binary_mask.  The land_binary_mask
    should have 1's to signify land points and 0's to signify ocean points.

    The algorithm used is relatively straight forward:
       1. where the land_binary_mask is 0 the source data will be set
          to missing.
       2. where the land_binary_mask is 1 and the source has missing data
          then one of two strategies are taken.  If there are non-missing
          data points in the Moore neighborhood (8 surrounding points) of
          source then the missing point is overwritten with the mean of the
          non-missing neighbours.  If the Moore neighborhood contains only
          missing data then the source data is set to 'value', or the
          source data mean if 'value' is None.

    Parameters
    ----------
    source : :class:`~iris.cube.Cube`
        Source cube which is to have its data updated according to the land
        binary mask.
    land_binary_mask : :class:`~iris.cube.Cube`
        The land_binary_mask indicates the ocean/land classification wanted
        on the source cube.
    value : Bool, optional
        Fill value used where there are no valid neighbours.

    Returns
    -------
    : :class:`~iris.cube.Cube`
        Source, with data points modified corresponding to location identified
        by the provided land binary mask.

    .. note::

        The source and land_binary_mask must be on the same grid and currently
        must be also defined in the same orientation.

    .. warning::

        This routine should not be used in the decomposition framework without
        taking care of haloes in the decomposition.

    """
    if (source.ndim != 2) or land_binary_mask.ndim != 2:
        raise RuntimeError(
            "Currently, only mask application to 2D grids are "
            "supported and with no broadcasting."
        )
    sx, sy = ants.utils.cube.horizontal_grid(source)
    bx, by = ants.utils.cube.horizontal_grid(land_binary_mask)
    if not ants.utils.coord.relaxed_equality(
        sx, bx
    ) or not ants.utils.coord.relaxed_equality(sy, by):
        raise RuntimeError(
            "Both source and land_binary_mask must be defined " "on identical grids"
        )
    if (source.coord_dims(sx) != land_binary_mask.coord_dims(bx)) or (
        source.coord_dims(sx) != land_binary_mask.coord_dims(bx)
    ):
        raise RuntimeError(
            "Currently, the source and the land_binary_mask "
            "must be defined in the same orientation"
        )

    # Determine which values need to be filled and apply the supplied mask.
    if not np.ma.isMaskedArray(source.data):
        source.data = np.ma.array(source.data)

    # Difference between the current mask and the land_binary_mask supplied
    dmask = source.data.mask * (land_binary_mask.data == 1)

    # Set Ocean points missing
    source.data.mask = land_binary_mask.data == 0

    # Deal with missing land points
    neighbours = MooreNeighbourhood(source)

    # Points with some data in neighbourhood and missing data at centre points
    coasts = neighbours.any_non_missing() * dmask
    coasts_masks = neighbours.neighbourhood_mean()
    source.data[coasts] = coasts_masks[coasts]
    if value is None:
        value = source.data[source.data != source.data.fill_value].mean()

    # Islands
    islands = neighbours.all_missing() * dmask
    source.data[islands] = value


def derive_mask(source, geometries, geometry_crs=None):
    """
    Given a source and one or more geometries, return a mask representing
    containment with these geometries.

    Parameters
    ----------
    source : :class:`~iris.cube.Cube`
    geometries : iterator of :shapely:`shapely.geometry <shapely.geometry>`
        Geometries used to define containment mask within source
        domain.  See :class:`cartopy.io.shapereader.Reader` for helper
        functions on reading shapefiles.
    geometry_crs : :class:`~iris.coord_system.CoordSystem`, optional
        Geometry of the geometries provided, if not specified, assumed to be
        equivelent to the source.

    .. note::

        Currently limited to 2D cubes.

    """
    if source.ndim > 2:
        raise RuntimeError("Currently limited to 2D cubes")

    # FILTER RELEVANT GEOMETRIES - those that intersect the area under
    # interest.
    sx, sy = ants.utils.cube.horizontal_grid(source)
    minx, maxx = sx.bounds.min(), sx.points.max()
    miny, maxy = sy.bounds.min(), sy.points.max()
    src_cartopy_crs = sx.coord_system.as_cartopy_projection()
    bbox = shapely.geometry.Polygon(
        ((minx, miny), (minx, maxy), (maxx, maxy), (maxx, miny), (minx, miny))
    )

    # Project bbox if crs does not match
    geom_cartopy_crs = None
    if geometry_crs is not None and sx.coord_system != geometry_crs:
        geom_cartopy_crs = geometry_crs.as_cartopy_projection()
        bbox = geom_cartopy_crs.project_geometry(bbox, src_cartopy_crs)

    geoms = []
    for geom in geometries:
        geom = bbox.intersection(geom)
        if geom:
            # Project geometry to source crs if crs does not match
            if geom_cartopy_crs is not None:
                geom = src_cartopy_crs.project_geometry(geom, geom_cartopy_crs)
            geoms.append(geom)
    if len(geoms) == 0:
        return False

    # DERIVE MASK - through containment
    corners = (
        (sy.bounds[:, i], sx.bounds[:, j]) for i, j in ((0, 0), (0, 1), (1, 1), (1, 0))
    )
    # corners = [(sy.points, sx.points)] # points only

    mask_inside = np.zeros((sx.points.size, sy.points.size), dtype="bool")
    for corner in corners:
        xx, yy = np.meshgrid(corner[1], corner[0])
        for geom in geoms:
            mask_inside |= contains(geom, xx, yy)

    # Transform the mask to match the source dimension mapping
    dsx, dsy = source.coord_dims(sx)[0], source.coord_dims(sy)[0]
    if dsy > dsx:
        mask_inside = mask_inside.transpose((1, 0))

    return mask_inside

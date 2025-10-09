# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import functools
import hashlib
import operator
import os
import tempfile
import warnings

import ants
import cartopy.crs as ccrs
import iris
import numpy as np
from scipy.stats import rankdata
from shapely.geometry import LinearRing

ESMPY_IMPORT_MESSAGE = """To use ESMF, set the ESMFMKFILE environment variable.
https://earthsystemmodeling.org/esmpy_doc/release/latest/html/install.html
#importing-esmpy"""

try:
    import esmpy

    _ESMPY_IMPORT_ERROR = False
except Exception as _ESMPY_IMPORT_ERROR:
    if "ESMFMKFILE" not in os.environ:
        warnings.warn(ESMPY_IMPORT_MESSAGE)
    if os.environ.get("ESMFMKFILE") == "":
        warnings.warn(ESMPY_IMPORT_MESSAGE)
    esmpy = None
    msg = " {}\nProceeding without capabilities provided by ESMPy (esmf)."
    warnings.warn(msg.format(str(_ESMPY_IMPORT_ERROR)))


def _source_cube_sanity_check(src_cube):
    sx = src_cube.coord(axis="x")
    sy = src_cube.coord(axis="y")
    sgrid_dims = set(src_cube.coord_dims(sx) + src_cube.coord_dims(sy))

    coords_sharing = [
        src_cube.coords(contains_dimension=sgrid_dim) for sgrid_dim in sgrid_dims
    ]
    for coords in coords_sharing:
        for coord in coords:
            if coord not in [sx, sy]:
                msg = "Additional coordinate(s) vary along the " "horizontal mapping."
                raise ValueError(msg)


def _supported_cube_check(cube):
    x_dims = cube.coord_dims(cube.coord(axis="x"))
    y_dims = cube.coord_dims(cube.coord(axis="y"))
    msg = "Currently only increasing rank dimension mappings are supported."
    if len(x_dims) == len(y_dims):
        if len(x_dims) == 1:
            if not np.allclose(
                (rankdata(y_dims + x_dims, method="ordinal") - 1), np.arange(2)
            ):
                msg += "  For 1D cases, expecting y, x dimension mapping " "(not x, y)."
                raise RuntimeError(msg)
        else:
            for dims in [x_dims, y_dims]:
                if not np.allclose(
                    (rankdata(dims, method="ordinal") - 1), np.arange(len(dims))
                ):
                    raise RuntimeError(msg)


def _remove_undesirable_attributes(cube):
    # Temporary workaround for the valid_x attributes which should likely not
    # persist a regrid operation.
    rm_attributes = ["valid_range", "valid_min", "valid_max"]
    [
        cube.attributes.pop(key) if key in rm_attributes else None
        for key in list(cube.attributes.keys())
    ]


class _LatLonExtractor(object):
    """
    Adaptor class that takes a cube and extracts the true cell latitudes and
    longitudes.

    """

    def __init__(self, cube, staggering="corner"):
        """
        Constructor

        Parameter
        ----------
        cube: :class:`~iris.cube.Cube`

        staggering: :str
            Either 'corner' or ''.
        """
        self.lats = None
        self.lons = None
        self.inlon_coord = cube.coord(axis="x")
        self.inlat_coord = cube.coord(axis="y")

        is_bounded = self.inlon_coord.has_bounds() and self.inlat_coord.has_bounds()
        if staggering == "corner" and not is_bounded:
            msg = "Must provide bounds for corner staggering"
            raise ValueError(msg)

        # Ensure we have a suitable coordinate system present.
        ants.utils.cube.set_crs(cube)

        from_crs = self.inlon_coord.coord_system.as_cartopy_crs()
        # Transform the rotated pole grid to true lat/lon.
        to_crs = ccrs.Geodetic()
        yy, xx = self._get_2d_latlon(staggering)
        xyz = to_crs.transform_points(from_crs, xx, yy)
        self.lats = xyz[..., 1]
        self.lons = xyz[..., 0]

    def get_latitude(self):
        """
        Get the true latitudes.

        Returns
        -------
        : class:`~numpy.array`
           The latitudes.
        """
        return self.lats

    def get_longitude(self):
        """
        Get the true longitudes.

        Returns
        -------
        : class:`~numpy.array`
           The longitudes.
        """
        return self.lons

    def _get_2d_latlon(self, staggering):
        ndims = len(self.inlat_coord.shape)

        if ndims == 1:
            if staggering == "corner":
                lat1d = self._get_1d_corner(self.inlat_coord)
                lon1d = self._get_1d_corner(self.inlon_coord)
            else:
                lat1d = self.inlat_coord.points
                lon1d = self.inlon_coord.points
            lons, lats = np.meshgrid(lon1d, lat1d)

        elif ndims == 2:
            if staggering == "corner":
                latbnd = self.inlat_coord.bounds[0, 0]
                lonbnd = self.inlon_coord.bounds[0, 0]
                clockwise = not LinearRing(
                    [(lon, lat) for lon, lat in zip(lonbnd, latbnd)]
                ).is_ccw
                lats = self._get_2d_corner(self.inlat_coord, clockwise)
                lons = self._get_2d_corner(self.inlon_coord, clockwise)
            else:
                lats = self.inlat_coord.points
                lons = self.inlon_coord.points
        else:
            msg = "Only 1d and 2d horizontal coordinates are supported."
            raise ValueError(msg)

        return lats, lons

    def _get_1d_corner(self, coord):
        n = coord.shape[0]
        x = np.zeros((n + 1,), np.float64)
        x[:-1] = coord.bounds[:, 0]
        x[-1] = coord.bounds[-1, 1]
        return x

    def _get_2d_corner(self, coord, clockwise):
        # ESMPy expects unique nodes, while bounds have many duplicates
        # (adjacent cells have 2 common bounds for contiguous data).  This
        # method slices the bounds arrays to eliminate that duplication and to
        # yield a nodes array with every node included once.
        test_bounds = coord.bounds[0, :2]
        allclose = ants.utils.ndarray.allclose

        # test_bounds is the first two cells:
        #
        # X ---- B ---- X
        # |      |      |
        # |  1   |   2  |
        # |      |      |
        # X ---- A ---- X
        #
        # We then test where the bounds array starts by comparing which
        # starting position ends up with the bounds A and B being shared
        # between the two cells.
        bottom_left_start = allclose(
            test_bounds[0, 1:3], np.array([test_bounds[1, 0], test_bounds[1, 3]])
        )
        bottom_right_start = allclose(test_bounds[0, 0:2], test_bounds[1, 2:])
        top_right_start = allclose(
            np.array([test_bounds[0, 0], test_bounds[0, 3]]), test_bounds[1, 1:3]
        )
        # Default to top left start for bounds
        topleft = 0
        if bottom_left_start:
            topleft = 3
        elif bottom_right_start:
            topleft = 2
        elif top_right_start:
            topleft = 1

        bounds = coord.bounds
        if clockwise:
            # Adjust indexing where clockwise.
            topleft += 1
        clockwise = -1 if clockwise else 1

        m, n = coord.shape[0], coord.shape[-1]
        xx = np.zeros((m + 1, n + 1), np.float64)
        xx[:-1, :-1] = bounds[:, :, topleft % 4]
        xx[-1, :-1] = bounds[-1, :, (topleft + (clockwise * 1)) % 4]
        xx[-1, -1] = bounds[-1, -1, (topleft + (clockwise * 2)) % 4]
        xx[:-1, -1] = bounds[:, -1, (topleft + (clockwise * 3)) % 4]

        return xx


class _BoxIterator:
    """
    Box iterator is a class that allows one to iterate over the cells of
    boxes in any number of dimensions.

    """

    def __init__(self, dims, row_major=True):
        """
        Constructor

        Parameters
        ----------
        dims: : list of dimensions along each axis
        row_major: :True if row major, False if column major

        """
        self.dims = dims
        self.ntot = functools.reduce(operator.mul, self.dims, 1)
        self.ndims = len(self.dims)
        self.big_index = -1
        self.dim_prod = np.array([1 for i in range(self.ndims)])
        if row_major:
            # row major
            for i in range(self.ndims - 2, -1, -1):
                self.dim_prod[i] = self.dim_prod[i + 1] * self.dims[i + 1]
        else:
            # column major
            for i in range(1, self.ndims):
                self.dim_prod[i] = self.dim_prod[i - 1] * self.dims[i - 1]

    def __iter__(self):
        return self

    def __next__(self):
        if self.big_index < self.ntot - 1:
            self.big_index += 1
            return self
        else:
            raise StopIteration

    def get_indices(self):
        """
        Return
        ------
         current index set
        """
        return self.get_indices_from_big_index(self.big_index)

    def get_big_index(self):
        """
        Return
        ------
         current big index
        """
        return self.big_index

    def get_indices_from_big_index(self, big_index):
        """
        Get index set from given big index.

        Parameters
        ----------
        big_index: : big index

        Return
        ------
          index set

        Note
        ----
        no checks are performed to ensure that the returned big index is valid.

        """
        indices = np.array([0 for i in range(self.ndims)])
        for i in range(self.ndims):
            indices[i] = big_index // self.dim_prod[i] % self.dims[i]
        return indices

    def get_big_index_from_indices(self, indices):
        """
        Get the big index from a given set of indices.

        Parameters
        ----------
        indices: : index set

        Return
        ------
         big index

        Note
        ----
          no checks are performed to ensure that the returned indices are valid
        """
        return functools.reduce(
            operator.add, [self.dim_prod[i] * indices[i] for i in range(self.ndims)], 0
        )

    def reset(self):
        """
        Reset big index.
        """
        self.big_index = -1

    def get_dims(self):
        """
        Get the axis dimensions.

        Return
        ------
         return list of dimensions
        """
        return self.dims

    def is_big_index_valid(self, big_index):
        """
        Test if big index is valid.

        Parameters
        ---------
        big_index: : big index

        Return
        ------
        True if big index is in range, False otherwise
        """
        return big_index < self.ntot and big_index >= 0

    def are_indices_valid(self, inds):
        """
        Test if indices are valid.

        Parameters
        ----------
        @param inds index set

        Return
        ------
          True if valid, False otherwise
        """
        return functools.reduce(
            operator.and_,
            [inds[d] < self.dims[d] and inds[d] >= 0 for d in range(self.ndims)],
            True,
        )


class ESMFRegridder(object):
    def __init__(self, src_cube, target_cube, **kwargs):
        """
        Regridding using ESMF via ESMPY.

        Suitable for general curvilinear grids.

        Parameters
        ----------
        src_cube : :class:`~iris.cube.Cube`
           Defining the source grid. Must have latitude and longitude
           coordinates.  Latitude and longitude can be axes
           (iris.coords.DimCoord) or auxilliary coordinates
           (iris.coords.AuxCoord) -- lat/lon axes will be converted to
           iris.coords.AuxCoord if need be. The cube can have additional axes,
           e.g. elevation, time, etc., data will be interpolated linearly along
           those axes.
        target_cube : :class:`~iris.cube.Cube`
           Defining the target grid. Same conditions as for src_cube apply for
           the coordinates.
        method : :class:`str`, optional
           Defining the regridding method. Currently supported methods are:
            "areaWeighted" (default)
        persistent_cache : :obj:`bool`, optional
            Determine whether cache persists between runs.  That is, whether
            the cache persists after the program is terminated and will be
            available for successive runs of the application.  The cache
            location is determined by the TMPDIR environmental variable.
            Cache filenames are derived from source-target grid metadata
            checksums.  Default is False (that is, cache is destroyed with the
            class).

        """
        keywarg_diff = set(kwargs.keys()) - set(["method", "persistent_cache"])
        if keywarg_diff:
            msg = "unexpected keyword argument {}"
            raise ValueError(msg.format(keywarg_diff))

        if esmpy is None:
            raise _ESMPY_IMPORT_ERROR
        _supported_cube_check(src_cube)
        _supported_cube_check(target_cube)

        # Set some parameters.
        self.handle = None
        self.coordSystem = esmpy.api.constants.CoordSys.SPH_DEG
        self.method = esmpy.api.constants.RegridMethod.CONSERVE
        self.stagger = esmpy.StaggerLoc.CENTER

        method = kwargs.get("method", "areaweighted")
        if method.lower() != "areaweighted":
            raise ValueError("Currently only area weighted regridding " "supported.")

        # Simply return if the src and tgt grids are identical.
        if (src_cube.coord(axis="x") == target_cube.coord(axis="x")) and (
            src_cube.coord(axis="y") == target_cube.coord(axis="y")
        ):
            return
        _source_cube_sanity_check(src_cube)

        # Build the 2D esmf grid and field objects.
        self.esmpy_src_grid, self.esmpy_src_field = self._build_field(src_cube)
        self.esmpy_tgt_grid, self.esmpy_tgt_field = self._build_field(target_cube)

        # Compute/read the weights following ESMPy weights tutorial.  See
        # ESMPy docs for details of arguments.
        self._cache_fnme = self._gen_cache_filename([src_cube, target_cube])
        self._persistent_cache = bool(kwargs.get("persistent_cache", False))
        if not os.path.isfile(self._cache_fnme):
            # No existing cache so have ESMF generate it.
            self.handle = esmpy.api.regrid.Regrid(
                self.esmpy_src_field,
                self.esmpy_tgt_field,
                regrid_method=self.method,
                line_type=esmpy.api.constants.LineType.CART,
                unmapped_action=esmpy.api.constants.UnmappedAction.IGNORE,
                ignore_degenerate=True,
                filename=self._cache_fnme,
            )
        else:
            # Utilise the existing cache.
            try:
                self.handle = esmpy.api.regrid.RegridFromFile(
                    self.esmpy_src_field, self.esmpy_tgt_field, self._cache_fnme
                )
            except ValueError as err:
                msg = " Problem attempting to utilise cache file {}"
                msg = msg.format(self._cache_fnme)
                err_msg = list(err.args)
                err_msg[0] += msg
                err.args = err_msg
                raise

        # Get the latitude/longitude
        self.tgt_latlon = self._get_latlon_from_cube(target_cube)

        # Store reference to target cube, sets the output grid.
        self.tgt_cube = target_cube

        # Record source grid used in the calculation of the weights.
        self.src_grid = [src_cube.coord(axis="x"), src_cube.coord(axis="y")]

    @property
    def cache(self):
        """
        Return the cache produced from the esmf regrid.

        Return the deferred columns, rows and weights esmf cache: where
        columns correspond to source cell indices; rows correspond to target
        cell indices and weights corresponding to the column-row mapping.
        All three will match in size.  The weights correspond to the fraction
        of the target cell which is overlapped by the given source cell.  See
        the following illustration::

            |-|             - Source
            |---------|    - Target

            Here the weight between the source and target cell is 0.25 as the
            source cell covers 25% of the target cell.

            |---------|     - Source
            |-|              - Target

            Here the weight between the source and target cell is 1 as the
            source cell covers 100% of the target cell.

        See Also
        --------
        http://earthsystemmodeling.org/docs/release/ESMF_8_3_1/ESMF_refdoc/node3.html#SECTION03029000000000000000
        : for esmf weight only file specification.

        Note
        ----
        ESMPy currently only creates a "Weight Only Weight File" and so doesn't
        contain the destination fraction (frac_b).  Points are assumed not to
        extend beyond the grid.

        Returns
        -------
        : `numpy.ndarray`, `numpy.ndarray`, `numpy.ndarray`
            source indices (columns), target indices (rows), weights.


        Examples
        --------

        Example usage of cache in performing area weighted regrid calculation::

            regridder = self.scheme.regridder(source, target_grid)
            columns, rows, weights = regridder.cache
            source_flattened = source.data.reshape(-1)
            result = target_grid.copy(
                np.zeros(target_grid.shape, dtype='float'))
            result_flattened = result.data.reshape(-1)
            for ind in range(rows.size):
                row = rows[ind]
                column = columns[ind]
                result_flattened[row] = (
                    result_flattened[row] +
                    (weights[ind]*source_flattened[column]))

        Example as above but with sparse array usage::

            result = target.copy(np.zeros(target.shape, dtype='float'))
            sparse_array = scipy.sparse.coo_matrix(
               (weights, (rows, columns)),
               shape=(np.prod([tgt.data.shape[1], tgt.data.shape[2]]),
                      src.data.size)).tocsc()
            result.data.reshape(-1)[:] = (sparse_array * src.data.reshape(-1))

        """
        columns, rows, weights = ants.io.load.load(
            self._cache_fnme, ["col", "row", "S"]
        )
        # esmf is Fortran based, which means we must convert indices to C
        # ordered indices.
        # - Convert to 0 based indexing.
        # - Convert from between column and row based indexing.
        c_columns = np.unravel_index(
            columns.data - 1, self.esmpy_src_field.data.shape, order="F"
        )
        c_columns = np.ravel_multi_index(
            c_columns, self.esmpy_src_field.data.shape, order="C"
        )
        c_rows = np.unravel_index(
            rows.data - 1, self.esmpy_tgt_field.data.shape, order="F"
        )
        c_rows = np.ravel_multi_index(
            c_rows, self.esmpy_tgt_field.data.shape, order="C"
        )
        return c_columns, c_rows, weights.data

    def _gen_cache_filename(self, cubes):
        m = hashlib.md5()
        m.update(str(self.method).encode("utf-8"))
        m.update(str(self.__class__).encode("utf-8"))
        for cube in cubes:
            for coord in [cube.coord(axis="x"), cube.coord(axis="y")]:
                ncoord = coord.copy()
                ncoord.var_name = None
                m.update(str(ncoord).encode("utf-8"))
        return os.path.join(tempfile.gettempdir(), m.hexdigest() + ".nc")

    def __del__(self):
        # Free memory
        for item in [
            "handle",
            "esmpy_src_field",
            "esmpy_tgt_field",
            "esmpy_src_grid",
            "esmpy_tgt_grid",
        ]:
            handle = getattr(self, item, None)
            if handle is not None:
                handle.destroy()
        if not getattr(self, "_persistent_cache", True) and os.path.isfile(
            self._cache_fnme
        ):
            os.remove(self._cache_fnme)

    def __call__(self, inp_cube):
        """
        Apply the interpolation weights to the source field.

        Parameters
        ----------
        inp_cube : :class:`~iris.cube.Cube`
           Defining the input cube which has same horizontal grid as src_cube,
           see constructor.

        Returns
        -------
        : class:`~iris.cube.Cube`
           Target cube with regridded data.
        """
        # Do not perform an unnecessary regrid when the source and target are
        # identical.
        if not hasattr(self, "tgt_cube"):
            return inp_cube

        # Populating and check coordinate system information.
        ants.utils.cube.set_crs(inp_cube)
        equal_x = ants.utils.coord.relaxed_equality(
            inp_cube.coord(axis="x"), self.src_grid[0]
        )
        equal_y = ants.utils.coord.relaxed_equality(
            inp_cube.coord(axis="y"), self.src_grid[1]
        )
        if not equal_x or not equal_y:
            msg = (
                "The provided source cube has a horizontal grid which is "
                "not identical to that used to derive the weights."
            )
            raise ValueError(msg)
        _supported_cube_check(inp_cube)
        _source_cube_sanity_check(inp_cube)

        # Start and end data indices when running in parallel.
        src_ib = self.esmpy_src_grid.lower_bounds[esmpy.StaggerLoc.CORNER][0]
        src_ie = self.esmpy_src_grid.upper_bounds[esmpy.StaggerLoc.CORNER][0]
        src_jb = self.esmpy_src_grid.lower_bounds[esmpy.StaggerLoc.CORNER][1]
        src_je = self.esmpy_src_grid.upper_bounds[esmpy.StaggerLoc.CORNER][1]

        tgt_ib = self.esmpy_tgt_grid.lower_bounds[esmpy.StaggerLoc.CORNER][0]
        tgt_ie = self.esmpy_tgt_grid.upper_bounds[esmpy.StaggerLoc.CORNER][0]
        tgt_jb = self.esmpy_tgt_grid.lower_bounds[esmpy.StaggerLoc.CORNER][1]
        tgt_je = self.esmpy_tgt_grid.upper_bounds[esmpy.StaggerLoc.CORNER][1]

        # Create the output cube from the target horizontal coordinates and the
        # input cube axes.
        out_cube = self._create_output_cube(inp_cube)

        # Check, input and output cubes must have lat/lon coords.
        self._check_cubes(inp_cube, out_cube)

        # Collect all the coordinate indices that are neither longitude nor
        # latitude, same for input and output cubes.
        other_inds = self._get_other_coord_indices(out_cube)

        # All the dimensions other than lat/lon, same for input and output
        # cubes.
        other_dims = [out_cube.data.shape[i] for i in other_inds]

        # Collect all the indices and their standard name.
        inp_name2i = self._get_coord_indices(inp_cube)
        inp_skip = tuple(set(inp_name2i["longitude"] + inp_name2i["latitude"]))
        out_name2i = self._get_coord_indices(out_cube)
        out_skip = tuple(set(out_name2i["longitude"] + out_name2i["latitude"]))

        # Iterate over the non lat/lon dimensions of the target field.
        for it in _BoxIterator(other_dims):
            # Set of indices, excluding the lat/lon indices.
            inds = it.get_indices()

            # Slicing operator for the input/ouput field. These have ':' in
            # place of the lat/lon indices and integers for all other axes.
            inp_inds_ext = self._get_extended_slice(inp_skip, inds, inp_cube)
            out_inds_ext = self._get_extended_slice(out_skip, inds, out_cube)

            # Get the input data for that slice.
            inp_data = inp_cube.data[inp_inds_ext]

            # Regrid the mask.
            out_mask = None
            if np.ma.is_masked(inp_cube.data):
                self.esmpy_src_field.data[src_ib:src_ie, src_jb:src_je] = (
                    inp_cube.data.mask[inp_inds_ext]
                )
                self.handle(self.esmpy_src_field, self.esmpy_tgt_field)
                # CP: Not now, but in future we would define this with a
                # tolerance (mdtol).
                out_mask = self.esmpy_tgt_field.data[tgt_ib:tgt_ie, tgt_jb:tgt_je] > 0.0

            # Regrid the field.
            inp_data = inp_cube.data[inp_inds_ext]
            self.esmpy_src_field.data[src_ib:src_ie, src_jb:src_je] = inp_data
            self.handle(self.esmpy_src_field, self.esmpy_tgt_field)

            # Apply mask and copy into cube container.
            out_cube.data[out_inds_ext] = self.esmpy_tgt_field.data[
                tgt_ib:tgt_ie, tgt_jb:tgt_je
            ]
            if out_mask is not False:
                out_cube.data[out_inds_ext] = np.ma.masked_where(
                    out_mask, out_cube.data[out_inds_ext]
                )

        return out_cube

    def _check_cubes(self, src_cube, tgt_cube):
        has_lat, has_lon = self._check_has_latitudes_and_longitudes(src_cube)
        if not has_lat:
            msg = "No latitude in source cube"
            raise ValueError(msg)
        if not has_lon:
            msg = "No longitude in source cube"
            raise ValueError(msg)
        has_lat, has_lon = self._check_has_latitudes_and_longitudes(tgt_cube)
        if not has_lat:
            msg = "No latitude in target cube"
            raise ValueError(msg)
        if not has_lon:
            msg = "No longitude in target cube"
            raise ValueError(msg)

    def _check_has_latitudes_and_longitudes(self, cube):
        # Must have latitudes and longitudes.
        has_lat, has_lon = False, False
        for coord in cube.coords():
            if isinstance(coord.standard_name, str) or isinstance(
                coord.standard_name, str
            ):
                if coord.standard_name.find("latitude") >= 0:
                    has_lat = True
                if coord.standard_name.find("longitude") >= 0:
                    has_lon = True
        return has_lat, has_lon

    def _get_latlon_from_cube(self, cube):
        #
        # Extract the latitude and longitude coordinates from the cube.
        # Apply coordinate transformation to convert a dim coord to
        # a 2d aux coordinate if need be.
        #
        data = {
            "lat_coord": None,
            "lat_data": None,
            "lon_coord": None,
            "lon_data": None,
        }

        data["lon_coord"], data["lat_coord"] = ants.utils.cube.horizontal_grid(cube)
        # for the data, no need to use the bounds to compute the lats/lons
        staggering = ""
        extractor = _LatLonExtractor(cube, staggering=staggering)
        data["lat_data"] = extractor.get_latitude()
        data["lon_data"] = extractor.get_longitude()

        return data

    def _create_output_cube(self, inp_cube):
        # Create the output cube from the target cube and the input cube.
        # Latitudes and longitudes come from the tgt_cube passed to the
        # constructor.  All other axes come from the input cube.

        # Gather the output cube's coordinates from self.tgt_cube and inp_cube
        inp_coords = inp_cube.coords()
        ndims = len(inp_cube.data.shape)
        out_data_shape = [None for i in range(ndims)]
        out_coords = []
        out_coord_dims = []
        offset = 0
        for j in range(len(inp_coords)):
            coord = inp_coords[j]
            dims = inp_cube.coord_dims(coord)
            std_name = coord.standard_name
            is_string = isinstance(std_name, str) or isinstance(std_name, str)

            if is_string and std_name.find("latitude") >= 0:
                # Take latitude from the target cube.
                out_coords.append(self.tgt_latlon["lat_coord"])
                if len(dims) > 1:
                    for i in range(len(dims)):
                        out_data_shape[dims[i]] = self.tgt_latlon["lat_data"].shape[i]
                else:
                    out_data_shape[dims[0]] = self.tgt_latlon["lat_data"].shape[offset]
                    offset += 1

            elif is_string and std_name.find("longitude") >= 0:
                # Take longitude from the target cube.
                out_coords.append(self.tgt_latlon["lon_coord"])
                if len(dims) > 1:
                    for i in range(len(dims)):
                        out_data_shape[dims[i]] = self.tgt_latlon["lon_data"].shape[i]
                else:
                    out_data_shape[dims[0]] = self.tgt_latlon["lon_data"].shape[offset]
                    offset += 1

            else:
                # Take coordinate from the input cube.
                out_coords.append(coord)
                for i in range(len(dims)):
                    out_data_shape[dims[i]] = coord.shape[i]

            out_coord_dims.append(dims)

        # Create the output cube with data initialised to zero.
        data = np.ma.zeros(out_data_shape, np.float64)
        out_cube = iris.cube.Cube(
            data, standard_name=inp_cube.standard_name, var_name=inp_cube.var_name
        )

        # Add attributes and rename.
        out_cube.attributes = inp_cube.attributes.copy()
        out_cube.rename(inp_cube.name())

        # Build 2d data dimensions for lat and lon in case input cube had 1d
        # dim coord and target has 2d aux coords.
        latlon_dims = []
        inp_lon_coord, inp_lat_coord = ants.utils.cube.horizontal_grid(inp_cube)
        lat_dims = inp_cube.coord_dims(inp_lat_coord)
        lon_dims = inp_cube.coord_dims(inp_lon_coord)
        offset = 0
        latlon_dims.append(lat_dims[offset])
        if len(lat_dims) > 1:
            offset += 1
        latlon_dims.append(lon_dims[offset])

        # Add coordinates.
        offset = 0
        for j in range(len(out_coords)):
            coord = out_coords[j]
            dims = out_coord_dims[j]
            if isinstance(coord, iris.coords.DimCoord):
                # DimCoord.
                out_cube.add_dim_coord(coord, data_dim=dims[offset])
                if len(dims) > 1:
                    offset += 1
            elif isinstance(coord, iris.coords.AuxCoord):
                # AuxCoord.
                if hasattr(dims, "__len__") and len(dims) == len(coord.shape):
                    out_cube.add_aux_coord(coord, data_dims=dims)
                else:
                    # Input cube has a dim coord while target has 2d aux coord
                    out_cube.add_aux_coord(coord, data_dims=latlon_dims)

        # copy the attribute from the input cube
        out_cube.metadata = inp_cube.metadata
        _remove_undesirable_attributes(out_cube)

        return out_cube

    def _get_extended_slice(self, skip, inds, cube):
        #
        # Build the extended slice, using inds as index set for the axes
        # E.g. for skip=(0, 2) and inds = [a, b, c], returns (:, a, :, b, c),
        # that is the slice through indices 0 and 2 and take a, b, c for the
        # remaining indices.
        #
        # Note: May not run in parallel!
        slce = slice(0, None, None)
        n = len(skip) + len(inds)
        coord_inds_ext = []
        j = 0
        for i in range(n):
            if i in skip:
                coord_inds_ext.append(slce)
            else:
                coord_inds_ext.append(inds[j])
                j += 1
        inds_ext = coord_inds_ext
        return tuple(inds_ext)

    def _build_field(self, cube):
        #
        # Build the esmpy field object.
        #

        staggering = "corner"
        if self.method != esmpy.api.constants.RegridMethod.CONSERVE:
            # Need to pass corner coordinates in all cases. When the field is
            # cell centred this requires using bounds n (so staggering is
            # corner). For all other regridding methods we will not use the
            # bounds (so staggering is '').
            staggering = ""
        # Get the true latitudes and longitudes on cell vertices.
        extractor = _LatLonExtractor(cube, staggering)
        lats = extractor.get_latitude()
        lons = extractor.get_longitude()

        # Create the grid.
        cellDims = np.array([lons.shape[0] - 1, lats.shape[1] - 1])
        grid = esmpy.Grid(max_index=cellDims, coord_sys=self.coordSystem)

        # Allocate space for the vertices, esmpy wants the first coordinate to
        # be longitudes.
        grid.add_coords(staggerloc=esmpy.StaggerLoc.CORNER, coord_dim=0)
        # No need to add lats, it will be added automatically with lons

        # Get pointers to the esmf coordinates.
        lonPoint = grid.get_coords(coord_dim=0, staggerloc=esmpy.StaggerLoc.CORNER)
        latPoint = grid.get_coords(coord_dim=1, staggerloc=esmpy.StaggerLoc.CORNER)

        # When esmpy runs in parallel, the start/end indices may be other than
        # 0,-1.
        # CP: Is esmpy running in parallel being tested??  I suggest just
        #     removing it, and we can add it once we get something that just
        #     works onto trunk.  I think there is greater benefit to getting
        #     this onto trunk soon and looking at another iteration of
        #     development when the need arises.  Perhaps I'm wrong??
        ibeg0 = grid.lower_bounds[esmpy.StaggerLoc.CORNER][0]
        iend0 = grid.upper_bounds[esmpy.StaggerLoc.CORNER][0]
        ibeg1 = grid.lower_bounds[esmpy.StaggerLoc.CORNER][1]
        iend1 = grid.upper_bounds[esmpy.StaggerLoc.CORNER][1]

        lonPoint[...] = lons[ibeg0:iend0, ibeg1:iend1]
        latPoint[...] = lats[ibeg0:iend0, ibeg1:iend1]

        # Build the field, stagger is either CENTER or CORNER depending
        # on the method of interpolation. (Might consider choosing the method
        # given the cell_method.)
        dtype = esmpy.api.constants.TypeKind.R8  # always use double precision
        field = esmpy.Field(grid, staggerloc=self.stagger, typekind=dtype)

        # Note: not setting the field data at this point.
        return grid, field

    def _get_coord_indices(self, cube):
        #
        # Associates a coordinate name to an index.
        #
        res = {}
        coords = cube.coords()
        for coord in coords:
            std_name = coord.standard_name
            res[std_name] = cube.coord_dims(coord)

        """
        for i in range(len(coords)):
            std_name = coords[i].standard_name
            res[std_name] = i
        """
        if "grid_longitude" in res:
            res["longitude"] = res["grid_longitude"]
        if "grid_latitude" in res:
            res["latitude"] = res["grid_latitude"]
        return res

    def _get_other_coord_indices(self, cube):
        #
        # Collect all the indices that are neither longitude nor latitude
        # (whether mapped or not).
        res = []
        coords = cube.coords()
        for i in range(len(coords)):
            coord = coords[i]
            std_name = coord.standard_name
            dims = cube.coord_dims(coord)
            if not (
                std_name == "longitude"
                or std_name == "grid_longitude"
                or std_name == "latitude"
                or std_name == "grid_latitude"
            ):
                for j in dims:
                    res.append(j)
        return tuple(set(res))


class ConservativeESMF(object):
    """
    ESMF regridding scheme using esmpy.

    Regridding suitable for general curvilinear grids.

    """

    def __init__(self):
        self._method = "areaweighted"

    def regridder(self, src_grid_cube, target_grid_cube, **kwargs):
        """
        Creates an ESMF regridding scheme using esmpy.

        Parameters
        ----------
        src_grid_cube : :class:`~iris.cube.Cube`
            Defining the source grid.
        target_grid_cube : :class:`~iris.cube.Cube`
            Defining the target grid.

        Returns
        -------
        : :class:`ESMFRegridder`
           Callable with the interface `callable(cube)`

           where `cube` is a cube with the same grid as `src_grid_cube`
           that is to be regridded to the `target_grid_cube`.

        """
        return ESMFRegridder(
            src_grid_cube, target_grid_cube, method=self._method, **kwargs
        )

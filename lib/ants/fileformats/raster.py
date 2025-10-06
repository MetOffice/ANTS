# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Module for importing raster data to Iris cubes using the GDAL library.

See `GDAL - Geospatial Data Abstraction Library <https://gdal.org>`_ for more
information.

"""
import copy
import warnings

import ants
import ants.coord_systems as acoord
import iris.coord_systems
import iris.coords
import numpy as np
from ants.utils._dask import as_lazy_data

try:
    from osgeo import gdal, osr
    from osgeo.gdal import GA_ReadOnly

    _GDAL_IMPORT_ERROR = False
    osr.UseExceptions()

except Exception as _GDAL_IMPORT_ERROR:
    gdal = None
    msg = (
        ' {}\nUnable to import "gdal", proceeding without the '
        "capabilities it provides.  See install.rst"
    )
    warnings.warn(msg.format(str(_GDAL_IMPORT_ERROR)))

_GDAL_DATATYPES = {
    "i2": gdal.GDT_Int16,
    "i4": gdal.GDT_Int32,
    "u1": gdal.GDT_Byte,
    "u2": gdal.GDT_UInt16,
    "u4": gdal.GDT_UInt32,
    "f4": gdal.GDT_Float32,
    "f8": gdal.GDT_Float64,
}


class _GdalDataProxy(object):
    """A reference to the data payload of a single gdal raster band."""

    __slots__ = ("shape", "dtype", "path", "raster_band_index", "fill_value")

    def __init__(self, shape, dtype, path, raster_band_index, fill_value):
        # Convert to numpy y-x order (gdal uses and always assumes x-y
        # ordering)
        if len(shape) != 2:
            raise ValueError(
                "Raster image shape describes {} dimensions, "
                "expecting 2 dimensions".format(len(shape))
            )
        self.shape = shape[::-1]
        # Ensure that we always return signed data - CF compliance
        #     - this should be handled in iris netcdf at some point, handling
        #       the saving of netcdf3 output properly (auto type-casting etc.)
        dtype = np.dtype(dtype)
        if dtype.name.startswith("uint"):
            dtype = np.dtype(np.sctypeDict[dtype.num + 1])
        self.dtype = dtype
        self.path = path
        self.raster_band_index = raster_band_index

        self.fill_value = np.ma.array(0, self.dtype).fill_value
        if fill_value is not None and fill_value is not np.nan:
            self.fill_value = np.array(fill_value, dtype)

    @property
    def ndim(self):
        return len(self.shape)

    def __getitem__(self, keys):
        def _offset_winsize(key, size):
            # Handle slices
            if hasattr(key, "__iter__"):
                slices = ants.utils.ndarray.group_indices(key)
                if len(slices) > 1:
                    msg = "Currently no support for discontiguous extraction."
                    raise ValueError(msg)
                key = slices[0]

            if isinstance(key, slice):
                if key.step not in (None, 1):
                    raise IndexError(
                        "Step size not currently supported for " "gdal indexing"
                    )
                wstart = key.start or 0
                wstop = key.stop if key.stop is not None else size

                # Convert Python slice notation to an offest and size
                if wstart < 0:
                    wstart += size
                if wstop < 0:
                    wstop += size
                wstop = min(wstop, size)
                wsize = wstop - wstart

                z_offset = wstart
                z_winsize = wsize
            else:
                if key < 0 or key >= size:
                    raise IndexError("Raster index out of range")
                z_offset = key
                z_winsize = 1
            return (z_offset, z_winsize)

        xind, yind = 1, 0
        if keys:
            x_offset, x_winsize = _offset_winsize(keys[xind], self.shape[xind])
            y_offset, y_winsize = _offset_winsize(keys[yind], self.shape[yind])
            # Note that gdal y-indexing is opposite
            y_offset = (self.shape[yind] - y_offset) - y_winsize
        else:
            x_offset = 0
            x_winsize = self.shape[xind]
            y_offset = 0
            y_winsize = self.shape[yind]

        dataset = gdal.Open(self.path, GA_ReadOnly)
        iband = dataset.GetRasterBand(self.raster_band_index + 1)
        data = iband.ReadAsArray(
            int(x_offset), int(y_offset), int(x_winsize), int(y_winsize)
        )
        # Again, y-indexing is opposite
        data = data[::-1, :]

        # Mask the array?
        data = np.ma.masked_values(data, self.fill_value, copy=False)
        # Ensure that we always return signed data - CF compliance
        if data.dtype.name.startswith("uint"):
            data = data.astype(data.dtype.name.lstrip("u"))
        return data

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(shape={self.shape}, "
            f"dtype='{self.dtype}', path='{self.path}', "
            f"fill_value={self.fill_value})"
        )

    def __getstate__(self):
        # Required to support pickling
        return [(name, getattr(self, name)) for name in self.__slots__]

    def __setstate__(self, state):
        # Required to support unpickling
        for key, value in state:
            setattr(self, key, value)


def _patch_projection_string(projection):
    """
    Patch introduced in #2043:

    Swap positions of latitude and longitude in a projection string.

    Version 3 of the projection file `gbats2_0ll_low_res.prj` found in
    '$UMDIR/ancil/atmos/master/vegetation/cover/igbp/v3/' is missing
    the axis information that osgeo.gdal now requires when loading raster files.
    When this information is missing, osgeo.gdal automatically populates it, but
    osgeo.osr expects latitude and longitude to the be listed in a different
    order when it later reads the string.
    """
    incorrect_axis_order = ',AXIS["Longitude",EAST],AXIS["Latitude",NORTH]'
    correct_axis_order = ',AXIS["Latitude",NORTH],AXIS["Longitude",EAST]'
    if incorrect_axis_order in projection:
        projection = projection.replace(incorrect_axis_order, correct_axis_order)
    return projection


def _get_crs(projection):
    """
    Derive a suitable iris crs based on a supplied gdal projection.

    """
    crs = None

    projection = _patch_projection_string(projection)

    if projection:
        srs = osr.SpatialReference(wkt=projection)
        try:
            srs.AutoIdentifyEPSG()
        except RuntimeError:
            "RuntimeError is raised if the spatial reference already has an EPSG code."
            pass
        try:
            # STAGE1: Identity via EPSG code
            epsg_code = int(srs.GetAuthorityCode(None))
            crs = acoord.EPSG_2_CRS[epsg_code]
        except (TypeError, KeyError):
            # STAGE2: Identify via name/proj4 parameters
            crs_name = srs.GetAttrValue("projcs")
            if crs_name:
                crs = acoord.Name2CRS.get_crs(crs_name)
            if crs is None:
                crs = acoord.Proj2CRS.get_crs(srs.ExportToProj4())
        if crs is None:
            msg = "Projection information not currently in lookup table: {}"
            raise RuntimeError(msg.format(projection))
    return crs


def _derive_coord(ax_dir, origin_xy, pixel_width, num_xy, crs):
    """Return an iris coordinate for the axis direction.

    The coordinate is derived from information provided by the GDAL raster
    datset (see https://gdal.org/user/raster_data_model.html).

    The y coordinate is reversed: the origin y point provided to origin_xy
    will come at the end of the returned coordinate.

    Parameters
    ----------
    ax_dir : str
        String representing the axis direction. Must be "x" or "y".
    origin_xy : tuple[float, float]
        Coordinates of the origin (corner of the raster).
    pixel_width : tuple[float, float]
        Pixel widths in x and y directions, respectively.
    num_xy : float[int, int]
        Number of pixels in x and y directions, respectively.
    crs : ants.coord_systems.CFCRS | None
        Coordinate reference system.

    Returns
    -------
    iris.coords.DimCoord
        A coordinate representing the x or y axis.
    """
    dim_info = dict(x=(0, None), y=(1, slice(None, None, -1)))

    ax_ind, aslice = dim_info[ax_dir]
    # Origin point is offset by half a pixel width from the true origin
    point_origin = origin_xy[ax_ind] + pixel_width[ax_ind] / 2.0
    # End point is offset from origin point by (N - 1)*pixel_width:
    # - the second pixel centre is one width away from the first,
    # - the third pixel centre is two widths away from the first,
    # - the Nth pixel centre is (N - 1) widths away from the first.
    point_end = point_origin + pixel_width[ax_ind] * (num_xy[ax_ind] - 1)
    points = np.linspace(
        point_origin,
        point_end,
        num_xy[ax_ind],
    )
    if aslice:
        points = points[aslice]

    if crs is not None:
        metadata = getattr(crs, ax_dir)
        coord = iris.coords.DimCoord(
            points,
            standard_name=metadata.standard_name,
            units=metadata.units,
            coord_system=copy.copy(crs.crs),
        )
    else:
        standard_name = "projection_{}_coordinate".format(ax_dir.lower())
        coord = iris.coords.DimCoord(points, standard_name=standard_name)
    ants.utils.coord.guess_bounds(coord)
    return coord


def load_cubes(filenames, callback=None):
    """
    Imports raster images using gdal and constructs a cube.

    Parameters
    ----------
    filenames : str or list
        Input file name(s).
    callback : :class:`~collections.abc.Callable`, optional
        Function which can be passed on to :func:`iris.io.run_callback`.

    Returns
    -------
    cube : iris.cube.Cube
        A 2D regularly gridded cube.  The resulting cube has regular,
        contiguous bounds.

    Note
    ----
        Unsigned integers are loaded as signed integers.

    """

    if gdal is None:
        raise _GDAL_IMPORT_ERROR
    gdal.UseExceptions()

    if isinstance(filenames, str):
        filenames = [filenames]
    for fname in filenames:
        dataset = gdal.Open(fname, GA_ReadOnly)
        if dataset is None:
            raise IOError("gdal failed to open raster image")

        # Get metadata applies to all raster bands
        transform = dataset.GetGeoTransform()
        origin_xy = (transform[0], transform[3])
        num_xy = (dataset.RasterXSize, dataset.RasterYSize)

        # This effectively indicates the bounds of the cells.
        pixel_width = (transform[1], transform[5])
        num_raster = dataset.RasterCount
        if not num_raster:
            return

        # Position of North 0, 0 is north-up
        rotation = (transform[2], transform[4])
        if rotation[0] != 0 or rotation[1] != 0:
            msg = "Rotation not supported: ({}, {})".format(rotation[0], rotation[1])
            raise ValueError(msg)

        # https://gdal.org/user/raster_data_model.html
        projection = dataset.GetProjection()
        crs = _get_crs(projection)

        # Calculate coordinate points
        x = _derive_coord("x", origin_xy, pixel_width, num_xy, crs)
        y = _derive_coord("y", origin_xy, pixel_width, num_xy, crs)

        # Create proxy data for each raster band.
        for iraster in range(num_raster):
            iband = dataset.GetRasterBand(iraster + 1)
            # BUG: Currently iris _GDAL_DATATYPES for gdal type byte is mapped
            # to u1, but u1 is lookup for an 8 bit unsigned integer.
            if iband.DataType == 1:
                dtype = np.dtype("byte")
            else:
                dtype = np.dtype(
                    [
                        key
                        for key, value in _GDAL_DATATYPES.items()
                        if value == iband.DataType
                    ][0]
                )
            proxy = _GdalDataProxy(
                num_xy, dtype, fname, iraster, iband.GetNoDataValue()
            )
            data = as_lazy_data(proxy)
            cube = iris.cube.Cube(data)
            cube.add_dim_coord(x, 1)
            cube.add_dim_coord(y, 0)

            # Perform any user registered callback function.
            cube = iris.io.run_callback(callback, cube, iband, fname)

            # Callback mechanism may return None, which must not be yielded
            if cube is None:
                continue

            yield cube

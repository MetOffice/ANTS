# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.coord_systems
import iris
from ants.utils.cube import CubeBuilder


def simple_3d_time_varying(
    crs=iris.coord_systems.GeogCS(6371229.0), times=3, shape=None, *args, **kwargs
):
    """Creates a 3-dimentional cube with varying time coordinate.

    The default cube created is:

    unknown / (unknown)                 (time: 3; latitude: 5; longitude: 6)
        Dimension coordinates:
            time                             x            -             -
            latitude                         -            x             -
            longitude                        -            -             x

    """
    if shape is None:
        default_shape = (times, 5, 6)
    else:
        default_shape = shape
    builder = CubeBuilder(crs, shape=default_shape, *args, **kwargs)
    builder.add_3d_time_coord(times)
    return builder._cube


def simple_4d_with_hybrid_height(
    crs=iris.coord_systems.GeogCS(6371229.0), longitude=6, shape=None, *args, **kwargs
):
    """
    air_temperature / (K)               (time: 3; model_level_number: 4; latitude: 5; longitude: 6)
         Dimension coordinates:
              time                           x                      -            -             -
              model_level_number             -                      x            -             -
              latitude                       -                      -            x             -
              longitude                      -                      -            -             x
         Auxiliary coordinates:
              level_height                   -                      x            -             -
              sigma                          -                      x            -             -
              surface_altitude               -                      -            x             x
         Derived coordinates:
              altitude                       -                      x            x             x

    """  # noqa
    if shape is None:
        default_shape = (3, 4, 5, longitude)
    else:
        default_shape = shape
    builder = CubeBuilder(crs, shape=default_shape, *args, **kwargs)
    builder.add_3d_time_coord(default_shape[0])
    builder.add_model_level_coordinate(additional_attributes={"positive": "up"})
    builder.add_sigma_aux_coord()
    builder.add_hybrid_height_coordinate_factory(longitude)
    builder.set_name("air_temperature")
    builder.set_units("K")
    return builder._cube


def simple_4d_with_hybrid_pressure(
    shape=(3, 4, 5, 6), crs=iris.coord_systems.GeogCS(6371229.0), *args, **kwargs
):
    """Creates a cube with hybrid pressure.

    ANTS does not support hybrid pressure cubes, this exists to check that ANTS
    correctly throws an error when handling one."""
    builder = CubeBuilder(crs, shape=shape, *args, **kwargs)
    builder.add_3d_time_coord(3)
    builder.add_model_level_coordinate()
    builder.add_sigma_aux_coord()
    builder.add_hybrid_pressure_coordinate_factory()
    builder.set_name("air_temperature")
    builder.set_units("K")
    return builder._cube


def gen_curvilinear_cube(crs, *args, **kwargs):
    """
    Generate curvilinear lat-lon cube by translating 1D cube on the specified
    coordinate system.

    When given a crs of iris.coord_systems.GeogCS(6371229.0) and a shape of (2,2),
    produces:

    unknown / (unknown)                 (-- : 2; -- : 2)
            Auxiliary coordinates:
                latitude                      x       x
                longitude                     x       x


    """
    builder = CubeBuilder(crs, *args, **kwargs)
    builder.make_cube_curvilinear(crs)
    return builder._cube


def gen_regular_cube(crs, *args, **kwargs):
    """
    Creates the most basic cube.

    When given a crs of iris.coord_systems.GeogCS(6371229.0) and a shape of (2,2),
    produces:

    unknown / (unknown)                 (latitude: 2; longitude: 2)
            Dimension coordinates:
                latitude                            x             -
                longitude                           -             x


    """
    builder = CubeBuilder(crs, *args, **kwargs)
    return builder._cube


def geodetic(
    shape=None,
    north_pole_lat=90.0,
    north_pole_lon=0.0,
    crs=iris.coord_systems.GeogCS(6371229.0),
    *args,
    **kwargs,
):
    """ "
    Produces a geodetic cube.

    Must have either a shape or data passed in.

    With the shape of (2,2) passed in, produces:

    unknown / (unknown)                 (latitude: 2; longitude: 2)
            Dimension coordinates:
                latitude                           x             -
                longitude                          -             x

    """
    crs = CubeBuilder.derive_crs(crs, north_pole_lat, north_pole_lon)
    builder = CubeBuilder(crs, shape=shape, *args, **kwargs)
    return builder._cube


def osgb(*args, **kwargs):
    """
    Return a cube covering the extent of the OSGB projection with the specified
    shape.

    See also :func:`gen_regular_cube`

    Default behaviour with the shape of (2,2) passed in, produces:

    unknown / (unknown)                 (projection_y_coordinate: 2; projection_x_coordinate: 2)
            Dimension coordinates:
                projection_y_coordinate                           x                           -
                projection_x_coordinate                           -                           x

    """  # noqa
    builder = CubeBuilder(ants.coord_systems.OSGB.crs, *args, **kwargs)
    return builder._cube

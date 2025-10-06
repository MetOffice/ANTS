# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
ANTS defines its own coordinate systems derived by CFCRS.  This acts to
encapsulate an iris coordinate system along with CF metadata.

Additionally, ANTS extends the iris.coord_systems.CoordSystem baseclass such
that every coordinate system has a new method
(see :meth:`ants.coord_systems.as_ants_crs`).
This allows one coordinate system to be treated as another, where required.
Examples include performing a regrid, where a WGS84 can be approximated as a
UMSPHERE.  Currently, the following ANTS routines/modules utilise this
coordinate system equivalence:

 * :func:`ants.ExtractConstraint`
 * :func:`ants.regrid.rectilinear`

"""
import copy
import re
from abc import ABCMeta, abstractmethod
from collections import namedtuple

import ants
import iris
import iris.coord_systems as icoord
from iris.fileformats.pp import EARTH_RADIUS


class CFCRS(object):
    """
    Ants encapsulation of coordinate system and metadata corresponding to grid
    metadata.

    """

    _AxisMeta = namedtuple("AxisMeta", "standard_name units")

    def __init__(self, crs):
        """
        Return an object describing a coordinate system along with metadata
        required for a grid defined on this coordinate system.

        Parameters
        ----------
        crs : :class:`iris.coord_systems.CoordSystem`
        x_metadata : dict
            Metadata describing the x axis of a grid with corresponding
            coordinate system.  Of the form
            {'standard_name': ..., 'units':, ...}.
        y_metatada : dict
            Metadata describing the x axis of a grid with corresponding
            coordinate system.  Of the form
            {'standard_name': ..., 'units':, ...}.

        """
        self._crs = crs

        if isinstance(crs, iris.coord_systems.GeogCS):
            x_metadata = {"standard_name": "longitude", "units": "degree_east"}
            y_metadata = {"standard_name": "latitude", "units": "degree_north"}
        elif isinstance(crs, iris.coord_systems.RotatedGeogCS):
            x_metadata = {"standard_name": "grid_longitude", "units": "degrees"}
            y_metadata = {"standard_name": "grid_latitude", "units": "degrees"}
        else:
            x_metadata = {"standard_name": "projection_x_coordinate", "units": "m"}
            y_metadata = {"standard_name": "projection_y_coordinate", "units": "m"}

        self._x_metadata = self._set_metadata(x_metadata)
        self._y_metadata = self._set_metadata(y_metadata)

    def __str__(self):
        fmt = "{!s}, x_metadata={!s}, y_metadata={!s}"
        return fmt.format(self.crs, self.x, self.y)

    def __repr__(self):
        return "{!r}".format(self.crs)

    def _set_metadata(self, value):
        return self._AxisMeta(**value)

    @property
    def crs(self):
        """Return coordinate system."""
        return copy.deepcopy(self._crs)

    @property
    def x(self):
        """Return metadata corresponding to the x axis."""
        return self._x_metadata

    @property
    def y(self):
        """Return metadata corresponding to the y axis."""
        return self._y_metadata


UM_SPHERE = CFCRS(iris.coord_systems.GeogCS(EARTH_RADIUS))


def _get_WGS84():
    """
    Return a standard WGS84 coordinate reference system from the
    default Iris definition.

    Returns
    -------
    :class:`ants.coord_systems.CFCRS`
            Ants coordinate system.

    """
    iris_defaults = iris.coord_systems.GeogCS.from_datum("WGS84")
    return CFCRS(
        iris.coord_systems.GeogCS(
            semi_major_axis=iris_defaults.semi_major_axis,
            semi_minor_axis=iris_defaults.semi_minor_axis,
        )
    )


WGS84_GEODETIC = _get_WGS84()

# Define our own OSGB rather than iris.coord_systems.OSGB as we do not want to
# impose projection limits for real usecases.
OSGB = CFCRS(
    iris.coord_systems.TransverseMercator(
        49,
        -2,
        400000,
        -100000,
        0.9996012717,
        iris.coord_systems.GeogCS(6377563.396, 6356256.909),
    )
)

EPSG_2_CRS = {4326: WGS84_GEODETIC, 27700: OSGB}


def as_ants_crs(self):
    """
    Return an ANTS coordinate system.

    Under most circumstances, return itself, unless the coordinate system can
    be treated as another, in which case, return its counterpart.  Here are
    the mappings between coordinate systems and their counterparts::

        if self == WGS84: return UM_SPHERE
        if self == OSGB: return TransverseMercator
        if self == RotatedGeogCS and grid_north_pole_latitude == 90:
            return Unrotated version of our crs
        else: return self

    Returns
    -------
    :class:`ants.coord_systems.CFCRS`

    Note
    ----
    This function is defined in ANTS but monkey patches
    :class:`iris.coord_systems.CoordSystem`

    """
    crs = self
    if isinstance(self, iris.coord_systems.RotatedGeogCS):
        # Treat as unrotated coordinate system where we can.
        # NOTE: iris regridding schemes should be made to do this internally,
        #       at which point, we can remove this here.
        cond1 = ants.utils.ndarray.allclose(self.grid_north_pole_latitude, 90)
        cond2 = ants.utils.ndarray.isclose(
            self.grid_north_pole_longitude, [0, 180]
        ).any()
        if self.ellipsoid == UM_SPHERE.crs and cond1 and cond2:
            crs = self.ellipsoid
    if self == WGS84_GEODETIC.crs:
        crs = UM_SPHERE.crs
    if isinstance(self, iris.coord_systems.OSGB):
        crs = ants.coord_systems.OSGB.crs
    return crs


# Add an additional method to the iris coordinate system base class
icoord.CoordSystem.as_ants_crs = as_ants_crs


class DefinitionsABC(object, metaclass=ABCMeta):
    """Abstract base class for creating coordinate reference systems mappers."""

    @abstractmethod
    def definitions():
        pass

    @abstractmethod
    def _re_pattern():
        pass

    @classmethod
    def get_crs(cls, value):
        """
        Get ANTS crs.

        Parameters
        ----------
        value : str
            String object to parse.

        Returns
        -------
        :class:`ants.coord_systems.CFCRS`
            Ants coordinate system.

        """
        value = re.findall(cls._re_pattern, value)
        result = None
        for definition in cls.definitions:
            exist = [part in definition[0] for part in value]
            if all(exist):
                result = definition[1]
                break
        return result


class Proj2CRS(DefinitionsABC, object):
    """Proj4 to ANTS crs mapper."""

    _re_pattern = r"[\+=a-zA-Z0-9]+"
    definitions = [
        ["+proj=longlat +a=6371229 +b=6371229 +no_defs", UM_SPHERE],
        ["+proj=longlat +R=6371229 +no_defs", UM_SPHERE],
    ]


class Name2CRS(DefinitionsABC, object):
    """Coordinate name to ANTS crs mapper."""

    _re_pattern = r"[a-zA-Z0-9]+"
    definitions = [["OSGB 1936 British National Grid", OSGB]]

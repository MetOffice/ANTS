# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
UM grid namelist format
-----------------------
This module intends to generate cubes from UM grid namelist files.

The grid namelist specification for UM grids is historically split into two
distinct encodings/usage: one was that defined by the central ancillary program
(CAP) for geneating ancillaries; another is that utilised by the UM ecosystem.

The implementation here, supports the CAP specification for the purpose of the
generation of ancillaries.  However, we also support a subset of the UM
ecosystem namelist specification (for supporting vertical levels) and also
for horizontal grid namelists where it overlaps with the CAP specification.

For details on the specification supported here, the user should refer to
:class:`CAPGridRegular` for regular grids, :class:`CAPGridVariable` for
variable resolution grids and :class:`VerticalLevels` for the vertical
definition specification.

"""
from abc import ABCMeta, abstractproperty
from collections import namedtuple

import ants
import dask.array as da
import iris
import numpy as np
from ants.fileformats.ancil.template import GRIDS


def ngrid(n_number, grid_staggering):
    """
    Return the shape for the provided UM notation for global grid resolution.

    The UM uses a notation of Nxxx for its global grid resolutions.
    These numbers map fairly straight forwardly onto the numbers
    of grid points in longitude and latitude.

    - The number of longitudes is twice the 'N' number.
    - The number of latitudes is 3/2 times the N' number rounded down to the
      nearest integer (+1 for newdynamics).

    Parameters
    ----------
    n_number : int
        The UM global grid resolution notation.
    grid_staggering : str or int
        The grid staggering, see :obj:`ants.fileformats.ancil.template.GRIDS`.

    Returns
    -------
    : tuple
        Shape, representing the number of latitudes by the number of
        longitudes.

    >>> ngrid(96, grid_staggering=6)
    (144, 192)
    >>> ngrid(96, grid_staggering=3)
    (145, 192)
    >>> ngrid(96, grid_staggering='endgame')
    (144, 192)
    >>> ngrid(216, grid_staggering=6)
    (324, 432)
    >>> ngrid(512, grid_staggering=6)
    (768, 1024)
    >>> ngrid(2048, grid_staggering=6)
    (3072, 4096)

    """
    msg = "Unexpected grid_staggering '{}', please choose from {}"
    if isinstance(grid_staggering, int):
        if grid_staggering not in ants.fileformats.ancil.template.GRIDS.values():
            raise ValueError(
                msg.format(grid_staggering, ants.fileformats.ancil.template.GRIDS)
            )
    else:
        try:
            grid_staggering = ants.fileformats.ancil.template.GRIDS[grid_staggering]
        except KeyError:
            raise ValueError(
                msg.format(grid_staggering, ants.fileformats.ancil.template.GRIDS)
            )

    ext = int(grid_staggering == ants.fileformats.ancil.template.GRIDS["newdynamics"])
    n_number == int(n_number)
    return (ext + int(1.5 * n_number), 2 * n_number)


class _NamelistGrid(object, metaclass=ABCMeta):
    _Coord = namedtuple("Coord", ["points", "bounds"])

    def __init__(self, definition):
        # Load all the necessary information into a flat namespace
        self._raw = {group: {} for group in self.defaults}
        for group in self.defaults:
            for subkey in self.defaults[group]:
                if group in definition:
                    self._raw[group][subkey] = definition[group].get(
                        subkey, self.defaults[group][subkey]
                    )
                else:
                    self._raw[group][subkey] = self.defaults[group][subkey]

        missing_groups = set(self.defaults.keys()) - set(definition.keys())
        if missing_groups:
            msg = "Cannot deduce grid, the following groups as missing: {}"
            raise IOError(msg.format(list(missing_groups)))

    @abstractproperty
    def defaults(self):
        raise NotImplementedError

    @abstractproperty
    def x(self):
        pass

    @abstractproperty
    def y(self):
        pass

    @abstractproperty
    def shape(self):
        pass

    @abstractproperty
    def attributes(self):
        pass

    @abstractproperty
    def coord_system(self):
        pass

    def get_cube(self):
        """Return a cube representation of the grid."""
        data = da.zeros(self.shape, chunks=self.shape)
        cube = iris.cube.Cube(data, long_name="Model Grid")

        crs = self.coord_system
        crs = ants.coord_systems.CFCRS(crs)
        x_coord = iris.coords.DimCoord(
            self.x.points,
            bounds=self.x.bounds,
            coord_system=crs.crs,
            standard_name=crs.x.standard_name,
            units=crs.x.units,
        )
        y_coord = iris.coords.DimCoord(
            self.y.points,
            bounds=self.y.bounds,
            coord_system=crs.crs,
            standard_name=crs.y.standard_name,
            units=crs.y.units,
        )

        modulus = getattr(x_coord.units, "modulus")
        if modulus is not None:
            # Ensure that our points don't extend beyond range 360
            xmin, xmax = 0, modulus
            if (x_coord.points.max() - x_coord.points.min()) > (xmin + xmax):
                msg = "x values overlap, points range: ({}, {})."
                raise RuntimeError(
                    msg.format(x_coord.points.min(), x_coord.points.max())
                )
        modulus = getattr(y_coord.units, "modulus")
        if modulus is not None:
            # Ensure that our points don't extend beyond (-90 90)
            ymin, ymax = (-1 * (modulus // 4)), (modulus // 4)
            if (y_coord.points.max() > ymax) or (y_coord.points.min() < ymin):
                msg = "y value range ({}, {}) extends beyond the (-90, 90) " "range."
                raise RuntimeError(
                    msg.format(y_coord.points.min(), y_coord.points.max())
                )

        cube.add_dim_coord(y_coord, 0)
        cube.add_dim_coord(x_coord, 1)
        cube.attributes = self.attributes

        ants.utils.cube.guess_horizontal_bounds(cube)
        ants.utils.cube.derive_circular_status(cube)
        return cube


class _CAPGrid(_NamelistGrid):
    @property
    def _is_rotated(self):
        res = False
        if self._raw["grid"]["phi_pole"] != 90 or self._raw["grid"][
            "lambda_pole"
        ] not in [180, 0]:
            res = True
        return res

    @property
    def coord_system(self):
        """Return the coord_system of the grid."""
        crs = ants.coord_systems.UM_SPHERE.crs
        if not self._is_rotated:
            coord_system = crs
        else:
            coord_system = iris.coord_systems.RotatedGeogCS(
                self._raw["grid"]["phi_pole"],
                self._raw["grid"]["lambda_pole"],
                ellipsoid=crs,
            )
        return coord_system


class CAPGridRegular(_CAPGrid):
    """
    UM grid regular grid namelist ('GRID') interpreter.

    See the following specification::

        points_lambda_targ
            - Number of columns (longitudes).
            - Optional: Parameter is derived if `delta_lambda_targ` specified.

        points_phi_targ:
            - Number of rows (latitudes).
            - Optional: Parameter is derived if `phi_lambda_targ` specified.

        lambda_origin_targ
            - Longitude origin.
            - Default: 0.0 if not specified.

        phi_origin_targ:
            - Latitude origin.
            - Default: 90.0 if not specified. This parameter should be specified
              for ENDgame grids.

        delta_lambda_targ:
            - Longitude spacing (degrees).
            - Optional: Parameter is derived if `points_lambda_targ` specified.

        delta_phi_targ:
            - Latitutde spacing (degrees).
            - Optional: Parameter is derived if `points_phi_targ` specified.

        phi_pole:
            - Real latitude of North Pole of the rotated grid.
            - Default: 90.0

        lambda_pole:
            - Real longitude of North Pole of the rotated grid.
            - Default: 0.0

        global:
            - Global grid.
            - Default: T (True).

        igrid_targ:
            - Grid indicator (2=ArwakawaB, 3=ArwakawaC, 6=ENDgame).
            - Default: 6

        inwsw:
            - ==0 if phi origin specified as NW corner. ==1 if SW corner.
            - Default: 1

    Raises
    ------
    RuntimeError
        If the grid is overspecified, and the number of points is not
        consistent with the spacing between the points, a RunTimeError will be
        raised.

    RuntimeError
        In the case where grids are underspecified, a suitable RuntimeError
        exception will be raised.

    """

    defaults = {
        "grid": {
            "points_lambda_targ": None,
            "points_phi_targ": None,
            "lambda_origin_targ": 0.0,
            "phi_origin_targ": 90.0,
            "delta_lambda_targ": None,
            "delta_phi_targ": None,
            "phi_pole": 90.0,
            "lambda_pole": 0.0,
            "global": True,
            "igrid_targ": GRIDS["endgame"],
            "inwsw": 0,
            "rotated_interp": None,
        }
    }

    def __init__(self, definition):
        super(CAPGridRegular, self).__init__(definition)

        if self._raw["grid"]["rotated_interp"] is not None:
            msg = (
                '"rotated_interp" has a value: {} but is not currently '
                "being interpreted".format(self._raw["grid"]["rotated_interp"])
            )
            raise RuntimeError(msg)

    @property
    def is_endgame(self):
        """Return True for an ENDgame grid and false otherwise."""
        return self._raw["grid"]["igrid_targ"] == 6

    @property
    def y(self):
        """Return y tuple (points, bounds)."""
        if getattr(self, "_y", None) is None:
            stop = self._start_yx[0] + (self._step_yx[0] * (self.shape[0] - 1))
            points = np.linspace(self._start_yx[0], stop, self.shape[0], endpoint=True)
            self._y = self._Coord(points, None)
        return self._y

    @property
    def x(self):
        """Return x tuple (points, bounds)."""
        if getattr(self, "_x", None) is None:
            stop = self._start_yx[1] + (self._step_yx[1] * (self.shape[1] - 1))
            points = np.linspace(self._start_yx[1], stop, self.shape[1], endpoint=True)
            self._x = self._Coord(points, None)
        return self._x

    @property
    def _start_yx(self):
        """Return a tuple representing the origin (start y, start x)."""
        return (
            self._raw["grid"]["phi_origin_targ"],
            self._raw["grid"]["lambda_origin_targ"],
        )

    @property
    def attributes(self):
        """Return attributes extracted from the namelist."""
        return {"grid_staggering": self._raw["grid"]["igrid_targ"]}

    @property
    def shape(self):
        """Return tuple representing the shape of the grid."""

        if getattr(self, "_shape", None) is None:
            err_msg = "Grid definition underspecified, cannot deduce the shape"

            if self._raw["grid"]["points_lambda_targ"] is not None:
                xsize = self._raw["grid"]["points_lambda_targ"]
            elif self._is_global:
                xsize = abs(360 // self._step_yx[1])
            else:
                raise RuntimeError(err_msg)

            if self._raw["grid"]["points_phi_targ"] is not None:
                ysize = self._raw["grid"]["points_phi_targ"]
            elif self._is_global and not self.is_endgame:
                # Newdynmanics grids have an extra latitude point
                ysize = abs(180 // self._step_yx[0]) + 1
            elif self._is_global:
                # ENDgame grids do not have the additional latitude point
                ysize = abs(180 // self._step_yx[0])
            else:
                raise RuntimeError(err_msg)

            self._shape = (ysize, xsize)
        return self._shape

    @property
    def _step_yx(self):
        """Return a tuple representing step size (step y, step x)."""
        if getattr(self, "_yx", None) is None:
            dx = dy = 0

            lambda_step_size = self._raw["grid"]["delta_lambda_targ"]
            lambda_number_of_points = self._raw["grid"]["points_lambda_targ"]
            if lambda_step_size is not None:
                if lambda_number_of_points is not None and self._is_global:
                    # Check for contradictory overspecificed lambda coordinate
                    if lambda_step_size != 360.0 / lambda_number_of_points:
                        msg = (
                            "Grid over specified. Contradictory longitude step size "
                            f"({lambda_step_size}) and number of points "
                            f"({lambda_number_of_points}) have been defined for a "
                            "global grid."
                        )
                        raise RuntimeError(msg)
                dx = lambda_step_size
            elif self._is_global and lambda_number_of_points is not None:
                dx = 360.0 / lambda_number_of_points
            else:
                raise RuntimeError(
                    "Grid definition underspecified, cannot " "deduce x step size"
                )

            phi_step_size = self._raw["grid"]["delta_phi_targ"]
            phi_number_of_points = self._raw["grid"]["points_phi_targ"]
            if phi_step_size is not None:
                if phi_number_of_points is not None and self._is_global:
                    # Define error message here so that it displays the number of phi
                    # points set by the user.
                    msg = (
                        "Grid over specified. Contradictory latitude step size "
                        f"({phi_step_size}) and number of points "
                        f"({phi_number_of_points}) have been defined for a global grid."
                    )
                    if not self.is_endgame:
                        # For a non-ENDGAME grid, we assume the grid is New
                        # Dynamics.  The grid staggering of New Dynamics means
                        # the grid has an extra latitude point (both end
                        # points) e.g.:
                        #
                        # In 1D, we have New Dynamics as (where "x" denotes the points):
                        # x---x---x---x
                        # and ENDGame as:
                        # --x---x---x--
                        #
                        # It's the spacing between the latitude points we need for
                        # the consistency check, so we remove the extra point from
                        # New Dynamics to use the same computation for computing
                        # the spacing for both grids.
                        phi_number_of_points -= 1
                    # Check for contradictory overspecified phi coordinate
                    if phi_step_size != 180.0 / phi_number_of_points:
                        raise RuntimeError(msg)
                dy = phi_step_size
            elif self._is_global and phi_number_of_points is not None:
                if self.is_endgame:
                    dy = 180.0 / phi_number_of_points
                else:
                    # If the grid is not ENDGAME we account for the fact that
                    # latitude includes both end points where as longitude does not.
                    dy = 180.0 / (phi_number_of_points - 1)
            else:
                raise RuntimeError(
                    "Grid definition underspecified, cannot " "deduce y step size"
                )
            # North-South direction
            if self._raw["grid"]["inwsw"] == 0:
                dy = abs(dy) * -1
            else:
                dy = abs(dy)

            self._yx = (dy, dx)
        return self._yx

    @property
    def _is_global(self):
        """Return True for global field and False for not."""
        return bool(self._raw["grid"]["global"])


class CAPGridVariable(_CAPGrid):
    """
    UM grid variable resolution grid namelist interpreter.

    Variable resolution grids are defined using both 'GRID' and 'HORIZGRID'
    files.  The former is the regular grid definition as defined in
    :class:`CAPGridRegular`, except where variable grids are defined, only the
    coordinate system information (`phi_pole`, `lambda_pole`) is interpreted.
    Everything else is silently ignored.

    The later file ('HORIZGRID') contains the definition of the variable
    resolution grid points::

        lambda_input_p:
            - Longitude 'p' grid points.

        lambda_input_u:
            - Longitude 'u' grid points.

        phi_input_p:
            - Latitude 'p' grid points.

        phi_input_v:
            - Latitude 'v' grid points.

    Ancillaries are nearly always exclusively defined with the centre of the
    cells corresponding to the 'p' grid points.  'u' and 'v' points are then
    utilised in the definition to derive suitable bounds.

    """

    defaults = {
        "grid": {"phi_pole": 90, "lambda_pole": 0},
        "horizgrid": {
            "lambda_input_p": None,
            "lambda_input_u": None,
            "phi_input_p": None,
            "phi_input_v": None,
        },
    }

    def _derive_bounds(self, bounds_side, points):
        """
        Derive the bounds based on the 'bounds_side' supplied.

        bounds_side is evaluated to determine whether it defines an upper or
        lower bound, then the other cell bound side is derived accordingly.

        Parameters
        ----------
        bounds_side : :class:`numpy.ndarray`
            Representing either lower or upper bounds to the cell.
        points : :class:`numpy.ndarray`
            Representing the cell centres.

        """
        direction = (int(points[-1] > points[0]) * 2) - 1
        bounds = np.vstack([bounds_side[:-1], bounds_side[1:]]).T

        if (direction == 1 and bounds[0, 0] > points[0]) or (
            direction == -1 and bounds[0, 0] < points[0]
        ):
            calc_bound = points[0] - (direction * abs(bounds[0, 0] - points[0]))
            bounds = np.vstack([[calc_bound, bounds[0, 0]], bounds])
        if (direction == 1 and bounds[-1, -1] < points[-1]) or (
            direction == -1 and bounds[-1, -1] > points[-1]
        ):
            calc_bound = points[-1] + (direction * abs(bounds[-1, -1] - points[-1]))
            bounds = np.vstack([bounds, [bounds[-1, -1], calc_bound]])
        return bounds

    @property
    def y(self):
        """Return y tuple (points, bounds)."""
        if getattr(self, "_y", None) is None:
            points = np.array(self._raw["horizgrid"]["phi_input_p"])
            phi_v = self._raw["horizgrid"]["phi_input_v"]
            bounds = self._derive_bounds(phi_v, points)
            self._y = self._Coord(points, bounds)
        return self._y

    @property
    def x(self):
        """Return x tuple (points, bounds)."""
        if getattr(self, "_x", None) is None:
            points = np.array(self._raw["horizgrid"]["lambda_input_p"])
            lambda_u = self._raw["horizgrid"]["lambda_input_u"]
            bounds = self._derive_bounds(lambda_u, points)
            self._x = self._Coord(points, bounds)
        return self._x

    @property
    def attributes(self):
        """Return attributes extracted from the namelist."""
        if getattr(self, "_attr", None) is None:
            grid_stagerring = GRIDS["newdynamics"]
            direction = (
                int(
                    self._raw["horizgrid"]["lambda_input_p"][-1]
                    > self._raw["horizgrid"]["lambda_input_p"][0]
                )
                * 2
            ) - 1
            if (
                direction == 1
                and self._raw["horizgrid"]["lambda_input_u"][0]
                < self._raw["horizgrid"]["lambda_input_p"][0]
            ) or (
                direction == -1
                and self._raw["horizgrid"]["lambda_input_u"][0]
                > self._raw["horizgrid"]["lambda_input_p"][0]
            ):
                grid_stagerring = GRIDS["endgame"]
            self._attr = {"grid_staggering": grid_stagerring}
        return self._attr

    @property
    def shape(self):
        """Return tuple representing the shape of the grid."""
        xsize = len(self._raw["horizgrid"]["lambda_input_p"])
        ysize = len(self._raw["horizgrid"]["phi_input_p"])
        return ysize, xsize


class VerticalLevels(object):
    """
    UM vertical level namelist interpreter.

    Processes vertical namelists into iris vertical coordinates.  There's
    three distinct sets of vertical coordinates involved:  The namelist
    defines the top of the model (`z_top_of_model`); the first spherical shell
    level (`first_constant_r_rho_level`) and the `eta_theta` and `eta_rho`
    levels (see `UM New Dynamics Formulation
    <https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_015.pdf>`_ for
    details).  From these, the intermediate set of vertical coordinates -
    `blev`, `brlev`, `bhlev` and `bhrlev` are calculated (see `UM input and
    output file formats (F03)
    <https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf>`_ for
    details).

    The intermediate coordinates are used to calculate the final iris vertical
    coordinates: `level_height` (Zsea in F03 appendix A), `sigma` (C in F03
    appendix A) and `model level number`.  An additional method is provided
    to calculate a one dimensional cube with these vertical coordinates.

    """

    def __init__(self, namelist_dict):
        """
        Parameters
        ----------
        namelist_dict : dict
            Dictionary containing the following items::

                z_top_of_model : float
                    height of model top [m]
                first_constant_r_rho_level : int
                    index of first pure spherical shell level (note: FORTRAN
                    namelist, so indexed from 1)
                eta_theta : list of float
                    eta value for theta levels, must be one more float than the
                    list for eta_rho.
                eta_rho : list of float
                    eta value for rho (density) levels, must be one fewer float
                    than the list for eta_theta.
        Raises
        ------
        ValueError
            Raised if eta theta are eta rho are not consistent lengths.

        """
        vertlevs = namelist_dict["vertlevs"]
        self._z_model_top = vertlevs["z_top_of_model"]
        self._first_constant_rho = vertlevs["first_constant_r_rho_level"]
        self._eta_theta = np.array(vertlevs["eta_theta"], dtype=np.float64)
        _eta_rho = vertlevs["eta_rho"]

        # Checks that eta_theta array is one longer than the eta_rho array.
        n_theta, n_rho = len(self._eta_theta), len(_eta_rho)
        if (n_theta - n_rho) != 1:
            msg = (
                'Expecting "eta_theta" to be of length one greater than '
                '"eta_rho", got lengths {}, {} respectively.'
            )
            msg = msg.format(n_theta, n_rho)
            raise ValueError(msg)

        # blev defines level_height.points
        self._blev = self._z_model_top * self._eta_theta

        # Add surface rho level (not included in name list)
        _eta_rho.insert(0, 0.0)
        # rho level above model top not in namelist.  Instead, derived after
        # conversion to self._brlev, so use NAN as a placeholder:
        _eta_rho.append(np.NAN)

        self._eta_rho = np.array(_eta_rho, dtype=np.float64)
        # brlev defines level_height.lower bounds
        self._brlev = self._z_model_top * self._eta_rho
        # F03, Appendix A:
        # "For the top theta level, the upper layer boundary is a rho level
        # above which is calculated to be the same distance above as the rho
        # level below."
        # i.e. this is the calculation for the rho level above model top.
        self._brlev[-1] = self._blev[-1] + (self._blev[-1] - self._brlev[-2])

        # bhlev defines sigma.points
        # Evaluate hybrid coordinate scale factor for orography from eta inputs
        # Note: defined as zero once the first constant rho level is reached
        #
        # There's two equal and opposite offsets here.  Python arrays indexed
        # from 0, first_constant_rho in fortran namelist defined for arrays
        # indexed from 1, which would imply a -1 to self._first_constant_rho.
        # But we've added in the extra rho level, which would imply a +1.
        eta_reference = self._eta_rho[self._first_constant_rho]

        def _calculate_sigma(eta):
            return (1 - (eta / eta_reference)) ** 2

        # self._bhlev is defined for a theta level
        # self._bhlev[0] is sigma at theta level 0 -
        # i.e. between rho levels 0 and 1.
        self._bhlev = np.zeros([len(self._eta_theta)])
        # Note: defined as zero once the first constant rho level is reached
        self._bhlev[: self._first_constant_rho] = _calculate_sigma(
            self._eta_theta[: self._first_constant_rho]
        )

        # bhrlev defines sigma bounds, and is derived from rho levels (note
        # self._eta_rho includes hard-coded surface rho level and computed rho
        # level above model top for the upper layer boundary).
        self._bhrlev = np.zeros([len(self._eta_rho)])
        # Note: defined as zero once the first constant rho level is reached
        self._bhrlev[: self._first_constant_rho] = _calculate_sigma(
            self._eta_rho[: self._first_constant_rho]
        )

    @property
    def level_height(self):
        """
        Derive level_height AuxCoord with bounds.

        The points of the coordinate are derived from eta_theta levels, while
        the bounds are derived from eta_rho levels.  See Appendix A of F03 for
        details of the calculation.

        Returns
        -------
        : :class:`iris.coords.AuxCoord`
            Coordinate describing the level heights derived from the
            vertical namelist.

        Raises
        ------
        ValueError
            Raised if the level height is not monotonically increasing.
        """
        # Dev note: theta and rho levels are not directly used in this method.
        # The level height points and bounds are provided from self._blev and
        # self._brlev properties, which were calculated in the init() from the
        # theta and rho levels.
        points = self._blev
        if np.any(np.less(points[1:], points[0:-1])):
            msg = (
                "Resulting level height coordinate is not monotonically " "increasing."
            )
            raise ValueError(msg)
        lower_bounds = self._brlev[:-1]
        upper_bounds = self._brlev[1:]
        bounds = np.array([lower_bounds, upper_bounds]).T
        level_height = iris.coords.AuxCoord(
            points,
            bounds=bounds,
            var_name="level_height",
            units="m",
            attributes={"positive": "up"},
        )
        return level_height

    @property
    def model_level_number(self):
        """
        Creates a model_level_number DimCoord without bounds.

        Returns
        -------
        : :class:`iris.coords.DimCoord`
            Coordinate describing the model level numbers derived from the
            vertical namelist.

        """
        model_levels = iris.coords.DimCoord(
            np.arange(0, len(self._blev)),
            standard_name="model_level_number",
            units="1",
            attributes={"positive": "up"},
        )
        return model_levels

    @property
    def sigma(self):
        """
        Creates a sigma AuxCoord with bounds.

        The points of the coordinate are derived from eta_theta levels, while
        the bounds are derived from eta_rho levels.  See Appendix A of F03 for
        details of the calculation.

        Returns
        -------
        : :class:`iris.coords.AuxCoord`
            Coordinate describing the sigma (i.e. terrain following
            coordinate) derived from the vertical namelist.

        Raises
        ------
        ValueError
            Raised if the calculated coordinate is not monotonically
            decreasing.

        """
        # Dev note: theta and rho levels are not directly used in this method.
        # The sigma points and bounds are provided from self._bhlev and
        # self._bhrlev properties, which were calculated in the init() from
        # the theta and rho levels.
        points = self._bhlev
        if np.any(np.greater(points[1:], points[0:-1])):
            msg = "Resulting sigma coordinate is not monotonically decreasing."
            raise ValueError(msg)
        lower_bounds = self._bhrlev[0:-1]

        upper_bounds = self._bhrlev[1:]
        bounds = np.array([lower_bounds, upper_bounds]).T
        sigma = iris.coords.AuxCoord(
            points,
            bounds=bounds,
            long_name="sigma",
            units="1",
        )
        return sigma

    def _UM_workaround(self, cube):
        """Remove zeroth level from vertical level specification."""
        # Discard the zeroth level:
        result = cube.extract(
            iris.Constraint(coord_values={"model_level_number": lambda cell: 0 < cell}),
        )
        # Need to extend level 1 bounds down to the level 0 bounds we've just discarded.
        original_sigma_bounds = cube.coord("sigma").bounds
        um_sigma_bounds = result.coord("sigma").bounds
        um_sigma_bounds[0, 0] = original_sigma_bounds[0, 0]
        original_level_height_bounds = cube.coord("level_height").bounds
        um_level_height_bounds = result.coord("level_height").bounds
        um_level_height_bounds[0, 0] = original_level_height_bounds[0, 0]
        return result

    def get_cube(self, apply_UM_workaround=True):
        """
        Returns a one dimensional cube with the vertical coordinates attached.

        Returns
        -------
        : :class:`iris.cube.Cube`
            A cube with vertical coordinates model_level_number, level_height
            and sigma.

        """
        shape = len(self.model_level_number.points)
        target = iris.cube.Cube(
            da.zeros(shape, chunks=shape), long_name="Model vertical definition"
        )
        target.add_dim_coord(self.model_level_number, 0)
        target.add_aux_coord(self.sigma, 0)
        target.add_aux_coord(self.level_height, 0)
        if apply_UM_workaround:
            target = self._UM_workaround(target)
        return target

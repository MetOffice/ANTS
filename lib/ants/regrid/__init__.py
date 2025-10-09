# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
ANTS regridding provides capability which extend beyond what is currently
provided by iris for the convenience of ancillary generation.
Therefore, the user is referred to :mod:`iris.analysis` for regridding
capability provided by iris.  ANTS provides:

* :mod:`ants.regrid.rectilinear` a set of rectilinear horizontal
  regridding/interpolation approaches.
* :mod:`ants.regrid.interpolation` a set of vertical points-based approaches.
* :mod:`ants.regrid.esmf` regridding schemes for ESMF framework using emspy.

The reader is referred to the module documentation for further details.
For further details see the user guide.

"""
import logging
import sys

from ants.config import CONFIG

from . import esmf, interpolation, rectilinear

_LOGGER = logging.getLogger(__name__)


class GeneralRegridder:
    def __init__(
        self, src_grid, target_grid, horizontal_regridder=None, vertical_regridder=None
    ):
        """
        General regridder abstracting away horizontal and vertical regridding.

        Parameters
        ----------
        src_grid : :class:`~iris.cube.Cube`
           Defining the source grid.
        target_grid : :class:`~iris.cube.Cube`
            Defining the target grid.
        horizontal_regridder : :obj:`str`, optional
            Horizontal regridder callable.
        vertical_regridder : :obj:`str`, optional
            Vertical regridder callable.

        """
        self._horizontal_regridder = horizontal_regridder
        self._vertical_regridder = vertical_regridder
        if horizontal_regridder is None and vertical_regridder is None:
            raise AttributeError(
                "At least one of horizontal or vertical re-grid schemes must be "
                "provided."
            )

    def __call__(self, cube):
        """
        Regrid both vertical and horizontally where appropriate.

        Parameters
        ----------
        cube : :class:`~iris.cube.Cube`
            Source to be regridded.

        Returns
        -------
        : :class:`~iris.cube.Cube`
            Redridded result.

        """
        res = cube
        if self._vertical_regridder:
            res = self._vertical_regridder(res)
        if self._horizontal_regridder:
            res = self._horizontal_regridder(res)

        return res


class GeneralRegridScheme:
    """
    Abstract away the concept of horizontal and vertical regridding by
    providing a general scheme that handles both under the hood.

    """

    def __init__(self, horizontal_scheme=None, vertical_scheme=None):
        """
        General scheme which handles both vertical and horizontal regrid.

        The GeneralRegridScheme is useful to define a regrid method(s) and
        allow this regridding to be overridden after the fact via a
        configuration file where necessary.  In the case where a fixed
        regridding scheme is wanted and no override is to be allowed, please
        use the regridding scheme directly.

        Parameters
        ----------
        horizontal_scheme : :obj:`str`, optional
            Name or instance of horizontal regridding scheme to use.
            Default regridding scheme is None.
            A horizontal regrid scheme set in the |config| will take precedence over the
            value passed here.
        vertical_scheme : :obj:`str`, optional
            Name or instance of vertical regridding scheme to use.
            Default regridding scheme is None.
            A vertical regrid scheme set in the |config| will take precedence over the
            value passed here.


        .. |config| replace:: :class:`~ants.config.GlobalConfiguration`
        """
        # Set horizontal scheme.
        horizontal_scheme = (
            CONFIG["ants_regridding_horizontal"]["scheme"] or horizontal_scheme
        )
        horizontal_extrapolation_mode = (
            CONFIG["ants_regridding_horizontal"]["extrapolation_mode"] or None
        )

        # If the name of a regrid scheme is passed, create a scheme instance
        if isinstance(horizontal_scheme, str):
            self._horizontal_scheme = _create_horizontal_regrid_scheme_instance(
                horizontal_scheme, horizontal_extrapolation_mode
            )
        # Otherwise, a scheme instance has been passed, so use that
        else:
            self._horizontal_scheme = horizontal_scheme

        # Set vertical scheme.
        vertical_scheme = (
            CONFIG["ants_regridding_vertical"]["scheme"] or vertical_scheme
        )
        vertical_extrapolation_mode = (
            CONFIG["ants_regridding_vertical"]["extrapolation_mode"] or None
        )

        # If the name of a regrid scheme is passed, create a scheme instance
        if isinstance(vertical_scheme, str):
            self._vertical_scheme = _create_vertical_regrid_scheme_instance(
                vertical_scheme, vertical_extrapolation_mode
            )
        # Otherwise, a scheme instance has been passed, so use that
        else:
            self._vertical_scheme = vertical_scheme

        _LOGGER.info(repr(self))

    def regridder(self, src_grid, target_grid):
        """
        Creates a GeneralRegridder to regrid from the source to target grid.

        Parameters
        ----------
        src_grid : :class:`~iris.cube.Cube`
           Defining the source grid.
        target_grid : :class:`~iris.cube.Cube`
            Defining the target grid.

        Returns
        -------
        ~collections.abc.Callable
           Callable with the interface `callable(cube)`

           where `cube` is a cube with the same grid as `src_grid`
           that is to be regridded to the `target_grid`.

        """
        hregridder = None
        if self._horizontal_scheme is not None:
            hregridder = self._horizontal_scheme.regridder(src_grid, target_grid)
        vregridder = None
        if self._vertical_scheme is not None:
            vregridder = self._vertical_scheme.regridder(src_grid, target_grid)
        return GeneralRegridder(src_grid, target_grid, hregridder, vregridder)

    def __repr__(self):
        return "{}(horizontal_scheme={!r}, vertical_scheme={!r})".format(
            self.__class__.__name__, self._horizontal_scheme, self._vertical_scheme
        )


def _create_horizontal_regrid_scheme_instance(
    scheme_name: str, extrapolation_mode: str | None
):
    """Create a horizontal regrid scheme instance from a named regrid scheme.

    The regrid scheme is sourced from one of three places. They are, in decreasing order
    of precedence:

    1. :mod:`ants.regrid.rectilinear`
    2. :mod:`iris.analysis`
    3. :mod:`ants.regrid.esmf`

    Parameters
    ----------
    scheme_name: str
        The name of the scheme to create.
    extrapolation_mode: str | None
        The extrapolation mode to be used by the scheme. Note that not all schemes
        support extrapolation, e.g. AreaWeighted. In these cases, None should be passed.
        If None is passed for a scheme which does support extrapolation, that scheme's
        default extrapolation mode will be used.
    """
    regrid_scheme_class = (
        getattr(rectilinear, scheme_name, None)
        or getattr(sys.modules["iris.analysis"], scheme_name, None)
        or getattr(esmf, scheme_name, None)
    )
    if extrapolation_mode is None:
        regrid_scheme_instance = regrid_scheme_class()
    else:
        regrid_scheme_instance = regrid_scheme_class(
            extrapolation_mode=extrapolation_mode.lower()
        )
    return regrid_scheme_instance


def _create_vertical_regrid_scheme_instance(
    scheme_name: str, extrapolation_mode: str | None
):
    """Create a vertical regrid scheme instance from a named regrid scheme.

    The regrid scheme is sourced from :mod:`ants.regrid.interpolation`.

    Parameters
    ----------
    scheme_name: str
        The name of the scheme to create.
    extrapolation_mode: str | None
        The extrapolation mode to be used by the scheme. Note that not all schemes
        support extrapolation, e.g. Conservative. In these cases, None should be passed.
        If None is passed for a scheme which does support extrapolation, that scheme's
        default extrapolation mode will be used.
    """
    regrid_scheme_class = getattr(interpolation, scheme_name, None)
    if extrapolation_mode is not None:
        regrid_scheme_instance = regrid_scheme_class(
            extrapolation=extrapolation_mode.lower()
        )
    else:
        regrid_scheme_instance = regrid_scheme_class()
    return regrid_scheme_instance

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import warnings

import iris
import numpy as np
import shapely.geometry as sgeom
from shapely import affinity
from shapely.ops import unary_union

from . import utils


def _extract_overlap(source, target, fix_period=False, pad_width=0):
    """
    Return the sub-region of the source which overlaps the target.

    Parameters
    ----------
    source : :class:`~iris.cube.Cube`
        Source cube.
    target : :class:`~iris.cube.Cube`
        Target cube used to define the area overlap with the source.
    fix_period : :obj:`bool`, optional
        Ensure that the range of the returned cube in not altered.  This may
        result in discontiguous bounds if the extract returns two disconnected
        regions of the source.
    pad_width : :obj:`int`, optional
        Pad the slices by the specified number of cells.
        See :func:`utils.cube.get_slices`.

    Returns
    -------
    : :class:`~iris.cube.Cube`
        An Iris cube representing the sub-region of source which overlaps
        the area of the target.

    Raises
    ------
    ants.exceptions.NoCoverageError
        When no source cells can be found which overlap the target.
    RuntimeError
        Where an extraction would otherwise return an overlap with
        discontiguous coordinates, where the source was originally contiguous.

    Note
    ----
    This function is wraparound aware.

    """

    def _bounding_box(target_x, target_y, src_crs):
        tgt_crs = target_x.coord_system.as_ants_crs()
        xpnts = np.sort(target_x.bounds.flatten())
        ypnts = np.sort(target_y.bounds.flatten())

        if src_crs != tgt_crs:
            xpnts = np.hstack([xpnts[::2], xpnts[-1]])
            ypnts = np.hstack([ypnts[::2], ypnts[-1]])
            geom_pnts = (
                [[x, ypnts[0]] for x in xpnts]
                + [[xpnts[-1], y] for y in ypnts[1:-1]]
                + [[x, ypnts[-1]] for x in xpnts[::-1]]
                + [[xpnts[0], y] for y in ypnts[1:-1:-1]]
            )
            boxes = [
                geom for geom in utils.transform_bbox(geom_pnts, tgt_crs, src_crs).geoms
            ]
        else:
            minx, miny = xpnts[0], ypnts[0]
            maxx, maxy = xpnts[-1], ypnts[-1]
            boxes = [sgeom.box(minx, miny, maxx, maxy)]

        if len(boxes) == 2:
            # Combine geometries if possible when they can be adjusted to an
            # alternative range.
            # Ensure the geometries are ordered from left to right across
            # domain.
            boxes = sorted(boxes, key=lambda box: box.bounds[0])
            if getattr(target_x.units, "modulus", None):
                if utils.ndarray.allclose(
                    boxes[0].bounds[0] % target_x.units.modulus,
                    boxes[1].bounds[2] % target_x.units.modulus,
                ):
                    boxes[0] = affinity.translate(boxes[0], xoff=target_x.units.modulus)
                    boxes = unary_union(boxes)
            if isinstance(boxes, list) and len(boxes) == 2:
                # We may need to support these cases in future, which
                # will mean returning these geometries rather than
                # raising an exception here.
                msg = f"""Proj4 has returned multiple geometries during
                    extraction, resulting in discontiguous extraction
                    which cannot be resolved. modulus: {target_x.units.modulus}.
                    """
                raise RuntimeError(msg)
        else:
            boxes = boxes[0]

        return boxes

    # Handles cubes of different coordinate systems by determining a suitable
    # bounding box from the target points.
    utils.cube.guess_horizontal_bounds(target)
    target_x, target_y = utils.cube.horizontal_grid(target)
    utils.cube.guess_horizontal_bounds(source)
    source_x, source_y = utils.cube.horizontal_grid(source)

    src_crs = source_x.coord_system.as_ants_crs()
    box = _bounding_box(target_x, target_y, src_crs)

    (minx, miny, maxx, maxy) = box.bounds
    slices = utils.cube.get_slices(source, [miny, maxy], [minx, maxx], pad_width)

    if len(slices) > 2:
        msg = (
            "{} slices were found, expecting 1 or 2.  Currently no support "
            "for this case.".format(len(slices))
        )
        raise RuntimeError(msg)

    cubes = iris.cube.CubeList([])
    for ss in slices:
        cube = source.copy(source.lazy_data())[ss]
        xcoord = cube.coord(axis="x")
        if not fix_period:
            # Wrap coordinates of extracted if applicable to ensure contiguous
            # return.
            # Determine min x when considering wrapping coordinates
            xdim = source.coord_dims(source_x)[0]
            xmin_ind = max([ss[xdim].start for ss in slices])
            xmin = source_x.bounds[xmin_ind].min()
            if hasattr(xcoord.units, "modulus") and xcoord.units.modulus:
                xcoord.points = utils.ndarray.wrap_lons(
                    xcoord.points, xmin, xcoord.units.modulus
                )
                xcoord.bounds = utils.ndarray.wrap_lons(
                    xcoord.bounds, xmin, xcoord.units.modulus
                )
        cubes.append(cube)
    cube = cubes.concatenate_cube()
    utils.cube.derive_circular_status(cube)

    if (
        source.coord(axis="x").is_contiguous()
        and not cube.coord(axis="x").is_contiguous()
    ):
        # iris area weighted regridding amongst other things require
        # 'contiguous bounds' which are not wraparound.  Raise a warning here
        # to make it obvious to the user where their coordinate became
        # discontiguous.
        warnings.warn(
            "Unable to perform extraction and maintain contiguous " "coordinates."
        )

    return cube


class ExtractConstraint(iris.Constraint):
    def __init__(self, target, fix_period=False, pad_width=1):
        """
        Area overlap extraction constraint.

        Parameters
        ----------
        target : :class:`~iris.cube.Cube`
            Target cube used to define the area overlap with the source.
        fix_period : :obj:`bool`, optional
            Ensure that the range of the returned cube in not altered.  This
            may result in discontiguous bounds if the extract returns two
            disconnected regions of the source.
        pad_width : :obj:`int`, optional
            Pad the slices by the specified number of cells.
            See :func:`utils.cube.get_slices`.

        """
        self._target = target
        self._fix_period = fix_period
        self._pad_width = pad_width

    def extract(self, source):
        """
        Extract the source region which covers the target domain.

        Parameters
        ----------
        source : :class:`~iris.cube.Cube`
            Source cube.

        Returns
        -------
        : :class:`~iris.cube.Cube`
            An Iris cube representing the sub-region of source which overlaps
            the area of the target.

        """
        return _extract_overlap(
            source, self._target, fix_period=self._fix_period, pad_width=self._pad_width
        )

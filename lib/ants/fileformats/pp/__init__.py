# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

"""
This module includes utility functions for working with PP files for
ancillary generation.

Loading PP data
---------------

The following additional functionality is provided on load by ANTS:

1. Pseudo-level order from the PP file is preserved.

"""
import collections
import itertools

import ants
import cf_units
import iris
import iris.fileformats.pp as ipp
import numpy as np

RMDI = -1.073741824e9


class _CallbackPP(object):
    """
    Callback to preserve pseudo level order.

    Returns a callable object used as a callback when loading pp files.

    Parameters
    ----------
    user_callback : function(cube, field, filename), optional
        Additional callback function to be run after this callback.

    See Also
    --------
    :meth:`_Callback.__call__`
    :func:`iris.io.run_callback`

    """

    def __init__(self):
        self._index = 0
        self._mapping = {}
        self._user_callback = None

    def __call__(self, cube, field, filename):
        """
        ANTS callback to maintain pseudo level order.

        Used as a callback when loading pp files for all ants.io.load
        operations (e.g. :func:`~ants.io.load.load`, :func:`~ants.io.load.load_cube`
        etc).

        Parameters
        ----------
        cube : :class:`iris.cube.Cube`
            The cube generated from the field.
        field: ppfield
            Not used in this implementation, but kept for consistency
            with the iris load callback protocol.
        filename: str
            The name of the ancillary file.

        """
        if len(cube.coords("pseudo_level")) > 0:
            self._freeze_pseudo_level(cube)
        if self._user_callback is not None:
            self._user_callback(cube, field, filename)

    def _freeze_pseudo_level(self, cube):
        """
        Add pseudo-level ordering coordinate.

        All scalar coordinates are converted to aux coords and an additional
        scalar dim coord representing pseudo-level order is added to ensure
        that pseudo level order from the fields file is maintained after all
        fields are loaded.

        Parameters
        ----------
        cube : :class:`iris.cube.Cube`
            The cube containing a pseudo level coordinate to be fixed.

        """
        self._demote_scalar_dim_coords(cube)
        pseudo_level_coord = cube.coord("pseudo_level")
        _order = self._get_order(pseudo_level_coord.points[0])
        cube.add_aux_coord(
            iris.coords.DimCoord(_order, long_name="_pseudo_level_order")
        )

    def _demote_scalar_dim_coords(self, cube):
        for dim_coord in cube.coords(dim_coords=True):
            if len(dim_coord.points) == 1:
                aux_coord = iris.coords.AuxCoord.from_coord(dim_coord)
                cube.remove_coord(dim_coord)
                cube.add_aux_coord(aux_coord)

    def _get_order(self, value):
        _order = self._mapping.get(value, None)
        if _order is None:
            self._index += 1
            self._mapping[value] = self._index
            _order = self._index
        return _order

    def append_user_callback(self, callback):
        self._user_callback = callback


def field_filter_strict(*args, **kwargs):
    """
    Return the sole field matching the given stash code.

    Arguments are passed straight to :func:`field_filter`.

    Returns
    -------
    :class:`iris.fileformats.pp.PPField`
        Single field with requested stash code.

    Raises
    ------
    RuntimeError
       if more than one field has the given stash code.

    See Also
    --------
    :func:`field_filter`

    """

    fields = field_filter(*args, **kwargs)
    if fields in [None, []]:
        raise RuntimeError("No fields found matching the filter parameters")
    if len(fields) > 1:
        raise RuntimeError(
            "More than one field matches the desired filter " "parameters"
        )
    return fields[0]


def field_filter(fields, stash):
    """
    Return only those fields with the given stash code.

    Parameters
    ----------
    fields : iterator of :class:`iris.fileformats.pp.PPField`
        Fields to filter.
    stash : :class:`iris.fileformats.pp.STASH`
        Stash code to filter on.

    Returns
    -------
    :class:`iris.fileformats.pp.PPField`
       List of fields with requested stash code.

    Notes
    -----

        The model identifier is ignored in the comparison when it has a value
        of 0.  This is due to the commonly missing model identifier in
        existing fields.

    """
    try:
        fields = list(fields)
    except TypeError:
        fields = [fields]

    # Note that some fields have an invalid model identifier '0' so we allow
    # these fields.
    try:
        fields = [
            field
            for field in fields
            if field.lbuser[3] == ((stash.section * 1000) + stash.item)
            and field.lbuser[6] in (stash.model, 0)
        ]
    except AttributeError:
        msg = "Type {} is not a recognised valid field type"
        raise TypeError(msg.format(type(fields[0])))
    return fields


def _iris_workarounds(cube, field, field_index):
    x_coord = cube.coord(axis="x")

    # Set LBLEV to model level number rather than 0 for depth fields when an
    # absolute depth coordinate and bounds have been provided.
    # See https://github.com/SciTools/iris/issues/4082.
    try:
        z_coord = cube.coord("depth")
        number_of_depth_levels = len(z_coord.points)

        if field.lblev == 0:
            field.lblev = (field_index % number_of_depth_levels) + 1
    except iris.exceptions.CoordinateNotFoundError:
        pass

    # Set LBLEV to 9999 for surface fields, rather than 0 as currently
    # set in iris. See https://github.com/SciTools/iris/issues/3820
    if field.lblev == 0:
        field.lblev = 9999

    # Override lbnpt bdx as iris does not support cubes with zonal
    # mean.  See https://github.com/SciTools/iris/issues/2054
    if field.lbnpt == 0:
        field.lbnpt = len(x_coord.points)
    if field.bdy != RMDI and field.bdx == 0.0:
        field.bdx = 360.0

    # Overide bplon as iris doesn not support properly support unrotated pp
    # LAMs.  See https://github.com/SciTools/iris/issues/3560
    if not ants.utils.cube.is_global(cube):
        if x_coord.coord_system == ants.coord_systems.UM_SPHERE.crs:
            field.bplon = 180


def cube2pp(cube, field_coords=None):
    """
    Generates pp fields from a cube.

    This is a wrapper around :func:`iris.fileformats.pp.as_fields`.  In
    addition to that function, this ensures the horizontal coordinates are
    defined in the directions anticipated by the UM, identifies logical data,
    and applies fixes required for zonal mean data.

    Parameters
    ----------
    cube : :class:`iris.cube.Cube`
        Cube to convert into pp fields.
    field_coords : list of 2 :class:`iris.coords.Coord` instances or list of \
                   2 str coordinate names, optional.
        The coordinates to use to reduce the cube into 2D slices.  Passed
        directly to :func:`iris.fileformats.pp.as_fields`.  If not provided,
        this is automatically determined from the cube dimension coordinates
        if possible.

    Returns
    -------
    : list of :class:`iris.fileformats.pp.PPField`
        The fields generated from the cube.  Note that due to processing
        requirements, this is a list, rather than the generator returned by
        :func:`iris.fileformats.pp.as_fields`.

    Raises
    ------
    RuntimeError
       If the cube has more than time based coordinate.
    ValueError
       If the cube has a time coordinate with a year of zero.
    ValueError
       If the cube has contradictory valid_range and valid_min/valid_max
       attributes.

    """
    # Ensure a south-north definition - required by the UM
    x_coord, y_coord = ants.utils.cube.horizontal_grid(cube)
    if y_coord.points[-1] < y_coord.points[0] and isinstance(
        y_coord, iris.coords.DimCoord
    ):
        # Ensure that we do not invert the original - restrict this
        # transformation to the ancillary output.
        cube = cube.copy(cube.lazy_data())
        cube = ants.utils.cube.reverse_coordinate(cube, y_coord)
    # TODO: Iris ignores proleptic_gregorian calendar time coordinates...
    # https://github.com/SciTools/iris/issues/3561
    time_coords = ants.utils.cube.find_time_coordinates(cube)
    if len(time_coords) == 1:
        if time_coords[0].units.calendar in [
            "proleptic_gregorian",
            "standard",
            "360_day",
        ]:
            units = time_coords[0].units.cftime_unit
            datetime = units.split("since")[1]
            year = datetime.split("-")[0]
            if int(year) == 0:
                raise ValueError(
                    "\nZero not allowed as a reference year.\n"
                    "Ensure that dates are representative of the data.\n"
                    "See https://metoffice.github.io/ANTS/\n"
                    "appendixA_time_handling.html#date-information"
                )
            if cube.coord("time").units.calendar in ["proleptic_gregorian"]:
                cube = cube.copy(cube.lazy_data())
                time_coord = cube.coord("time")
                new_units = cf_units.Unit(time_coord.units.name, calendar="standard")
                time_coord.units = new_units
    elif len(time_coords) > 1:
        msg = "More than one time based coordinate: {}"
        time_coord_names = []
        for coord in time_coords:
            time_coord_names.append(coord.name())
        raise RuntimeError(msg.format(time_coord_names))

    if field_coords is None:
        field_coords = [y_coord, x_coord]
    try:
        fields = list(ipp.as_fields(cube, field_coords))
    except ValueError as err:
        iris_msg = (
            "zero not allowed as a reference year, does not exist in "
            "Julian or Gregorian calendars"
        )
        err_msg = list(err.args)
        if iris_msg in list(err.args):
            msg = (
                "\nEnsure that dates are representative of the data. See "
                "https://metoffice.github.io/ANTS/"
                "appendixA_time_handling.html#date-information"
            )
            err_msg[0] += msg
            err.args = err_msg
        raise

    # Determine whether the cube represents logical data even if not a boolean
    # dtype.
    # http://www.unidata.ucar.edu/software/netcdf/docs/
    # attribute_conventions.html
    logical_field = 0
    dtype_kind = cube.lazy_data().dtype.kind
    if dtype_kind in ["i", "u"]:
        valid_range = []
        valid_range.append(cube.attributes.get("valid_range"))
        valid_range.append(
            [cube.attributes.get("valid_min"), cube.attributes.get("valid_max")]
        )
        valid_range = [x for x in valid_range if x is not None]
        valid_range = [x for x in valid_range if None not in x]
        for vrange in valid_range:
            if np.allclose([0, 1], vrange):
                logical_field += 1

        if logical_field > 0 and len(valid_range) != logical_field:
            msg = (
                "Cube attribute valid range is overspecified and "
                "contradictory. valid_range:{}, valid_min, valid_max: {}"
            )
            raise ValueError(msg.format(valid_range[0], valid_range[1]))

    for field_index, field in enumerate(fields):
        _iris_workarounds(cube, field, field_index)
        if logical_field > 0:
            field.lbuser[0] = 3
        else:
            # Populate lbuser0 now as iris only populates on save so that the
            # field becomes more self contained.
            field.lbuser[0] = {"b": 3, "u": 2, "i": 2, "f": 1}[dtype_kind]
    return fields


def _sorted_ppfields(cubes):
    """
    Converts a Cubelist into a list of fields in the expected order.

    The field order is defined as:

    for month in month_list:
       for STASH in STASH_list:
           for level in level_pseudolevel_list:
               for zlevel in z_level_list:
                    write out field

    where the level_pseudolevel_list and STASH_list are orders in which the
    pseudo levels, and STASH codes are first encountered in the cubes, while
    the month list and the z_level_list is ascending order of time or model
    level number.

    Parameters
    ----------
    cubes : :class:`iris.cube.CubeList`
        Cube to convert into pp fields.

    Returns
    -------
    : list of :class:`iris.fileformats.pp.PPField`
        The fields generated from the cube in the required order for
        ancillaries.

    Raises
    ------
    KeyError
        If one or more of the cubes in the cubelist does not have a STASH code.
    ValueError
        If the cubes do not have identical pseudolevel coordinates.

    See Also
    --------
    http://fcm2/projects/UM/ticket/4612

    """

    def get_stash_order(cubes):
        stash_order = []
        for cube in cubes:
            try:
                stash_order.append(cube.attributes["STASH"])
            except KeyError:
                raise ValueError(
                    "Cube {} does not have a stash code".format(cube.name())
                )
        return stash_order

    def sort_keys(ppfield):
        return int_time(ppfield.t1), stash_order.index(ppfield.stash), ppfield.blev

    def int_time(time):
        try:
            # Converts a time of "1-02-03 04:05:06" to 10203040506
            result = int(time.strftime("%Y%m%d%H%M%S").strip())
        except ValueError:
            # To cover cases where no time value needs to be provided.
            # If the cftime strftime attempts to format a time of 0
            # (i.e. no time information), this creates a string of 0000-00-00,
            # which is invalid for the cftime api. It requires a valid calendar
            # based date, e.g. 0000-01-01 for year 0, day 1, month 1.
            # In this case, we want to show that no time information has been
            # provided, so return the original 0 for the time field.
            result = 0
        return result

    ppfields = []
    stash_order = get_stash_order(cubes)

    for cube in cubes:
        if not isinstance(cube.attributes["STASH"], ipp.STASH):
            cube.attributes["STASH"] = ipp.STASH.from_msi(cube.attributes["STASH"])
        ppfields.extend(cube2pp(cube))

    ppfields = sorted(ppfields, key=sort_keys)
    return ppfields


def _add_callback(callback, *args, **kwargs):
    """
    Adds both the ants callback and the user provided callback (if any) to the
    load.

    """
    args = list(args)
    if len(args) == 1:
        args += [callback]
    else:
        callback.append_user_callback(args[1])
        args[1] = callback
    args = tuple(args)
    return args, kwargs


def load_cubes(*args, **kwargs):
    """
    Loads cubes from a list of pp filenames.

    This function acts as a wrapper to :func:`iris.fileformats.pp.load_cubes`.

    See Also
    --------
    :func:`iris.fileformats.pp.load_cubes`

    """
    args, kwargs = _add_callback(_CallbackPP(), *args, **kwargs)
    return iris.fileformats.pp.load_cubes(*args, **kwargs)


def load_cubes_little_endian(*args, **kwargs):
    """
    Loads cubes from a list of pp filenames.

    This function acts as a wrapper to :func:`iris.fileformats.pp.load_cubes`.

    See Also
    --------
    :func:`iris.fileformats.pp.load_cubes`

    """
    args, kwargs = _add_callback(_CallbackPP(), *args, **kwargs)
    return iris.fileformats.pp.load_cubes_little_endian(*args, **kwargs)


def pp2cubes(fields):
    """
    Convert ppfields to cube(s).

    Parameters
    ----------
    fields : :class:`iris.fileformats.pp.PPField`
       A single pp field or an iterator of pp fields to convert to one or more
       cubes.

    Returns
    -------
    :class:`iris.cube.CubeList`
        The cubes derived from the pp fields.

    Notes
    -----
    At time of writing there was no iris implementation of this function.
    This implementation will be retired when the iris implementation is
    complete.

    """
    if not isinstance(fields, collections.abc.Iterable):
        fields = [fields]
    cube_field_pairs = iris.fileformats.pp.load_pairs_from_fields(fields)
    cubes = iris.cube.CubeList(
        [cube_field_pair[0] for cube_field_pair in cube_field_pairs]
    ).merge()
    ants.utils.cube.guess_horizontal_bounds(cubes)
    return cubes


def load_ppfields(*args, **kwargs):
    """
    Read PPFields from on or more files.

    Parameters
    ----------
    filenames : str or ~collections.abc.Iterable of str
        One or more filenames to load.

    Returns
    -------
    ~collections.abc.Iterator
      The pp fields from all files read.


    Notes
    -----

    This function differs from :func:`iris.fileformats.pp.load` by supporting multiple
    file names on input.

    """
    args = list(args)
    filenames = args.pop(0)
    if isinstance(filenames, str):
        filenames = [filenames]

    return itertools.chain.from_iterable(
        (ipp.load(fnme, *args, **kwargs) for fnme in filenames)
    )

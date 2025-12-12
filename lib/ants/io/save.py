# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
This module contains code used to save cubes.

###########
Saving data
###########

Like loading, ANTS save adds extra file format dependent capability over
the base iris save.  Saving the cube to NetCDF uses
:func:`ants.io.save.netcdf`.  Saving to an F03 UM ancillary file
(using ``saver='ancil'``) uses :func:`ants.io.save.ancil`.
NetCDF is easier to use for verification and
diagnostic purposes, while the fields file is currently needed for the UM.

Additionally, ANTS has support for 'ukca' flavoured NetCDF, chosen by
specifying ``saver='ukca'`` (see :func:`ants.io.save.ukca_netcdf`).

"""
import os
import sys
import warnings
from datetime import datetime

import ants.utils.cube
import iris
from ants.fileformats.ancil import _cubes_to_ancilfile, _mule_set_lbuser2
from ants.fileformats.netcdf.cf import (
    _coerce_netcdf_classic_dtypes,
    _iris_dask_chunking_workaround,
)
from ants.fileformats.netcdf.ukca import LOCAL_ATTS, _ukca_conventions


def ancil(cubes, filename):
    """
    Save one or more cubes to a F03 UM ancillary file.

    UM documentation paper `UM input and output file formats (F03)
    <https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf>`_
    defines the ancillary file format.

    Every provided cube must have a STASH code attribute defined.

    The fields are written to the output file in this order::

        for time in time_list:
            for STASH in STASH_list:
                for level in level_list:
                    <write out field>

    The ``time_list`` is sorted into ascending order.

    The ``STASH_list`` is sorted into the order in which the STASH codes are
    first found in the cubes being passed into this function.  If your use
    case requires fields with a particular STASH order, sort the cubes into
    that order prior to calling the save.

    The ``level_list`` is either pseudo levels or model level numbers.
    The behaviour depends on the kind: model level numbers are sorted
    into ascending order like times, while pseudo levels are sorted in
    the order first found in the cubes, like STASH codes.

    Saving cubes with both pseudo levels and model level numbers is not
    supported.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube` or :class:`iris.cube.CubeList`
        One or more cubes to be saved.
    filename : str
        The name of the F03 UM ancillary file, including any extension.

    Notes
    -----
    To save a cube as a fields file, it must have a grid staggering set.
    To set the grid staggering manually you can use the grid_staggering
    attribute. For example, to set an ENDGame grid staggering::

        cube.attributes['grid_staggering'] = 6

    See UM doc F03 for suitable grid staggering values. Some metadata is
    set so applications apart from the UM can read the ancillary. This
    includes:

    * XCONV - integer_constants(3) is set to 1 if there's no valid value for it
    """
    if filename.endswith(".nc"):
        raise ValueError("F03 UM ancillary files cannot be saved with a .nc extension.")

    cubes = ants.utils.cube.as_cubelist(cubes)
    ancilfile = _cubes_to_ancilfile(cubes)
    _mule_set_lbuser2(ancilfile)
    ancilfile.to_file(filename)


def netcdf(
    cubes,
    filename,
    netcdf_format="NETCDF4_CLASSIC",
    local_keys=None,
    unlimited_dimensions=None,
    zlib=False,
    complevel=4,
    fill_value=None,
    update_history=True,
    history_message=None,
):
    """
    Save one or more cubes to a netCDF file.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube` or :class:`iris.cube.CubeList`
        One or more cubes to be saved.
    filename : str
        The name of the netCDF file. If the .nc extension is missing then it
        it will be added to enforce CF compliance.
    netcdf_format : str
        Underlying netCDF file format, one of ``NETCDF4``,
        ``NETCDF4_CLASSIC``, ``NETCDF3_CLASSIC`` or ``NETCDF3_64BIT``.
        Default is ``NETCDF4_CLASSIC`` format.
    local_keys : ~collections.abc.Iterable of str
        Cube attribute keys. Any cube attributes with matching keys will
        become attributes on the data variable rather than global
        attributes.
    unlimited_dimensions : :class:`~collections.abc.Iterable` of :obj:`str` \
        and/or :class:`iris.coords.Coord`
        Coordinate dimensions of ``cube`` to save with the netCDF
        dimension variable length ``UNLIMITED``. By default there are no
        dimensions assigned with length ``UNLIMITED``.
    zlib : bool
        If True, the data will be compressed in the netCDF file using
        gzip compression (default False).
    complevel : int
        An integer between 1 and 9 describing the level of compression
        desired (default 4). Ignored if ``zlib`` is False.
    fill_value : ~numbers.Number or list
        The value to use for the ``_FillValue`` attribute on the netCDF
        variable. If this argument is a list it must have the same
        number of elements as ``cubes`` if ``cubes`` is a
        :class:`iris.cube.CubeList`, or a single element, and each
        element of this argument will be applied to each cube
        separately.
    update_history : bool
        If True, the ``history`` attribute will be updated with the
        timestamped command line arguments (default True).
    history_message : str
        The message to use instead of the command line arguments when
        updating the ``history`` attribute. This argument will only be
        used if ``update_history`` is set to True.

    Notes
    -----
    If the cubes being saved have lazy data, this saver has two
    potential side effects:

    1. The data of any cubes with a datatype ``int64`` and being saved
       as ``NETCDF4_CLASSIC`` are realised.
    2. The data for each cube is rechunked such that the innermost
       dimension is a single chunk. This can be disabled via
       configuration, see ``ants_tuning`` in
       :class:`ants.config.GlobalConfiguration`.

    See also
    --------
    :func:`iris.save`
    """
    if not filename.endswith(".nc"):
        filename = f"{filename}.nc"

    if history_message is not None and not update_history:
        warnings.warn(
            "The message specified by 'history_message' will not be used as "
            "'update_history' is False"
        )

    if netcdf_format == "NETCDF4_CLASSIC":
        _coerce_netcdf_classic_dtypes(cubes)

    _iris_dask_chunking_workaround(cubes)

    if update_history:
        if history_message is not None:
            for cube in cubes:
                ants.utils.cube.update_history(cube, history_message)
        else:
            _update_history_cmd(cubes)

    iris.save(
        cubes,
        filename,
        saver="nc",
        netcdf_format=netcdf_format,
        local_keys=local_keys,
        unlimited_dimensions=unlimited_dimensions,
        zlib=zlib,
        complevel=complevel,
        fill_value=fill_value,
    )


def ukca_netcdf(
    cubes,
    filename,
    netcdf_format="NETCDF4_CLASSIC",
    local_keys=None,
    unlimited_dimensions=None,
    update_history=True,
):
    """
    Save one or more cubes to a UKCA-specific netCDF file.

    The following represents applied UKCA specification or standard UKCA
    netCDF setup:

    - Compression used: ``zlib`` with ``complevel=4``.
    - Ensure that specific attributes are local (see
      :obj:`ants.fileformats.netcdf.ukca.LOCAL_ATTS`).
    - Bounds are present (guessed where not).
    - Data types are made either 32-bit integer or 32-bit float.
    - Masked data is filled with zeros (a warning is issued where this
      happens).
    - Old UKCA conventions present are updated:

      - Replace ``emission_type`` with ``update_type``.
      - All UKCA numeric attributes are converted to 32-bit integers.
        These include ``update_type``, ``update_freq_in_hours``,
        ``lowest_level`` and ``highest_level``.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube` or :class:`iris.cube.CubeList`
        One or more cubes to be saved.
    filename : str
        The name of the UKCA-specific netCDF file, including the
        extension.
    netcdf_format : str
        Underlying netCDF file format, one of ``NETCDF4``,
        ``NETCDF4_CLASSIC``, ``NETCDF3_CLASSIC`` or ``NETCDF3_64BIT``.
        Default is ``NETCDF4_CLASSIC`` format.
    local_keys : ~collections.abc.Iterable of str
        Cube attribute keys. Any cube attributes with matching keys will
        become attributes on the data variable rather than global
        attributes.
    unlimited_dimensions : :class:`~collections.abc.Iterable` of :obj:`str` \
        and/or :class:`iris.coords.Coord`
        Coordinate dimensions of ``cube`` to save with the netCDF
        dimension variable length ``UNLIMITED``. By default there are no
        dimensions assigned with length ``UNLIMITED``.
    update_history : bool
        If True, the ``history`` attribute will be updated with the
        timestamped command line arguments (default True).

    See also
    --------
    :func:`ants.io.save.netcdf`
    """
    if local_keys is None:
        local_keys = LOCAL_ATTS
    else:
        local_keys = set(list(local_keys) + LOCAL_ATTS)
    zlib = True
    complevel = 4

    ants.utils.cube.guess_horizontal_bounds(cubes)
    _ukca_conventions(cubes)
    netcdf(
        cubes,
        filename,
        netcdf_format=netcdf_format,
        local_keys=local_keys,
        unlimited_dimensions=unlimited_dimensions,
        zlib=zlib,
        complevel=complevel,
        update_history=update_history,
    )


def _update_history_cmd(cube):
    """
    Update the cube history attribute with timestamped commandline arguments.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube` or :class:`iris.cube.CubeList`
        One or more cubes to be saved.

    See Also
    --------
    :func:`update_history`

    """
    metadata = ants.config.CONFIG["ants_metadata"]["history"]
    date = datetime.today().replace(microsecond=0)
    cubes = ants.utils.cube.as_cubelist(cube)

    # In some cases it may be desireable to combine data from different processing
    # chains, so we need to combine the history attributes so they are the same for
    # all cubes being saved.
    combine_histories = False

    for cc in cubes:
        if cc.attributes.get("history") != cubes[0].attributes.get("history"):
            combine_histories = True
            break

    # Construct a new combined history if needed and update all cubes to use that
    combined_history = []
    if combine_histories:
        for cc in cubes:
            combined_history.append(cc.attributes["history"])
        combined_history = "\n".join(combined_history)
        for cc in cubes:
            cc.attributes["history"] = combined_history

    for cc in cubes:
        items = sys.argv[:]
        items[0] = os.path.basename(items[0])
        items.append("({})".format(metadata)) if metadata else None
        ants.utils.cube.update_history(cc, " ".join(items), date)

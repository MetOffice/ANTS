# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
####################
Loading Target grids
####################

The ANTS library provides a grid loading capability via
:func:`ants.io.load.load_grid`.  This function will return an iris cube that can be
used to define the target grid for processing.  The cube can have a constant
data field or a land sea mask depending on the data source.

Grid loading supports the following formats:

1. Ancillary (CAP) compliant Fortran Namelist grid definition files (further
   information can be found at :func:`ants.io.load.load_grid`).
   Use this format in applications that do not need to use the land sea mask
   of the target field as part of their processing.
2. Any fileformat that can be interpreted by iris.
   Use this format to read a grid with a land sea mask.

############
Loading data
############

ANTS uses iris to load common fileformats and therefore has access to all
formats that are supported by iris.

In most cases you should, however, use :func:`ants.io.load`,
:func:`ants.io.load.load_cube` etc. to load data as cubes from files.
These ANTS functions perform additional processing on the input
data.  They will attempt to:

1. Derive the global/regional status of the input data and
   set the metadata on the cube accordingly.
2. Guess bounds of latitude and longitude for any sources without
   horizontal grid bounds.
3. Remove any forecast_reference_time and forecast_period coordinates.

The ANTS functions add extra capability, depending on the fileformat, over the
base iris functions.  You should read the documentation for the ANTS module
for the specific fileformat being used, for example
:mod:`ants.fileformats.ancil` for ancillary fields file loading.

See Also
--------
:func:`ants.fileformats.ancil.load_cubes`,
:func:`ants.fileformats.ancil.load_cubes_32bit_ieee`,
:func:`ants.fileformats.raster.load_cubes`,
:func:`ants.fileformats.pp.load_cubes`,
:func:`ants.fileformats.pp.load_cubes_little_endian`,
:func:`ants.fileformats.namelist.load_cap_horizontal`,
:func:`ants.fileformats.namelist.load_um_vertical`

"""
import copy
import glob
import warnings
from contextlib import contextmanager
from functools import wraps

import ants.utils
import iris
import iris.fileformats
import iris.io
import numpy as np
from ants.fileformats import _grid_extract, ancil, namelist, pp, raster
from ants.fileformats.raster import gdal


class _GdalIdentify(iris.io.format_picker.FileElement):
    """A :class:`FileElement` that queries 'gdalinfo' for the file."""

    def get_element(self, basename, file_handle):
        result = False
        if gdal is not None:
            result = True
            gdal.UseExceptions()
            try:
                gdal.Open(file_handle.name)
            except RuntimeError as err:
                if "not recognized as a supported file format" in err.args[0]:
                    result = False
        return result


XUM_FIELDSFILE_PRE_V3_1 = iris.fileformats.FormatSpecification(
    "xUM Fieldsfile (FF) pre v3.1",
    iris.fileformats.MagicNumber(8),
    0x000000000000000F,
    ancil.load_cubes,
    priority=6,
    constraint_aware_handler=True,
)


XUM_FIELDSFILE_POST_V5_2 = iris.fileformats.FormatSpecification(
    "xUM Fieldsfile (FF) post v5.2",
    iris.fileformats.MagicNumber(8),
    0x0000000000000014,
    ancil.load_cubes,
    priority=5,
    constraint_aware_handler=True,
)

XUM_FIELDSFILE_ANCILLARY = iris.fileformats.FormatSpecification(
    "xUM Fieldsfile (FF) ancillary",
    iris.fileformats.MagicNumber(8),
    0xFFFFFFFFFFFF8000,
    ancil.load_cubes,
    priority=4,
    constraint_aware_handler=True,
)


XUM_FIELDSFILE_CONVERTED_WITH_IEEE_TO_32_BIT = iris.fileformats.FormatSpecification(
    "xUM Fieldsfile (FF) converted " "with ieee to 32 bit",
    iris.fileformats.MagicNumber(4),
    0x00000014,
    ancil.load_cubes_32bit_ieee,
    priority=4,
    constraint_aware_handler=True,
)

XUM_FIELDSFILE_ANCILLARY_CONVERTED_WITH_IEEE_TO_32_BIT = (
    iris.fileformats.FormatSpecification(
        "xUM Fieldsfile (FF) ancillary " "converted with ieee to 32 bit",
        iris.fileformats.MagicNumber(4),
        0xFFFF8000,
        ancil.load_cubes_32bit_ieee,
        priority=4,
        constraint_aware_handler=True,
    )
)

GDAL = iris.fileformats.FormatSpecification(
    "gdal",
    _GdalIdentify(),
    True,
    raster.load_cubes,
    priority=0,
    constraint_aware_handler=False,
)

UM_POST_PROCESSING = iris.fileformats.FormatSpecification(
    "UM Post Processing file (PP)",
    iris.fileformats.MagicNumber(4),
    0x00000100,
    pp.load_cubes,
    priority=6,
    constraint_aware_handler=True,
)


UM_POST_PROCESSING_LITTLE_ENDIAN = iris.fileformats.FormatSpecification(
    "UM Post Processing file (PP) little-endian",
    iris.fileformats.MagicNumber(4),
    0x00010000,
    pp.load_cubes_little_endian,
    priority=4,
    constraint_aware_handler=True,
)

HORIZONTAL_NAMELIST_FORMAT = iris.fileformats.FormatSpecification(
    "Namelist horizontal definition",
    iris.fileformats.LeadingLine(),
    lambda line: any([group in str(line).lower() for group in ["&horizgrid", "&grid"]]),
    namelist.load_cap_horizontal,
    priority=4,
    constraint_aware_handler=False,
)


NAMELIST_VERTICAL_DEFINITION = iris.fileformats.FormatSpecification(
    "Namelist vertical definition",
    iris.fileformats.LeadingLine(),
    lambda line: "&vertlevs" in str(line).lower(),
    namelist.load_um_vertical,
    priority=4,
    constraint_aware_handler=False,
)


@contextmanager
def ants_format_agent():
    """
    Customises iris.fileformats.FORMAT_AGENT for ants loading and reverts
    the FORMAT_AGENT once the loading is complete.
    """
    try:
        original_format_agent = copy.deepcopy(iris.fileformats.FORMAT_AGENT)
        # Replace the ancillary format agent with a customised (wrapped one).
        iris.fileformats.FORMAT_AGENT.add_spec(XUM_FIELDSFILE_PRE_V3_1)
        iris.fileformats.FORMAT_AGENT.add_spec(XUM_FIELDSFILE_POST_V5_2)
        iris.fileformats.FORMAT_AGENT.add_spec(XUM_FIELDSFILE_ANCILLARY)
        iris.fileformats.FORMAT_AGENT.add_spec(
            XUM_FIELDSFILE_CONVERTED_WITH_IEEE_TO_32_BIT
        )
        iris.fileformats.FORMAT_AGENT.add_spec(
            XUM_FIELDSFILE_ANCILLARY_CONVERTED_WITH_IEEE_TO_32_BIT
        )
        iris.fileformats.FORMAT_AGENT.add_spec(GDAL)
        iris.fileformats.FORMAT_AGENT.add_spec(UM_POST_PROCESSING)
        iris.fileformats.FORMAT_AGENT.add_spec(UM_POST_PROCESSING_LITTLE_ENDIAN)
        iris.fileformats.FORMAT_AGENT.add_spec(HORIZONTAL_NAMELIST_FORMAT)
        iris.fileformats.FORMAT_AGENT.add_spec(NAMELIST_VERTICAL_DEFINITION)
        yield
    finally:
        iris.fileformats.FORMAT_AGENT = original_format_agent


def load_landsea_mask(filename, land_threshold=None):
    """
    Load a landsea mask from either a landsea mask file or a landfraction file.

    Parameters
    ----------
    filename : str
        Landsea mask or landsea fraction filepath.
    land_threshold : :obj:`float`, optional
        Threshold for converting the land fraction field into a landsea mask
        field.  0.5 would mean that any fraction greater than this will be
        masked.  This argument is used when loading a land fraction field.

    Returns
    -------
    : :class:`iris.cube.Cube`
        Landsea mask cube.

    """
    try:
        # Is it a landsea mask field?
        lbm = ants.io.load.load_cube(
            filename, "land_binary_mask", ignore_metadata_files=True
        )
        lbm = lbm.copy(lbm.data.astype("bool", copy=False))
    except iris.exceptions.ConstraintMismatchError:
        try:
            # Is it a land fraction field?
            land_fraction = ants.io.load.load_cube(
                filename, "vegetation_area_fraction", ignore_metadata_files=True
            )
            lbm = land_fraction.copy(land_fraction.data > land_threshold)
            lbm.rename("land_binary_mask")
        except iris.exceptions.ConstraintMismatchError:
            # It looks like we are wanting to extract a landsea mask from some
            # other field.
            cube = ants.io.load.load(filename, ignore_metadata_files=True)[0]
            y = cube.coord(axis="y")
            x = cube.coord(axis="x")
            cube = cube.slices((y, x)).next()
            lbm = cube.copy(~np.ma.getmaskarray(cube.data))
    return lbm


def load_grid(filenames, *args, **kwargs):
    """
    Load a grid definition and return an iris cube.

    The purpose of this function is to load a single grid definition, without
    the data payload, from components derived from one or more file.  That is,
    to merge these components where possible to return a single grid
    definition.  Examples include the merging of a vertical definition with
    one defining the horizontal domain.  Surface altitude (orography) is also
    supported as a merge component.  A hybrid height coordinate will ensue.
    Where source datasets have conflicting components, an exception will be
    raised.  Where more than one source dataset has identical components, a
    single grid will still be returned.

    Parameters
    ----------
    filenames : str
        Pathname of a file, or a list of such paths that contain the grid
        definition.
    *args :
        See :func:`iris.load`
    **kwargs :
        See :func:`iris.load`

    Returns
    -------
    :class:`iris.cube.Cube`
        Cube representing the grid defined with no data disk dependence and
        negligible data memory usage (using dummy data).

    Raises
    ------
    ValueError
        Where we are unable to resolve a single grid due to a conflicting
        coordinate.
    iris.exceptions.ConstraintMismatchError
        Where no cubes have been found.

    """
    if isinstance(filenames, str):
        filenames = (filenames,)

    results = iris.cube.CubeList()

    # Use normal ants load for all regular files in one go.  This is needed
    # for variable resolution namelists - need both parts (regular and
    # variable namelists) in the namelist loader at the same time.
    if filenames:
        cubes = load(filenames, *args, **kwargs)
        if cubes:
            results.extend(cubes)

    # Remove dependence on disc for regular files.
    grid = None
    if results:
        grid = _grid_extract.extract_grid(results)
    if not grid:
        raise iris.exceptions.ConstraintMismatchError("no cubes found")
    return grid


def _customised_load(func):

    def _pseudo_level_order_removal(cube):
        # Discard '_pseudo_level_order' coord on load (an implementation detail
        # we want to hide from the user).
        # Ideally this code can be removed when we have official support from
        # iris.
        cubes = ants.utils.cube.as_cubelist(cube)
        for cube in cubes:
            try:
                cube.remove_coord("_pseudo_level_order")
            except iris.exceptions.CoordinateNotFoundError:
                pass

    def _forecast_coordinates_removal(cube):
        # Discard 'forecast_period' and 'forecast_reference_time' coords on
        # load.
        cubes = ants.utils.cube.as_cubelist(cube)
        coords = ("forecast_period", "forecast_reference_time")
        for cube in cubes:
            for coord in coords:
                try:
                    cube.remove_coord(coord)
                except iris.exceptions.CoordinateNotFoundError:
                    pass

    # Wrap the iris load function with our own set of behaviours.
    @wraps(func)
    def load_function(*args, **kwargs):
        # Ensure that we leave appropriate calling to the underlying iris load
        # function.

        # TODO https://github.com/MetOffice/ANTS/issues/91, remove warning filter
        # workaround when iris issue https://github.com/SciTools/iris/issues/5749 has
        # been fixed.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                "Ignoring a datum in netCDF load for consistency with existing "
                "behaviour. In a future version of Iris, this datum will be applied. "
                "To apply the datum when loading, use the "
                "iris.FUTURE.datum_support flag.",
                FutureWarning,
            )
            ignore_metadata_files = False
            if "ignore_metadata_files" in kwargs:
                ignore_metadata_files = kwargs.pop("ignore_metadata_files")
            if not ignore_metadata_files:
                # Do the handling for each way a user callback can be passed in through
                # iris
                user_callback = None
                if len(args) == 3:
                    user_callback = args[2]
                else:
                    if "callback" in kwargs:
                        user_callback = kwargs.pop("callback")
                args, kwargs = _add_callback(
                    _CallbackMetadata(user_callback), *args, **kwargs
                )
            # Use context manager to avoid permanently modifying iris behaviour.
            with ants_format_agent():
                cubes = func(*args, **kwargs)
        if cubes is not None:
            try:
                ants.utils.cube.derive_circular_status(cubes)
            except iris.exceptions.CoordinateNotFoundError:
                pass
            _pseudo_level_order_removal(cubes)
            _forecast_coordinates_removal(cubes)
        return cubes

    return load_function


def _add_callback(callback, *args, **kwargs):
    """
    Adds both the ants callback and the user provided callback (if any) to the
    load.
    """
    args = list(args)
    if len(args) == 1:
        kwargs["callback"] = callback
    elif len(args) == 3:
        args[2] = callback
    args = tuple(args)
    return args, kwargs


class _CallbackMetadata(object):
    """Callback for collecting metadata from sidecar files.

    This callback will load additional metadata files with the naming convention:
    filename.<metadata> and append the contents of those files to the cube
    attributes.
    """

    def __init__(self, user_callback):
        self._user_callback = user_callback

    def __call__(self, cube, field, filename):
        """
        The method that runs when iris runs the callback. Collects the filenames and
        will run the user callback
        """
        if type(filename) is list:
            filename = filename[0]
        metadata_filenames = "".join([filename, ".*"])
        metadata_files = glob.glob(metadata_filenames)
        if metadata_files != []:
            self._retrieve_metadata(metadata_files, cube)
        if self._user_callback is not None:
            self._user_callback(cube, field, filename)

    def _retrieve_metadata(self, metadata_files, cube):
        """
        Reads in the contents of each file and adds an attribute to the cube with the
        name of the file.

        Parameters
        ----------
        metadata_files: list
            The list of filenames that contain metadata for the cube.
        cube : :class:`iris.cube.Cube`
            The cube being loaded.

        """
        valid_metadata_names = ["license", "attribution", "restrictions"]
        other_license = ["lisense", "licence", "lisence"]
        for metadata_file in metadata_files:
            file_name_splits = str(metadata_file).split(".")
            attribute_name = file_name_splits[-1]
            if attribute_name in other_license:
                warnings.warn(
                    f"The attribute name {attribute_name} has been changed to "
                    "license, in line with ANTS working practices.",
                    category=UserWarning,
                )
                attribute_name = "license"
            if attribute_name not in valid_metadata_names:
                warnings.warn(
                    f"Attribute {attribute_name} is not a valid metadata file "
                    "name. Accepted metadata names are license, attribution "
                    "and restrictions.",
                    category=UserWarning,
                )
            else:
                if attribute_name in cube.attributes:
                    raise AttributeError(
                        f"The {attribute_name} is already an attribute on the "
                        "cube. To ignore metadata files, use the "
                        "--ignore-metadata-files flag."
                    )
                open_file = open(metadata_file, "r")
                metadata = open_file.readlines()
                open_file.close()
                cube.attributes[attribute_name] = metadata
                with open("written_license.txt", "a") as file:
                    file.write("".join(metadata))


def load_cube(*args, **kwargs):
    """
    Loads a single cube.

    Wraps :func:`iris.load_cube`. Different to the iris functionality, this will
    remove any forecast_reference_time and forecast_period coordinates. The order
    of pseudolevels will be preserved from the source file.

    Parameters
    ----------
    *args :
        See :func:`iris.load_cube`
    **kwargs :
        See :func:`iris.load_cube`

    Returns
    -------
        A :class:`~iris.cube.Cube`.
    """
    loading_function = _customised_load(iris.load_cube)
    return loading_function(*args, **kwargs)


def load(*args, **kwargs):
    """
    Loads any number of Cubes for each constraint.

    Wraps :func:`iris.load`. Different to the iris functionality, this will
    remove any forecast_reference_time and forecast_period coordinates. The order
    of pseudolevels will be preserved from the source file.


    Parameters
    ----------
    *args :
        See :func:`iris.load`
    **kwargs :
        See :func:`iris.load`

    Returns
    -------
        A :class:`~iris.cube.CubeList`.
    """
    loading_function = _customised_load(iris.load)
    return loading_function(*args, **kwargs)


def load_cubes(*args, **kwargs):
    """
    Loads exactly one Cube for each constraint.

    Wraps :func:`iris.load_cubes`. Different to the iris functionality, this will
    remove any forecast_reference_time and forecast_period coordinates. The order
    of pseudolevels will be preserved from the source file.


    Parameters
    ----------
    *args :
        See :func:`iris.load_cubes`
    **kwargs :
        See :func:`iris.load_cubes`

    Returns
    -------
        A :class:`~iris.cube.CubeList`.

    """
    loading_function = _customised_load(iris.load_cubes)
    return loading_function(*args, **kwargs)


def load_raw(*args, **kwargs):
    """
    Loads non-merged cubes.

    Wraps :func:`iris.load_raw`. Different to the iris functionality, this will
    remove any forecast_reference_time and forecast_period coordinates. The order
    of pseudolevels will be preserved from the source file.


    Parameters
    ----------
    *args :
        See :func:`iris.load_raw`
    **kwargs :
        See :func:`iris.load_raw`

    Returns
    -------
        A :class:`~iris.cube.CubeList`.
    """
    loading_function = _customised_load(iris.load_raw)
    return loading_function(*args, **kwargs)

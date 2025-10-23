# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

"""
This module supports saving cubes as UM ancillary files.

UM documentation paper `UM input and output file formats (F03)
<https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf>`_
defines the ancillary file format.

Loading ancillary data
----------------------

The following additional functionality is provided on load by ANTS,
independent of which load function is used:

1. Pseudo-level order from the fieldsfile is preserved.
2. Grid staggering is stored on the cube and made available via
   cube.attributes['grid_staggering'].

"""
import warnings

import ants
import iris

try:
    import mule
except ImportError as _mule_import_error:
    mule = None
    message = (
        f"Unable to import mule: {_mule_import_error}\nProceeding "
        "without capabilities provided by mule."
    )
    warnings.warn(message)
import numpy as np
from ants.fileformats import pp

from . import template

# Dev note: within this file, we have both pp field and mule field instances.
# Be careful with the indexing when accessing elements by index: pp field
# headers are indexed from 0 while one dimensional mule field headers
# (i.e. lookup headers) are indexed from 1.  Where possible, access the header
# elements by name rather than index.

IMDI = -32768  # As defined by UMDP F03 at UM version 13.9.
RMDI = -1073741824.0  # As defined by UMDP F03 at UM version 13.9.


class _CallbackUM(pp._CallbackPP):
    """Callback to preserve pseudo level order and grid staggering."""

    def __init__(self, grid_staggering):
        super(_CallbackUM, self).__init__()
        self.grid_staggering = grid_staggering

    def __call__(self, cube, field, filename):
        """
        ANTS callback to add grid staggering and maintain pseudo level order.

        Used as a callback when loading fields files for all ants.io.load
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
        cube.attributes["grid_staggering"] = self.grid_staggering[filename]
        super(_CallbackUM, self).__call__(cube, field, filename)


class _IrisPPFieldDataProvider(object):
    def __init__(self, ppfield):
        self.ppfield = ppfield

    def _data_array(self):
        # Data type conversions and mask handling
        data = self.ppfield.data
        if isinstance(data, np.ma.core.MaskedArray):
            data = data.filled(fill_value=RMDI)
        data = data.astype(
            {"f": ">f8", "u": ">i8", "b": ">i8", "i": ">i8"}[data.dtype.kind],
            copy=False,
        )
        return data


class _TripwireField3:
    """This class enables mule to be an optional import.

    Any attempt to instantiate this class will trigger a ValueError.  This
    means that we can import this package safely, but any attempt to use
    mule functionality will trigger an error.

    """

    def __init__(self, *args, **kwargs):
        raise ValueError(
            "Mule cannot be imported, but an attempt has been "
            "made to use mule functionality through the "
            "_Field3 class"
        )

def _get_Field3(mule):
    if mule:
        class _ActualField3(mule.Field3):
            """
            Provides conveniences for ancillary generation on top of the mule Field3.

            """

            _NUM_LOOKUP_INTS = mule.Field.NUM_LOOKUP_INTS
            _NUM_LOOKUP_REALS = mule.Field.NUM_LOOKUP_REALS

            @staticmethod
            def _get_headers_from_pp(ppfield):
                """
                Gets headers in a format suitable for use for generating a mule Field
                from the ppfield.


                Parameters
                ----------

                ppfield : :class:`iris.fileformats.pp.PPField`
                    The field from which to extract the headers.

                Returns
                -------

                : tuple(:class:`numpy.ndarray`, :class:`numpy.ndarray`)
                    First array is the int_headers and the second array is the real
                    headers

                """
                # Following pp.PPField.save we make sure the data is big-endian
                int_headers = np.empty(
                    shape=_ActualField3._NUM_LOOKUP_INTS,
                    dtype=np.dtype(">i%d" % mule._DEFAULT_WORD_SIZE),
                )
                int_headers.fill(IMDI)
                real_headers = np.empty(
                    shape=_ActualField3._NUM_LOOKUP_REALS,
                    dtype=np.dtype(">f%d" % mule._DEFAULT_WORD_SIZE),
                )
                real_headers.fill(RMDI)

                word_count = 0
                for name, word_no in ppfield.HEADER_DEFN:
                    ppfield_value = getattr(ppfield, name)
                    for sub_index, num in enumerate(word_no):
                        if len(word_no) > 1:
                            value = ppfield_value[sub_index]
                        else:
                            value = ppfield_value

                        # First sort out the integer headers
                        if word_count >= _ActualField3._NUM_LOOKUP_INTS:
                            word_count = 0

                        # Cast as special types include pp.SplittableInt and pp._LBProc
                        if num < _ActualField3._NUM_LOOKUP_INTS:
                            int_headers[word_count] = int(value)
                        else:
                            real_headers[word_count] = float(value)
                        word_count += 1
                return (int_headers, real_headers)

            @classmethod
            def from_pp(cls, ppfield):
                """
                Generates a mule Field3 from an iris PPField3.

                Data type conversion is done to ensure that the data is in the correct
                format for writing as an ancillary.  This also corrects the missing
                data indicator if needed.

                Parameters
                ----------
                ppfield: :class:`iris.fileformats.pp.PPField3`
                    The PP field from which to create a mule Field.

                Returns
                -------
                : :class:`mule.Field3`
                    The ppfield translated to a mule Field3.

                .. warning::

                    This is not lazy - i.e. if the data attached to the ppfield is
                    lazy, the conversion to a mule field will realise it.

                """

                # pp field with 64 word length header to ancillary field conversion.
                if not isinstance(ppfield, iris.fileformats.pp.PPField3):
                    raise TypeError(
                        "pp header version not supported for ancillary " "field generation."
                    )

                int_headers, real_headers = cls._get_headers_from_pp(ppfield)

                # Ensure consistent RMDI across all fields
                if ppfield.bmdi != RMDI:
                    bmdi_offset = [
                        offset[0] for (name, offset) in ppfield.HEADER_DEFN if name == "bmdi"
                    ][0]
                    bmdi_ind = bmdi_offset - _ActualField3._NUM_LOOKUP_INTS
                    real_headers[bmdi_ind] = RMDI

                # LBVC - should always be set (surface/model level).
                if ppfield.lbvc == 0:
                    int_headers[25] = 129

                field = cls(
                    int_headers=int_headers,
                    real_headers=real_headers,
                    data_provider=_IrisPPFieldDataProvider(ppfield),
                )

                field.x = field.y = None
                if getattr(ppfield, "x", None) is not None:
                    field.bdx = field.bzx = RMDI
                    field.x = ppfield.x
                if getattr(ppfield, "y", None) is not None:
                    field.bdy = field.bzy = RMDI
                    field.y = ppfield.y

                return field

            @property
            def is_regular(self):
                """
                Determine whether the field has regular x or y.

                Returns
                -------
                : tuple of bool
                    Regularity of the dimensions in the order (x, y).

                """
                if not hasattr(self, "x"):
                    self.x = None
                if not hasattr(self, "y"):
                    self.y = None
                return (self.x is None, self.y is None)

            @property
            def is_rotated(self):
                """
                Returns
                -------
                : bool
                    True if the pp header lbcode.ix is 1

                """
                try:
                    ix = int(str(self.lbcode)[-3])
                    res = ix == 1
                except IndexError:
                    res = False
                return res

        _Field3 = _ActualField3
    else:
        _Field3 = _TripwireField3
    return _Field3


_Field3 = _get_Field3(mule)


def _cubes_to_ancilfile(cubes):
    """
    Converts iris cubes into headers and fields for saving with mule.

    Returns
    ----------
     : :class:`mule.AncilFile`
        AncilFile generated from the cubes.

    Parameters
    ----------

    cubes : :class:`iris.cube.Cube` or :class:`iris.cube.CubeList`
        Cubes from which to derive the information necessary for creating an
        ancillary.

    Raises
    ------

    RuntimeError
        If a cube with an unsupported coordinate is used.

    """

    def _reject_unsupported_coords(cubes):
        # Some coordinates we reject in all circumstances:
        unsupported = [
            "level_pressure",
        ]
        for cube in cubes:
            rejected = [c.name() for c in cube.coords() if c.name() in unsupported]
            if rejected:
                msg = (
                    "Coordinates {!s} are presently unsupported for "
                    "saving as F03 ancillary files."
                ).format(sorted(rejected))
                raise RuntimeError(msg)
        # For depths, we only support the case where depth has a "positive:
        # down" attribute at this time:
        depth_coords = [coord for coord in cube.coords() if "depth" in coord.name()]
        if len(depth_coords) > 0:
            for coord in depth_coords:
                attributes = coord.attributes
                if "positive" not in attributes or attributes["positive"] != "down":
                    msg = (
                        'Unsupported depth coordinate "{}".  Currently, '
                        'only depths with the "positive" attribute defined '
                        'as "down" are supported.'
                    ).format(coord.name())
                    raise ValueError(msg)

    cubes = ants.utils.cube.as_cubelist(cubes)
    _reject_unsupported_coords(cubes)
    ants.utils.cube.derive_circular_status(cubes)
    # _ppfields guaranteed to be a list due to sort, but could be either lazy
    # or realised data
    _ppfields = pp._sorted_ppfields(cubes)
    _reference_field = _Field3.from_pp(_ppfields[0])
    # But _Field3 is not lazy, so use a generator to avoid excessive memory
    # usage
    fields = (_Field3.from_pp(ppfield) for ppfield in _ppfields)
    _template = template.create(cubes, _reference_field)

    ancilfile = mule.AncilFile.from_template(_template)
    ancilfile.fields.extend(fields)

    return ancilfile


def _fetch_grid_staggering_from_file(filenames):
    """
    Fetch grid filename: staggering mapping.

    Parameters
    ----------
    filename: str or iterable of str
        The name of the ancillary file from which to fetch the grid staggering
        attribute.

    Returns
    -------
    : dict
        Mapping between filename and grid staggering.

    """
    mapping = {}
    for filename in filenames:
        ffv = mule.AncilFile.from_file(filename)
        mapping.update({filename: ffv.fixed_length_header.grid_staggering})
    return mapping


def load_cubes(*args, **kwargs):
    """
    Loads cubes from a list of fields files filenames.

    This function acts as a wrapper to :func:`iris.fileformats.um.load_cubes`.
    Adds grid staggering to the loaded data.

    See Also
    --------
    :func:`iris.fileformats.um.load_cubes`

    """
    grid_staggering = _fetch_grid_staggering_from_file(args[0])
    args, kwargs = pp._add_callback(_CallbackUM(grid_staggering), *args, **kwargs)
    return iris.fileformats.um.load_cubes(*args, **kwargs)


def load_cubes_32bit_ieee(*args, **kwargs):
    """
    Loads cubes from a list of 32bit ieee converted fieldsfiles filenames.
    Adds grid staggering to the loaded data.

    See Also
    --------
    :func:`load_cubes` for keyword details

    """
    grid_staggering = _fetch_grid_staggering_from_file(args[0])
    args, kwargs = pp._add_callback(_CallbackUM(grid_staggering), *args, **kwargs)
    return iris.fileformats.um.load_cubes_32bit_ieee(*args, **kwargs)


def _mule_set_lbuser2(ancilfile):
    # Set lbuser2 as some downstream applications are dependent on it and mule
    # doesn't currently derive it for us.
    # https://code.metoffice.gov.uk/trac/um/ticket/4656
    # Size of the field in 64-bit words and adjusted for 512 word sector
    # boundary described by Steve Wardle.
    # Assumes that output is 64-bit and unpacked (something we enforce
    # anyway for our ancillaries).
    lbnrec = ancilfile.integer_constants.num_rows * ancilfile.integer_constants.num_cols
    lbnrec = lbnrec - (lbnrec % -512)
    for ind, field in enumerate(ancilfile.fields):
        field.lbnrec = lbnrec
        if ind == 0:
            field.lbuser2 = 1
            continue
        prev_field = ancilfile.fields[ind - 1]
        field.lbuser2 = prev_field.lbnrec + prev_field.lbuser2

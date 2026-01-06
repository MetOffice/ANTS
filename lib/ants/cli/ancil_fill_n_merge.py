#!/usr/bin/env python
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Ancillary fill and merge application
************************************

This application fulfils two requirements: to merge datasets and to fill
missing values.

"""
import ants
import ants.io.save as save
import cartopy
from ants.utils.cube import create_time_constrained_cubes


def load_data(
    primary_source,
    alternate_source=None,
    validity_polygon_filepath=None,
    target_mask_filepath=None,
    land_fraction_threshold=None,
    begin=None,
    end=None,
    ignore_metadata_files=None
):
    """
    Load the necessary data for performing a merge and fill operation.

    Parameters
    ----------
    primary_source : str
        Primary source filepath.
    alternate_source : :obj:`str`, optional
        Alternate source filepath used when merging.
    validity_polygon_filepath : :obj:`str`, optional
        Filepath to the validity polygon which represents the data from the
        primary dataset which is valid.
    target_mask_filepath : :obj:`str`, optional
        Filepath to the target field mask.
    land_fraction_threshold : :obj:`str`, optional
    begin: :obj:`datetime`, optional
        Datetime to start the processing.
    end: :obj:`datetime`, optional
        Datetime to end the processing.


    Returns
    -------
    tuple
        The tuple contains the primary cube(s) (:class:`~iris.cube.CubeList`),
        alternate cube(s) (:class:`~iris.cube.CubeList`), validity polygon
        (:class:`shapely.Polygon`) and target mask (:class:`~iris.cube.Cube`)
        respectively.

    """
    primary_cubes = ants.io.load.load(
        primary_source, ignore_metadata_files=ignore_metadata_files
    )
    if begin is not None:
        primary_cubes = create_time_constrained_cubes(primary_cubes, begin, end)
    alternate_cubes = None
    if alternate_source:
        alternate_cubes = ants.io.load.load(
            alternate_source, ignore_metadata_files=ignore_metadata_files
        )
        if begin is not None:
            alternate_cubes = create_time_constrained_cubes(alternate_cubes, begin, end)

    rpolygon = None
    if validity_polygon_filepath:
        rpolygon = cartopy.io.shapereader.Reader(validity_polygon_filepath)
        rpolygon = [polygon for polygon in rpolygon.geometries()]
        if len(rpolygon) > 1:
            raise RuntimeError(
                "Expecting file to contain a single geometry, "
                "{} found".format(len(rpolygon))
            )
        rpolygon = rpolygon[0]

    tgt_cube = None
    if target_mask_filepath:
        tgt_cube = ants.io.load.load_landsea_mask(
            target_mask_filepath, land_fraction_threshold
        )
    return primary_cubes, alternate_cubes, rpolygon, tgt_cube


def main(
    primary_source,
    output,
    alternate_source,
    validity_polygon_filepath,
    target_mask_filepath,
    invert_mask,
    land_fraction_threshold,
    begin,
    end,
    netcdf_only,
    search_method,
    ignore_metadata_files,
):
    """
    Perform merge and fill operation on the provided sources.

    The merge stage requires both a ``primary_source`` and an ``alternate_source``
    to be provided, and may optionally have a ``polygon`` shapefile.  The
    resulting data takes values from the ``primary_source`` within the ``polygon``
    (or everywhere where valid data is present, if the ``polygon`` is not
    provided), and values from the ``alternate_source`` everywhere else.  See
    :func:`ants.analysis.merge` for further details.

    The fill stage replaces missing data values with valid data, where missing
    is defined as data that is either masked or NaN.  If a landseamask is
    provided, this mask is honoured by only filling missing land points with
    valid land values (and similarly, missing sea points with valid sea
    values).  The fill stage occurs after the merge if multiple source files
    are provided.  If the ``alternate_source`` file is not provided, only the
    fill stage is performed.

    Parameters
    ----------
    primary_source : str
        Primary source filepath.
    alternate_source : :obj:`str`, optional
        Alternate source filepath, used when merging.
    output : str
        Merged output filepath.
    validity_polygon_filepath : :obj:`str`, optional
        Filepath to the validity polygon which represents the data from the
        primary dataset which is valid.
    target_mask_filepath : :obj:`str`, optional
        Filepath to the target mask.
    invert_mask : :obj:`bool`, optional
       When set to True, treat target mask True (1) values as unmasked.  When set
       to False, treat target mask True (1) values as masked. Default is True.
    land_fraction_threshold : :obj:`str`, optional
    begin : :obj:`datetime`, optional
        If provided, all source data prior to this year is discarded.  Default is to
        include all source data.
    end : :obj:`datetime`, optional
        If provided, all source data after this year is discarded.  Default is to
        include all source data.
    search_method : :obj:`str`
        Select the search method to be used when filling missing points. The methods
        currently supported are "spiral" and "kdtree".
    Returns
    -------
    : :class:`~iris.cube.CubeList`
        Merged result.
    Raises
    ------
    RuntimeError
        If the primary source is wholly within a provided validity polygon.

    """
    primary_cubes, alternate_cubes, validity_polygon, lbm = load_data(
        primary_source,
        alternate_source,
        validity_polygon_filepath,
        target_mask_filepath,
        land_fraction_threshold,
        begin,
        end,
        ignore_metadata_files,
    )

    result = primary_cubes
    if alternate_cubes is not None:
        result = ants.analysis.merge(primary_cubes, alternate_cubes, validity_polygon)
    if target_mask_filepath:
        ants.analysis.make_consistent_with_lsm(result, lbm, invert_mask, search_method)

    if not netcdf_only:
        save.ancil(result, output)
    save.netcdf(result, output)

    return result


def _get_parser():
    parser = ants.AntsArgParser(time_constraints=True)
    lsm_help = (
        "Path to the land sea mask.  If not supplied, the missing "
        "neighbour search considers all points valid to choose "
        "from."
    )
    # Define these next two arguments here as this application brakes the mold
    # by them being optional, not mandatory.
    parser.add_argument("--target-lsm", type=str, help=lsm_help, required=False)
    parser.add_argument(
        "--land-threshold",
        type=float,
        required=False,
        help="Land fraction threshold for converting "
        "land fraction to a landsea mask. \n"
        "Fractions greater than this specified "
        "are masked.  Required if the field "
        "provided is a land fraction rather than "
        "land binary mask field.",
    )

    poly_help = (
        "Validity polygon filepath.  If not supplied, the entirety "
        "of the primary takes priority except in the presence of NAN "
        "values.  This is expected to be a shapefile and is read by "
        "cartopy.io.shapereader.Reader. "
        "If the primary source is wholly within the polygon then a runtime "
        "error will be raised."
    )
    parser.add_argument("--polygon", type=str, help=poly_help, required=False)
    invmask_help = (
        "Invert the provided target_mask or not.\n"
        "Using this argument will set it to False. "
        "When set to True, treat target mask True (1) values as unmasked. When set "
        "to False, treat target mask True (1) values as masked. "
        "It is common to use this argument to denote source ocean fields as the "
        "landsea mask has True values to denote land."
    )
    parser.add_argument(
        "--invert-mask",
        action="store_false",
        help=invmask_help,
        required=False,
    )
    parser.add_argument(
        "--search-method",
        type=str,
        help="Select the search method used when filling.",
        required=False,
        default="spiral",
    )
    return parser


def cli_interface():
    # Parse commandline arguments
    parser = _get_parser()
    args = parser.parse_args()

    try:
        source1, source2 = args.sources
    except ValueError:
        source1 = args.sources[0]
        source2 = None
    main(
        source1,
        args.output,
        source2,
        args.polygon,
        args.target_lsm,
        invert_mask=args.invert_mask,
        land_fraction_threshold=args.land_threshold,
        begin=args.begin,
        end=args.end,
        netcdf_only=args.netcdf_only,
        search_method=args.search_method,
        ignore_metadata_files=args.ignore_metadata_files,
    )


if __name__ == "__main__":
    cli_interface()

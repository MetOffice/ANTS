#!/usr/bin/env python
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
A general regrid application
****************************

Regrids data from a source to a target grid using
:class:`ants.regrid.GeneralRegridScheme`.  The result is written to an output
file.  The application supports both horizontal and vertical regridding.  The
regrid algorithm can be specified in the ants configuration file as described
in :class:`ants.config.GlobalConfiguration`. See :mod:`ants.regrid` for further
details.

If a landseamask is provided using the `target-lsm` argument, this mask is
honoured by only filling missing land points with valid land values (or
similarly, missing sea points with valid sea values).

********************
Zonal mean behaviour
********************

If the source and target provided have global extent in the 'x' axis, or if the
source has only one column ('x'), then the target will be processed to ensure
it fits the definition of a zonal mean. This ensures that a zonal mean output
is produced, regardless of the number of longitude
points in the regrid target.
"""
import ants
import ants.decomposition as decomp
import ants.io.save as save
import ants.utils
from ants.utils.cube import create_time_constrained_cubes


def load_data(
    source,
    target_grid=None,
    target_landseamask=None,
    land_fraction_threshold=None,
    begin=None,
    end=None,
    ignore_metadata_files=None,
):
    source_cubes = ants.io.load.load(
        source, ignore_metadata_files=ignore_metadata_files
    )
    if begin is not None:
        source_cubes = create_time_constrained_cubes(source_cubes, begin, end)
    if target_grid:
        target_cube = ants.io.load.load_grid(
            target_grid, ignore_metadata_files=ignore_metadata_files
        )
    else:
        target_cube = ants.io.load.load_landsea_mask(
            target_landseamask, land_fraction_threshold
        )
    return source_cubes, target_cube


def regrid(sources, target):
    sources = ants.utils.cube.as_cubelist(sources)
    results = []
    scheme = ants.regrid.GeneralRegridScheme()
    for source in sources:
        results.append(source.regrid(target, scheme))
    return results


def main(
    source_path,
    output_path,
    target_path,
    target_lsm_path,
    invert_mask,
    land_fraction_threshold,
    begin,
    end,
    save_ukca,
    netcdf_only,
    search_method,
    ignore_metadata_files,
):
    """
    General regrid application top level call function.

    Loads source data cubes, regrids them to match target data cube
    co-ordinates, and saves result to output.  In addition to writing the
    resulting data cube to disk, also returns the regridded data cube.

    Parameters
    ----------

    source_path : str
        File path for one or more files which contain the data to be
        regridded.
    target_path : str
        File path for files that provide the grid to which the source data
        cubes will be mapped.  Separate files can be provided to generate a
        complete grid i.e. a namelist for vertical levels can be used with a
        data file for the horizontal coordinates.
    target_lsm_path : str
        File path for a land sea mask that provides the grid to which
        the source data cube will be mapped.  The output will be made
        consistent with this land sea mask.
    invert_mask : :obj:`bool`, optional
        Determines whether to invert the mask for the `target_lsm_path`
        argument.
        When set to True, treat target mask True (1) values as unmasked.  When set
        to False, treat target mask True (1) values as masked. Default is True.
    output_path : str
        Output file path to write the regridded data to.
    land_fraction_threshold : str
    begin : :obj:`datetime`, optional
        If provided, all source data prior to this year is discarded.  Default is to
        include all source data.
    end : :obj:`datetime`, optional
        If provided, all source data after this year is discarded.  Default is to
        include all source data.
    search_method : :obj:`str`
        This specifies which search routine is used in making the
        provided source(s) consistent with the provided land sea mask.
        This should only be provided if a target land sea mask is also
        provided via target_lsm_path.
    ignore_metadata_files : :obj:`bool`, optional
        When set to True, files containing metadata will not be loaded alongside data
        and added as attributes to the cube.

    Returns
    -------
    : :class:`~iris.cube.Cube`
    A single data cube with the regridded data.

    """
    source_cubes, target_cube = load_data(
        source_path,
        target_path,
        target_lsm_path,
        land_fraction_threshold,
        begin,
        end,
        ignore_metadata_files,
    )
    if ants.utils.cube._is_ugrid(target_cube):
        raise ValueError(
            "Target appears to be a UGrid mesh - the regrid to mesh application in "
            "UG-ANTS should be used instead."
        )

    regridded_cubes = decomp.decompose(regrid, source_cubes, target_cube)
    if target_lsm_path:
        ants.analysis.make_consistent_with_lsm(
            regridded_cubes, target_cube, invert_mask, search_method
        )

    if save_ukca:
        save.ukca_netcdf(regridded_cubes, output_path)
    else:
        if not netcdf_only:
            save.ancil(regridded_cubes, output_path)
        save.netcdf(regridded_cubes, output_path)

    return regridded_cubes


def _get_parser():
    parser = ants.AntsArgParser(
        target_lsm=True, target_grid=True, time_constraints=True
    )
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
        "--save-ukca",
        action="store_true",
        help="Save to a UKCA-specific netCDF file",
        required=False,
    )
    parser.add_argument(
        "--search-method",
        type=str,
        help="Select the search method used when filling. "
        "This specifies which search routine is used in making the "
        "provided source(s) consistent with the provided land sea mask. "
        "This should only be provided if a target land sea mask is provided via "
        "the ``--target-lsm`` option.",
        required=False,
        default="spiral",
    )
    return parser


def cli_interface():
    parser = _get_parser()
    args = parser.parse_args()

    source = args.sources
    main(
        source,
        args.output,
        args.target_grid,
        args.target_lsm,
        args.invert_mask,
        args.land_threshold,
        args.begin,
        args.end,
        args.save_ukca,
        args.netcdf_only,
        args.search_method,
        args.ignore_metadata_files,
    )


if __name__ == "__main__":
    cli_interface()

#!/usr/bin/env python
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
A vertical regrid application
*****************************

Regrids data from a source to a target grid using
:class:`ants.regrid.GeneralRegridScheme`.  The result is written to an output
file.  The application supports only vertical regridding.  The
regrid algorithm can be specified in the ants configuration file as described
in :class:`ants.config.GlobalConfiguration`. See :mod:`ants.regrid` for further
details.
"""
import ants
import ants.io.save as save
import ants.utils
from ants.utils.cube import create_time_constrained_cubes


def load_data(
    source,
    target_grid,
    begin=None,
    end=None,
):
    source_cubes = ants.io.load.load(source)
    if begin is not None:
        source_cubes = create_time_constrained_cubes(source_cubes, begin, end)

    target_cube = ants.io.load.load_grid(target_grid)

    check_target(target_cube, source_cubes)

    return source_cubes, target_cube


def check_target(
    target_cube,
    source_cubes,
):
    """
    Check the target cube against common pitfalls. This application is for
    structured mesh and vertical regridding only.
    """
    if ants.utils.cube._is_ugrid(target_cube):
        raise ValueError(
            "Target appears to be a UGrid mesh - the regrid to mesh application in "
            "UG-ANTS should be used instead."
        )

    target_coords = [coord.name() for coord in target_cube.coords()]

    if "latitude" in target_coords:
        for cube in source_cubes:
            if cube.coord("latitude") != target_cube.coord("latitude"):
                raise ValueError(
                    "Target grid latitude coordinates do not match source grid "
                    "latitude coordinates"
                )

    if "longitude" in target_coords:
        for cube in source_cubes:
            if cube.coord("longitude") != target_cube.coord("longitude"):
                raise ValueError(
                    "Target grid longitude coordinates do not match source grid "
                    "longitude coordinates"
                )


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
    begin,
    end,
    save_ukca,
    netcdf_only,
):
    """
    Vertical regrid application top level call function.

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
        cubes will be mapped.  e.g. a namelist for vertical levels.
    output_path : str
        Output file path to write the regridded data to.
    begin : :obj:`datetime`, optional
        If provided, all source data prior to this year is discarded.  Default is to
        include all source data.
    end : :obj:`datetime`, optional
        If provided, all source data after this year is discarded.  Default is to
        include all source data.


    Returns
    -------
    : :class:`~iris.cube.Cube`
    A single data cube with the regridded data.

    """
    source_cubes, target_cube = load_data(
        source_path,
        target_path,
        begin,
        end,
    )

    regridded_cubes = regrid(source_cubes, target_cube)

    if save_ukca:
        save.ukca_netcdf(regridded_cubes, output_path)
    else:
        if not netcdf_only:
            save.ancil(regridded_cubes, output_path)
        save.netcdf(regridded_cubes, output_path)

    return regridded_cubes


def _get_parser():
    parser = ants.AntsArgParser(target_grid=True, time_constraints=True)
    parser.add_argument(
        "--save-ukca",
        action="store_true",
        help="Save to a UKCA-specific netCDF file",
        required=False,
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
        args.begin,
        args.end,
        args.save_ukca,
        args.netcdf_only,
    )


if __name__ == "__main__":
    cli_interface()

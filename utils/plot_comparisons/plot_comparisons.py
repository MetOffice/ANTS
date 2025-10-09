#!/usr/bin/env python
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Plot Comparisons Tool
*********************

This module generates comparison plots from a two ancillary files. It is
intended for comparing a KGO file with a test output file when there is a
difference between the two datasets. Plots it will generate are:

- The slice in the KGO dataset where the greatest difference was detected.

- The slice in the test result dataset where the greatest difference was
  detected.

- The absolute difference between those two slices.

- The log difference (where the base-10 logarithm of both datasets is
  generated, then their difference calculated).

- The relative error.

Examples
--------
To run the tool from the command line:

$ python kgo_file.nc test_output_.nc /specified/output/directory

Notes
-----
- This module is integrated into the rose-stem test suite, and will trigger on
  rose_ana check_nccmp failures.
- If run automatically via the test suite, the plots will be saved in a
  "plot_comparisons" folder in the cylc run "share" directory - a link to this
  folder is printed to the plot_comparison task's job.out.
- Supports .nc and f03 ancillary files.
- The datasets for comparison must use the same grid coords.
"""
import argparse
from pathlib import Path

import iris
from plot_comparisons_utils import (
    check_grids_match,
    generate_absolute_difference_cube,
    generate_log_difference_cube,
    generate_relative_error_cube,
    locate_slice_of_greatest_difference,
    retrieve_corresponding_slices_of_greatest_difference,
)
from plot_generator import generate_plots, plot_title_generator, save_plot


def retrieve_comparison_filepaths():
    """
    Retrieves the filepaths that are required for running the main plotting
    functionality.


    Parameters
    ----------
    None

    Returns
    -------
    args.kgo_filepath : pathlib.PosixPath
    args.actual_result_filepath : pathlib.PosixPath
    args.plot_output_filepath : str
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("kgo_filepath", type=Path, help="Path to KGO file")
    parser.add_argument(
        "actual_result_filepath",
        type=Path,
        help="Path to file resulting from test.",
    )
    parser.add_argument(
        "plot_output_filepath",
        type=str,
        help="The directory where you would like the plots to be saved.",
    )
    args = parser.parse_args()
    if not args.kgo_filepath.is_file():
        raise ValueError("KGO filepath retrieved is not a file.")
    if not args.actual_result_filepath.is_file():
        raise ValueError("Result filepath retrieved is not a file.")
    else:
        return (
            args.kgo_filepath,
            args.actual_result_filepath,
            args.plot_output_filepath,
        )


def main(kgo_filepath, actual_result_filepath, plot_output_filepath):
    """
    Generate comparison plots using the provided filepaths.

    Parameters
    ----------
    kgo_filepath : pathlib.PosixPath
    actual_result_filepath : pathlib.PosixPath
    plot_output_filepath : str

    Returns
    -------
    None

    """
    kgo_cube = iris.load_cube(kgo_filepath)
    test_output_cube = iris.load_cube(actual_result_filepath)

    check_grids_match(kgo_cube, test_output_cube)

    absolute_difference_cube = generate_absolute_difference_cube(
        kgo_cube, test_output_cube
    )

    max_diff_slice_index, slice_of_greatest_difference = (
        locate_slice_of_greatest_difference(absolute_difference_cube)
    )

    kgo_slice_of_interest, test_result_slice_of_interest = (
        retrieve_corresponding_slices_of_greatest_difference(
            max_diff_slice_index, kgo_cube, test_output_cube
        )
    )
    log_difference_cube = generate_log_difference_cube(
        kgo_slice_of_interest, test_result_slice_of_interest
    )

    relative_error_cube = generate_relative_error_cube(
        kgo_slice_of_interest, slice_of_greatest_difference
    )

    plot_title = plot_title_generator(kgo_cube, test_output_cube)
    generate_plots(
        plot_title,
        slice_of_greatest_difference,
        kgo_slice_of_interest,
        test_result_slice_of_interest,
        log_difference_cube,
        relative_error_cube,
    )

    save_plot(kgo_filepath, plot_output_filepath)


if __name__ == "__main__":
    kgo_filepath, actual_result_filepath, plot_output_filepath = (
        retrieve_comparison_filepaths()
    )
    main(kgo_filepath, actual_result_filepath, plot_output_filepath)

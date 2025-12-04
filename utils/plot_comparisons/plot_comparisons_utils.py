# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import iris
import numpy as np


def check_grids_match(kgo_cube, test_output_cube):
    """
    Verifies the grid coordinates of the kgo and test output cubes match.

    Parameters
    ----------
    kgo_cube : iris.cube.Cube
    test_output_cube : iris.cube.Cube

    Raises
    ------
    ValueError
        If the grid co-ordinates between the kgo_cube and test_output_cube do
        not match.
    """
    if kgo_cube.coord(axis="X") != (test_output_cube.coord(axis="X")):
        raise ValueError(
            "Grid co-ordinates (X axis) between KGO and test output do not match."
        )

    elif kgo_cube.coord(axis="Y") != (test_output_cube.coord(axis="Y")):
        raise ValueError(
            "Grid co-ordinates (Y axis) between KGO and test output do not match."
        )


def generate_absolute_difference_cube(kgo_cube, test_output_cube):
    """
    Return a cube of absolute difference by subtracting the the results of
    the test output data from the kgo data.

    Parameters
    ----------
    kgo_cube : iris.cube.Cube
        The kgo_cube related to the nccmp test that has failed.
    test_output_cube : iris.cube.Cube
        The test_output_cube related to the nccmp test that has failed.

    Returns
    -------
    absolute_difference_cube : :class:`~iris.cube.Cube`
        A cube containing the absolute differences of all the slices between
        the kgo_cube and test_output_cube.
    """
    absolute_difference_cube = iris.analysis.maths.abs(test_output_cube - kgo_cube)
    return absolute_difference_cube


def locate_slice_of_greatest_difference(absolute_difference_cube):
    """
    Locate the slice with the greatest absolute difference.

    This function returns the slice with the greatest absolute difference,
    which is used for generating the absolute difference plot.

    It also returns an index for relocating the slice in other functions.

    Parameters
    ----------
    absolute_difference_cube : iris.cube.Cube
        The cube containing the absolute differences calculated as a result
        of subtracting the kgo_cube from the test_output_cube.

    Returns
    -------
    tuple
        A tuple containing:
        - max_diff_slice_index : int
            The index of the slice with the greatest absolute difference.
        - slice_of_greatest_difference : :class:`~iris.cube.Cube`
            The slice with the greatest absolute difference.
    """
    slices = absolute_difference_cube.slices(
        [
            absolute_difference_cube.coord(axis="X"),
            absolute_difference_cube.coord(axis="Y"),
        ]
    )
    max_diff_value = 0
    max_diff_slice_index = 0
    slice_of_greatest_difference = None
    for index, slice in enumerate(slices):
        current_max = np.max(slice.data)
        if current_max > max_diff_value:
            max_diff_value = current_max
            max_diff_slice_index = index
            slice_of_greatest_difference = slice
    return max_diff_slice_index, slice_of_greatest_difference


def retrieve_corresponding_slices_of_greatest_difference(
    max_diff_slice_index, kgo_cube, test_output_cube
):
    """
    Retrieve the slices with the greatest absolute difference from the KGO
    and test result cubes required for their corresponding plots.

    Parameters
    ----------
    max_diff_slice_index : int
        The index of the slice with the greatest absolute difference.

    kgo_cube : iris.cube.Cube
        The kgo_cube related to the nccmp test that has failed.

    test_output_cube : iris.cube.Cube
        The test_output_cube related to the nccmp test that has failed.

    Returns
    -------
    kgo_slice_of_interest : :class:`~iris.cube.Cube`
        The slice with the greatest absolute difference from the KGO cube to
        generate the KGO plot.

    test_result_slice_of_interest : :class:`~iris.cube.Cube`
        The slice with the greatest absolute difference from the
        test_output_cube to generate the test output plot.
    """

    kgo_slices = kgo_cube.slices([kgo_cube.coord(axis="X"), kgo_cube.coord(axis="Y")])
    test_output_cube_slices = test_output_cube.slices(
        [kgo_cube.coord(axis="X"), kgo_cube.coord(axis="Y")]
    )
    for index, (kgo_slice, test_output_slice) in enumerate(
        zip(kgo_slices, test_output_cube_slices)
    ):
        if index == max_diff_slice_index:
            kgo_slice_of_interest = kgo_slice
            test_result_slice_of_interest = test_output_slice
            return kgo_slice_of_interest, test_result_slice_of_interest


def generate_log_difference_cube(kgo_slice_of_interest, test_result_slice_of_interest):
    """
    Generate a log difference cube from the two slices where greatest
    difference has been detected.

    Parameters
    ----------
    kgo_slice_of_interest : iris.cube.Cube
        The slice with the greatest absolute difference from the KGO cube.

    test_result_slice_of_interest : iris.cube.Cube
        The slice with the greatest absolute difference from the
        test_output_cube.

    Returns
    -------
    log_diff_cube : iris.cube.Cube
        The log difference cube generated from the log-transformed data of the
        KGO slice and the test result slice.
    """
    with np.errstate(divide="ignore"):
        log_diff_data = np.log10(
            kgo_slice_of_interest.data - test_result_slice_of_interest.data
        )
        log_diff_cube = kgo_slice_of_interest.copy(data=log_diff_data)
        return log_diff_cube


def generate_relative_error_cube(kgo_slice_of_interest, slice_of_greatest_difference):
    """
    Generates a relative error cube from the two slices where greatest
    difference have been detected.

    Parameters
    ----------
    kgo_slice_of_interest : iris.cube.Cube
        The slice with the greatest absolute difference from the KGO cube.

    slice_of_greatest_difference : iris.cube.Cube
        The slice with the greatest absolute difference.

    Returns
    -------
    relative_error_cube : :class:`~iris.cube.Cube`
        An Iris cube representing the relative error between the test result
        and the kgo, at the slice where greatest difference was calculated.

    """
    relative_error_cube = (slice_of_greatest_difference / kgo_slice_of_interest) * 100
    return relative_error_cube

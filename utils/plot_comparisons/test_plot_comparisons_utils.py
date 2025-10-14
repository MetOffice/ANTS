# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import re

import numpy as np
import pytest
from ants.tests.stock import osgb, simple_3d_time_varying
from plot_comparisons_utils import (
    check_grids_match,
    generate_absolute_difference_cube,
    locate_slice_of_greatest_difference,
    retrieve_corresponding_slices_of_greatest_difference,
)


@pytest.fixture
def synthetic_abnormal_first_slice_cube():
    stock_cube = simple_3d_time_varying()
    stock_cube.data = np.array(
        [
            [
                [1000, 1, 2, 3, 4, 5],
                [6, 7, 8, 9, 10, 11],
                [12, 13, 14, 15, 16, 17],
                [18, 19, 20, 21, 22, 23],
                [24, 25, 26, 27, 28, 29],
            ],
            [
                [30, 31, 32, 33, 34, 35],
                [36, 37, 38, 39, 40, 41],
                [42, 43, 44, 45, 46, 47],
                [48, 49, 50, 51, 52, 53],
                [54, 55, 56, 57, 58, 59],
            ],
            [
                [60, 61, 62, 63, 64, 65],
                [66, 67, 68, 69, 70, 71],
                [72, 73, 74, 75, 76, 77],
                [78, 79, 80, 81, 82, 83],
                [84, 85, 86, 87, 88, 89],
            ],
        ]
    )
    return stock_cube


@pytest.fixture
def synthetic_abnormal_last_slice_cube():
    stock_cube = simple_3d_time_varying()
    stock_cube.data = np.array(
        [
            [
                [0, 1, 2, 3, 4, 5],
                [6, 7, 8, 9, 10, 11],
                [12, 13, 14, 15, 16, 17],
                [18, 19, 20, 21, 22, 23],
                [24, 25, 26, 27, 28, 29],
            ],
            [
                [30, 31, 32, 33, 34, 35],
                [36, 37, 38, 39, 40, 41],
                [42, 43, 44, 45, 46, 47],
                [48, 49, 50, 51, 52, 53],
                [54, 55, 56, 57, 58, 59],
            ],
            [
                [60, 61, 62, 63, 64, 65],
                [66, 67, 68, 69, 70, 71],
                [72, 73, 74, 75, 76, 77],
                [78, 79, 80, 81, 82, 83],
                [84, 85, 86, 87, 88, 1000],
            ],
        ]
    )
    return stock_cube


@pytest.fixture
def synthetic_slice():
    return np.array(
        [
            [0, 1, 2, 3, 4, 5],
            [6, 7, 8, 9, 10, 11],
            [12, 13, 14, 15, 16, 17],
            [18, 19, 20, 21, 22, 23],
            [24, 25, 26, 27, 28, 29],
        ]
    )


class TestCheckGrids:
    def test_mismatched_x_grids_raises_error(self):
        cube1 = osgb(shape=[2, 2])
        cube2 = osgb(shape=[2, 3])
        expected_error = re.escape(
            "Grid co-ordinates (X axis) between KGO and test output do not match."
        )
        with pytest.raises(
            ValueError,
            match=expected_error,
        ):
            check_grids_match(cube1, cube2)

    def test_mismatched_y_grids_raises_error(self):
        cube1 = osgb(shape=[2, 2])
        cube2 = osgb(shape=[3, 2])
        expected_error = re.escape(
            "Grid co-ordinates (Y axis) between KGO and test output do not match."
        )
        with pytest.raises(
            ValueError,
            match=expected_error,
        ):
            check_grids_match(cube1, cube2)


def test_generate_absolute_difference_cube(
    synthetic_abnormal_first_slice_cube, synthetic_abnormal_last_slice_cube
):
    result = generate_absolute_difference_cube(
        synthetic_abnormal_first_slice_cube, synthetic_abnormal_last_slice_cube
    )
    assert result.data[0, 0, 0] == 1000
    assert result.data[0, 0, 1] == 0
    assert result.data[-1, -1, -1] == 911


class TestLocateSliceOfGreatestDifference:

    def test_locate_index_of_greatest_difference_first_slice(
        self, synthetic_abnormal_first_slice_cube
    ):
        index_located, _cube_slice = locate_slice_of_greatest_difference(
            synthetic_abnormal_first_slice_cube
        )
        assert index_located == 0

    def test_locate_index_of_greatest_difference_last_slice(
        self, synthetic_abnormal_last_slice_cube
    ):

        index_located, _cube_slice = locate_slice_of_greatest_difference(
            synthetic_abnormal_last_slice_cube
        )
        assert index_located == 2

    def test_returns_first_slice_cube(self, synthetic_abnormal_first_slice_cube):

        result = locate_slice_of_greatest_difference(
            synthetic_abnormal_first_slice_cube
        )
        slice_of_greatest_difference = result[1]
        time_coord = slice_of_greatest_difference.coord("time")
        time = time_coord.units.num2date(time_coord.points)[0]

        assert str(time) == "1970-01-01 00:00:00"

    def test_returns_last_slice_cube(self, synthetic_abnormal_last_slice_cube):

        result = locate_slice_of_greatest_difference(synthetic_abnormal_last_slice_cube)
        slice_of_greatest_difference = result[1]
        time_coord = slice_of_greatest_difference.coord("time")
        time = time_coord.units.num2date(time_coord.points)[0]

        assert str(time) == "1970-01-01 02:00:00"


@pytest.mark.parametrize(
    "max_diff_slice_index, expected_time_slice",
    [
        (0, "1970-01-01 00:00:00"),
        (1, "1970-01-01 01:00:00"),
        (2, "1970-01-01 02:00:00"),
    ],
)
def test_retrieve_corresponding_slices_of_greatest_difference(
    max_diff_slice_index,
    expected_time_slice,
    synthetic_abnormal_last_slice_cube,
):
    kgo_cube = synthetic_abnormal_last_slice_cube
    test_output_cube = synthetic_abnormal_last_slice_cube

    retrieved_kgo_slice, retrieved_test_output_slice = (
        retrieve_corresponding_slices_of_greatest_difference(
            max_diff_slice_index, kgo_cube, test_output_cube
        )
    )
    kgo_time_coord = retrieved_kgo_slice.coord("time")
    kgo_time = kgo_time_coord.units.num2date(kgo_time_coord.points)[0]

    test_output_time_coord = retrieved_test_output_slice.coord("time")
    test_output_time = test_output_time_coord.units.num2date(
        test_output_time_coord.points
    )[0]
    assert str(kgo_time) == expected_time_slice
    assert str(test_output_time) == expected_time_slice

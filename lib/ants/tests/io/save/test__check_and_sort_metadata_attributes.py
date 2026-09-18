# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import logging
from unittest import mock

import ants.tests.stock as stock
import pytest
from ants.io.save import _check_and_sort_metadata_attributes


def test_license_attribute_written(tmp_path):
    """Tests that a cube with a license is written out."""
    cube = stock.geodetic(shape=(2, 2))
    license = "This is a cube's license. "
    cube.attributes["license"] = license
    cube.rename("license test cube")
    filename = tmp_path / "test_cube"
    _check_and_sort_metadata_attributes([cube], filename)
    expected_filename = str(filename) + ".license"
    with open(expected_filename, "r") as file:
        actual_license = file.read()
    assert actual_license == license


@pytest.mark.filterwarnings(
    "ignore:The attribute name licence has been changed to 'license', in line with "
    "ANTS working practices.:UserWarning"
)
def test_licence_attribute_written(tmp_path):
    """Tests that a cube with a licence  is changed and written out."""
    cube = stock.geodetic(shape=(2, 2))
    licence = "This is a cube's license. "
    cube.attributes["licence"] = licence
    cube.rename("licence test cube")
    filename = tmp_path / "test_cube"
    _check_and_sort_metadata_attributes([cube], filename)
    expected_filename = str(filename) + ".license"
    with open(expected_filename, "r") as file:
        actual_license = file.read()
    assert actual_license == licence


def test_loaded_license_written(tmp_path):
    """Tests that a cube with a license that resembles the format of a longer license
    written in, is written out correctly."""
    loaded_license = [
        "This is the license of the cube.\n",
        "\n",
        "    It should be preserved and added to the cube when loaded.\n",
        "    ",
    ]
    cube = stock.geodetic(shape=(2, 2))
    cube.attributes["license"] = loaded_license
    cube.rename("loaded license test cube")
    filename = tmp_path / "test_cube"
    _check_and_sort_metadata_attributes([cube], filename)
    expected_filename = str(filename) + ".license"
    with open(expected_filename, "r") as file:
        actual_license = file.readlines()
    assert actual_license == loaded_license


def test_log_output(caplog):
    """Tests that the logger gives the correct output when a file is written out."""
    cube = stock.geodetic(shape=(2, 2))
    institution = "This data came from University Blah. "
    cube.attributes["institution"] = institution
    expected_message = (
        "institution has been written to sidecar file filename.institution"
    )
    # mocks out the opening of files, so no file is created
    with mock.patch("builtins.open"):
        with caplog.at_level(logging.INFO):
            _check_and_sort_metadata_attributes([cube], "filename")
    assert expected_message in caplog.text


def test_multiple_cubes(tmp_path):
    """Test that multiple_cubes with attributes is written out correctly."""
    # creating three cubes with different license attributes
    cube1 = stock.geodetic(shape=(2, 2))
    license1 = "This is a cube's license. "
    cube1.attributes["license"] = license1
    cube1.rename("the first cube")
    cube2 = stock.geodetic(shape=(2, 2))
    license2 = "This is another cube's license. "
    cube2.attributes["license"] = license2
    cube2.rename("the second cube")
    cube3 = stock.geodetic(shape=(2, 2))
    license3 = "This is a third cube's license. "
    cube3.attributes["license"] = license3
    cube3.rename("the third cube")
    cubelist = [cube1, cube2, cube3]
    filename = tmp_path / "multiple_cube_test"
    # The actual test
    _check_and_sort_metadata_attributes(cubelist, filename)
    expected_filename = str(filename) + ".license"
    with open(expected_filename, "r") as file:
        actual_license = file.read()
    expected_license = (
        "the first cube = This is a cube's license. \nthe second cube = "
        "This is another cube's license. \nthe third cube = This is a third cube's "
        "license. \n"
    )
    assert actual_license == expected_license


def test_all_different_attributes_written_out():
    """Tests that a cube with a multiple different attributes writes
    out all metadata files."""
    cube = stock.geodetic(shape=(2, 2))
    attribution = "This data came from an institution. "
    cube.attributes["attribution"] = attribution
    cube.attributes["restrictions"] = (
        "This data is restricted to be used for testing purposes only."
    )
    cube.attributes["license"] = "This is a license for the data"
    filename = "test_multiple_attributes"
    with mock.patch("ants.io.save._write_metadata_file") as mock_method:
        _check_and_sort_metadata_attributes([cube], filename)

    expected_license = mock.call(
        ["This is a license for the data"], "test_multiple_attributes", "license"
    )
    expected_attribution = mock.call(
        ["This data came from an institution. "],
        "test_multiple_attributes",
        "attribution",
    )
    expected_restrictions = mock.call(
        ["This data is restricted to be used for testing purposes only."],
        "test_multiple_attributes",
        "restrictions",
    )

    assert expected_license in mock_method.call_args_list
    assert expected_attribution in mock_method.call_args_list
    assert expected_restrictions in mock_method.call_args_list

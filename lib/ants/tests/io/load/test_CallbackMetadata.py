# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Includes tests for end-to-end functionality of CallbackMetadata as well as calling the
class directly.
"""

import unittest.mock as mock
import warnings

import ants.io.load
import iris
import pytest


def test_metadata_files_added_to_attributes(tmp_path):
    """Tests that metadata files are found and added to the cube's attributes."""
    # The text that would be in a license file
    license_text = """This is the license of the cube.

    It should be preserved and added to the cube when loaded.
    """
    # How the text should look while stored in an array
    loaded_license = [
        "This is the license of the cube.\n",
        "\n",
        "    It should be preserved and added to the cube when loaded.\n",
        "    ",
    ]
    test_cube = ants.tests.stock.geodetic(shape=(2, 2))
    temporary_cube_path = tmp_path / "cube_attribute.pp"
    iris.save(test_cube, str(temporary_cube_path))
    temporary_license_path = tmp_path / "cube_attribute.pp.license"
    temporary_license_path.write_text(license_text, encoding="utf-8")
    loaded_test_cube = ants.io.load.load_cube(temporary_cube_path)
    assert loaded_test_cube.attributes["license"] == loaded_license


def test_no_metadata_loaded(tmp_path):
    """Tests that metadata files are not loaded when the option is turned off."""
    # The text that would be in a license file
    license_text = """This is the license of the cube.

    It should be preserved and added to the cube when loaded.
    """
    test_cube = ants.tests.stock.geodetic(shape=(2, 2))
    temporary_cube_path = tmp_path / "cube_attribute.pp"
    iris.save(test_cube, str(temporary_cube_path))
    temporary_license_path = tmp_path / "cube_attribute.pp.license"
    temporary_license_path.write_text(license_text, encoding="utf-8")
    loaded_test_cube = ants.io.load.load_cube(
        temporary_cube_path, ignore_metadata_files=True
    )
    with pytest.raises(KeyError):
        loaded_test_cube.attributes["license"]


def test_user_callback_added():
    """Test that on ititialisation, the user's function will be set."""

    def user_callback(cube, field, filename):
        print("a user's callback, passed in")

    class_instance = ants.io.load._CallbackMetadata(user_callback)
    assert class_instance._user_callback == user_callback


def test_args_parsed_correctly_with_kwargs(tmp_path):
    """Tests that when passed a callback using a keyword argument,
    the callback is parsed correctly."""
    mock_callback = mock.Mock()
    test_cube = ants.tests.stock.geodetic(shape=(2, 2))
    temporary_cube_path = tmp_path / "cube_attribute.pp"
    iris.save(test_cube, str(temporary_cube_path))
    ants.io.load.load_cube(temporary_cube_path, callback=mock_callback)
    mock_callback.assert_called()


def test_args_parsed_correctly_with_positional_args(tmp_path):
    """Tests that when passed a callback using a keyword argument,
    the callback is parsed correctly."""
    mock_callback = mock.Mock()
    test_cube = ants.tests.stock.geodetic(shape=(2, 2))
    temporary_cube_path = tmp_path / "cube_attribute.pp"
    iris.save(test_cube, str(temporary_cube_path))
    ants.io.load.load_cube(temporary_cube_path, None, mock_callback)
    mock_callback.assert_called()


def test_existing_metadata_error(tmp_path):
    """Tests that an error is raised when a cube has existing metadata attributes."""
    license_text = "a license"
    test_cube = ants.tests.stock.geodetic(shape=(2, 2))
    test_cube.attributes["license"] = "an existing license"
    temporary_cube_path = tmp_path / "cube_attribute.nc"
    iris.save(test_cube, str(temporary_cube_path))
    temporary_license_path = tmp_path / "cube_attribute.nc.license"
    temporary_license_path.write_text(license_text, encoding="utf-8")
    error_message = (
        "The license is already an attribute on the cube. To ignore "
        "metadata files, use the --ignore-metadata-files flag."
    )

    with pytest.raises(AttributeError, match=error_message):
        ants.io.load.load_cube(temporary_cube_path)


def test_misspelt_license_warning(tmp_path):
    """Tests that different spellings for license will raise a warning."""
    license_text = "a license"
    test_cube = ants.tests.stock.geodetic(shape=(2, 2))
    temporary_cube_path = tmp_path / "cube_attribute.nc"
    iris.save(test_cube, str(temporary_cube_path))
    temporary_license_path = tmp_path / "cube_attribute.nc.lisense"
    temporary_license_path.write_text(license_text, encoding="utf-8")

    warning_message = (
        "The attribute name lisense has been changed to license, in "
        "line with ANTS working practices."
    )
    with pytest.raises(UserWarning, match=warning_message):
        ants.io.load.load_cube(temporary_cube_path)


def test_misspelt_license_added(tmp_path):
    """Tests that a different spelling of license will add a license attribute."""
    license_text = "a license"
    test_cube = ants.tests.stock.geodetic(shape=(2, 2))
    temporary_cube_path = tmp_path / "cube_attribute.nc"
    iris.save(test_cube, str(temporary_cube_path))
    temporary_license_path = tmp_path / "cube_attribute.nc.lisense"
    temporary_license_path.write_text(license_text, encoding="utf-8")
    # ignore warning that will be raised
    warning_message = (
        "The attribute name lisense has been changed to license, in "
        "line with ANTS working practices."
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=warning_message, category=UserWarning)
        loaded_cube = ants.io.load.load_cube(temporary_cube_path)
        assert loaded_cube.attributes["license"] == ["a license"]


def test_invalid_metadata_name(tmp_path):
    """Tests that an invalid metadata name will not be added as an attribute."""
    test_cube = ants.tests.stock.geodetic(shape=(2, 2))
    temporary_cube_path = tmp_path / "cube_attribute.nc"
    iris.save(test_cube, str(temporary_cube_path))
    temporary_license_path = tmp_path / "cube_attribute.nc.invalid-name"
    temporary_license_path.write_text(" ", encoding="utf-8")

    warning_message = (
        "Attribute invalid-name is not a valid metadata file name. "
        "Accepted metadata names are license, attribution and restrictions."
    )
    with pytest.raises(UserWarning, match=warning_message):
        ants.io.load.load_cube(temporary_cube_path)

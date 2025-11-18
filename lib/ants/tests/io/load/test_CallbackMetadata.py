"""
Includes tests for end-to-end functionality of CallbackMetadata as well as calling the
class directly.
"""

import ants.io.load
import iris
import pytest
import unittest.mock as mock


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

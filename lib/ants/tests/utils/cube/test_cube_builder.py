# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import ants.tests.stock
import iris
import numpy as np
import pytest
from ants.utils.cube import CubeBuilder


def _compare_dictionary(expected_dictionary, actual_dictionary):
    # check keys
    for dictionary_keys in zip(
        expected_dictionary.keys(), actual_dictionary.keys(), strict=True
    ):
        assert dictionary_keys[0] == dictionary_keys[1]
    # check values
    for dictionary_values in zip(
        expected_dictionary.values(), actual_dictionary.values(), strict=True
    ):
        try:
            assert dictionary_values[0] == dictionary_values[1]
        except ValueError:
            assert np.array_equal(dictionary_values[0], dictionary_values[1])


def test_create_the_cube_geodoetic():
    """Test that a cube contains all the attributes passed in"""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(1, 2))
    builder.x = {
        "points": ([-90.0, 90.0]),
        "bounds": ([[-180.0, 0.0], [0.0, 180.0]]),
        "dim": 1,
    }
    builder.y = {"points": ([0.0]), "bounds": ([[-90.0, 90.0]]), "dim": 0}
    builder.data = [[0, 1]]

    cube = builder._create_the_cube(None, None)

    assert cube == ants.tests.stock.geodetic(shape=(1, 2))


def test_create_the_cube_osgb():
    """Test create the cube works with osgb coordinate system"""
    builder = CubeBuilder(ants.coord_systems.OSGB.crs, shape=(1, 2))

    builder.x = {
        "points": ([-10000000.0, 10000000.0]),
        "bounds": ([[-20000000.0, 0.0], [0.0, 20000000.0]]),
        "dim": 1,
    }
    builder.y = {"points": ([0.0]), "bounds": ([[-10000000.0, 10000000.0]]), "dim": 0}
    builder.data = [[0, 1]]

    cube = builder._create_the_cube(None, None)

    assert cube == ants.tests.stock.osgb(shape=(1, 2))


def test_create_data():
    """Test create_data method with default"""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(1, 2))
    expected_x = {"points": ([-90.0, 90.0]), "bounds": None, "dim": 1}
    expected_y = {"points": ([0.0]), "bounds": None, "dim": 0}
    expected_data = [[0, 1]]
    actual_x, actual_y, actual_data = builder._create_data(
        (1, 2), None, None, None, None
    )

    _compare_dictionary(actual_x, expected_x)
    _compare_dictionary(actual_y, expected_y)
    assert np.array_equal(actual_data, expected_data)


def test_create_data_x_and_y_lim():
    """Test create_data method with x and y limits specified."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(1, 2))
    expected_x = {"points": ([-2.5, 2.5]), "bounds": None, "dim": 1}
    expected_y = {"points": ([2.5]), "bounds": None, "dim": 0}
    expected_data = [[0, 1]]
    actual_x, actual_y, actual_data = builder._create_data(
        (1, 2), (-5, 5), (-5, 10), None, None
    )

    _compare_dictionary(actual_x, expected_x)
    _compare_dictionary(actual_y, expected_y)
    assert np.array_equal(actual_data, expected_data)


def test_create_data_with_bounds():
    """Test create_data method with bounds specified"""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(1, 2))
    expected_x = {
        "points": ([-2.5, 2.5]),
        "bounds": ([[-5.0, 0.0], [0.0, 5.0]]),
        "dim": 1,
    }
    expected_y = {"points": ([2.5]), "bounds": ([[-5.0, 10.0]]), "dim": 0}
    expected_data = [[0, 1]]
    actual_x, actual_y, actual_data = builder._create_data(
        (1, 2), (-5, 5), (-5, 10), None, True
    )

    _compare_dictionary(actual_x, expected_x)
    _compare_dictionary(actual_y, expected_y)
    assert np.array_equal(actual_data, expected_data)


def test_create_data_no_shape():
    """Test the create data method when given data rather than a shape"""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(1, 2))
    expected_x = {"points": ([-90.0, 90.0]), "bounds": None, "dim": 1}
    expected_y = {"points": ([0.0]), "bounds": None, "dim": 0}
    expected_data = [[0, 0]]
    actual_x, actual_y, actual_data = builder._create_data(
        None, None, None, np.array([[0, 0]]), None
    )

    _compare_dictionary(actual_x, expected_x)
    _compare_dictionary(actual_y, expected_y)
    assert np.array_equal(actual_data, expected_data)


def test_no_shape_and_no_data():
    """Tests that a ValueError will be raised if no shape or data is given."""
    expected_error = "Shape and data cannot be None values."
    with pytest.raises(ValueError, match=expected_error):
        CubeBuilder(iris.coord_systems.GeogCS(6371229.0))


def test_invalid_shape():
    """Tests that the CubeBuilder will return an error when given an invalid shape."""
    expected_error = "Invalid shape 1 given."
    with pytest.raises(ValueError, match=expected_error):
        CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=1)


def test_add_3d_time_coord_default():
    """Tests that the time coordinate is added to the cube with the most common
    value."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(3, 5, 6))
    # Get the names for all the coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check time coordinate doesn't exist yet
    assert "time" not in coord_names
    builder.add_3d_time_coord(3)
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check time coordinate is there
    assert "time" in coord_names


def test_add_3d_time_coord_different():
    """Tests that the time coordinate is added to the cube with a different value to
    the most common use case."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(7, 5, 6))
    # Get the names for all the coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check time coordinate doesn't exist yet
    assert "time" not in coord_names
    builder.add_3d_time_coord(7)
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check time coordinate is there
    assert "time" in coord_names


def test_add_sigma_aux_coord():
    """Tests that the sigma coordinate gets added to the cube."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(3, 4, 5, 6))
    # Get the names for all the coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check sigma coordinate doesn't exist yet
    assert "sigma" not in coord_names
    builder.add_sigma_aux_coord()
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check sigma coordinate is there
    assert "sigma" in coord_names


def test_add_model_level_coordinate():
    """Tests that the model_level_number coordinate gets added to the cube."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(3, 4, 5, 6))
    # Get the names for all the coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check model_level_number coordinate doesn't exist yet
    assert "model_level_number" not in coord_names
    builder.add_model_level_coordinate()
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check model_level_number coordinate is there
    assert "model_level_number" in coord_names


def test_add_hybrid_height_coordinate_factory_level_height():
    """Tests that the add_hybrid_height_coordinate_factory method adds level_height
    to the cube."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(3, 4, 5, 6))
    # Get the names for all the coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check the different coordinates that the hybrid_height_coordinate_factory
    # adds doesn't exist yet.
    assert "level_height" not in coord_names
    builder.add_sigma_aux_coord()
    builder.add_model_level_coordinate()
    builder.add_hybrid_height_coordinate_factory(6)
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check new coordinates are there
    assert "level_height" in coord_names


def test_add_hybrid_height_coordinate_factory_surface_altitude():
    """Tests that the add_hybrid_height_coordinate_factory method add ssurface
    altitude to the cube."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(3, 4, 5, 6))
    # Get the names for all the coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check the different coordinates that the hybrid_height_coordinate_factory
    # adds doesn't exist yet.
    assert "surface_altitude" not in coord_names
    builder.add_sigma_aux_coord()
    builder.add_model_level_coordinate()
    builder.add_hybrid_height_coordinate_factory(6)
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check new coordinates are there
    assert "surface_altitude" in coord_names


def test_add_hybrid_pressure_coordinate_factory_level_pressure():
    """Tests that the add_hybrid_pressure_coordinate_factory method adds
    level_pressure to the cube."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(3, 4, 5, 6))
    # Get the names for all the coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check the different coordinates that the hybrid_pressure_coordinate_factory
    # adds doesn't exist yet.
    assert "level_pressure" not in coord_names
    builder.add_model_level_coordinate()
    builder.add_sigma_aux_coord()
    builder.add_hybrid_pressure_coordinate_factory()
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check new coordinates are there
    assert "level_pressure" in coord_names


def test_add_hybrid_pressure_coordinate_factory_surface_air_pressure():
    """Tests that the add_hybrid_pressure_coordinate_factory method adds
    surface_air_pressure to the cube."""
    builder = CubeBuilder(iris.coord_systems.GeogCS(6371229.0), shape=(3, 4, 5, 6))
    # Get the names for all the coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check the different coordinates that the hybrid_pressure_coordinate_factory
    # adds doesn't exist yet.
    assert "surface_air_pressure" not in coord_names
    builder.add_model_level_coordinate()
    builder.add_sigma_aux_coord()
    builder.add_hybrid_pressure_coordinate_factory()
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.coords()]
    # Check new coordinates are there
    assert "surface_air_pressure" in coord_names


def test_make_cube_curvilinear_longitude():
    """Tests that longitude is correctly picked up as an auxillary
    coordinate."""
    builder = CubeBuilder(iris.coord_systems.RotatedGeogCS(20, 10), shape=(16, 16))
    # Get the names for all the auxillary coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.aux_coords]
    # Check the different coordinates that the make_cube_curvilinear()
    # adds doesn't exist yet.
    assert "longitude" not in coord_names
    builder.make_cube_curvilinear(iris.coord_systems.RotatedGeogCS(20, 10))
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.aux_coords]
    # Check new coordinates are there
    assert "longitude" in coord_names


def test_make_cube_curvilinear_latitude():
    """Tests that latitude is correctly picked up as an auxillary
    coordinate."""
    builder = CubeBuilder(iris.coord_systems.RotatedGeogCS(20, 10), shape=(16, 16))
    # Get the names for all the auxillary coordinates in the cube
    coord_names = [coord.name() for coord in builder._cube.aux_coords]
    # Check the different coordinates that the make_cube_curvilinear()
    # adds doesn't exist yet.
    assert "latitude" not in coord_names
    builder.make_cube_curvilinear(iris.coord_systems.RotatedGeogCS(20, 10))
    # Get the new list of coordinate names
    coord_names = [coord.name() for coord in builder._cube.aux_coords]
    # Check new coordinates are there
    assert "latitude" in coord_names


def test_derive_crs_default_coordinates():
    """Tests the derive_crs method with the arguments passed in by default within
    the stock methods"""
    crs = CubeBuilder.derive_crs(iris.coord_systems.GeogCS(6371229.0), 90.0, 0.0)
    assert crs == iris.coord_systems.GeogCS(6371229.0)


def test_derive_crs_rotated():
    """Tests that the derive_crs method picks up when a crs should be rotated."""
    crs = CubeBuilder.derive_crs(iris.coord_systems.GeogCS(6371229.0), 80.0, 0.0)
    assert type(crs) is iris.coord_systems.RotatedGeogCS

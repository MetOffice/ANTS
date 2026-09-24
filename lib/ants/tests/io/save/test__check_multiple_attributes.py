# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

from ants.io.save import _check_multiple_attributes


def test_one_element_in_list():
    """Tests that when given a list with one element, that is returned."""
    expected = ["This is the only attribution given. "]
    cube_name = ["a cube with an attribution"]
    actual = _check_multiple_attributes(expected, cube_name)
    assert expected == actual


def test_only_one_Cube_in_list():
    """Tests that when given only one cube name, the attributes are returned."""
    expected = [
        "This is an attribution for some of the data. ",
        "This is a different attribution for the rest of the data.",
    ]
    cube_name = ["a cube with multiple attributions"]
    actual = _check_multiple_attributes(expected, cube_name)
    assert expected == actual


def test_all_elements_in_list_same():
    """Tests that when all elements in list are the same, one is returned."""
    expected = ["This is the only attribution given. "]
    cube_name = ["a cube with an attribution"]
    attribute_list = [
        "This is the only attribution given. ",
        "This is the only attribution given. ",
        "This is the only attribution given. ",
    ]
    actual = _check_multiple_attributes(attribute_list, cube_name)
    assert expected == actual


def test_different_elements_have_cube_names():
    """Tests that when multiple attributes are given, cube names are included."""
    expected = ["cube1 = license 1. \n", "cube2 = license 2. \n"]
    licenses = ["license 1. ", "license 2. "]
    cube_names = ["cube1", "cube2"]
    actual = _check_multiple_attributes(licenses, cube_names)
    assert expected == actual

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import pytest
from ants.tests import stock
from ants.utils.cube import copy_metadata_attributes


def test_adding_new_attribute():
    """Tests that a new attribute will be added to the source cube if it doesn't exist
    already."""
    # Source cube:
    source = stock.geodetic(shape=(1, 2))
    # Reference cube:
    reference = stock.geodetic(shape=(3, 4))
    reference.attributes["license"] = "a test license"
    reference.rename("test cube")
    # Copy the metadata
    copy_metadata_attributes(source, reference)
    assert source.attributes["license"] == "test cube = a test license"


def test_modifying_existing_attribute():
    """Tests that an existing attribute will be modified on the source cube."""
    # Source cube:
    source = stock.geodetic(shape=(1, 2))
    source.attributes["references"] = "a test reference"
    source.rename("source cube")
    # Reference cube
    reference = stock.geodetic(shape=(3, 4))
    reference.attributes["references"] = "another different test reference"
    reference.rename("reference cube")
    # Copy the metadata
    copy_metadata_attributes(source, reference)
    assert (
        source.attributes["references"]
        == "source cube = a test reference\n"
        + "reference cube = another different test reference"
    )


def test_no_reference_attribute():
    """Tests that a source cube attribute with no reference will be left unchanged."""
    # Source cube:
    source = stock.geodetic(shape=(1, 2))
    source.attributes["restrictions"] = "a test restriction"
    # Reference cube
    reference = stock.geodetic(shape=(3, 4))
    # Copy the metadata
    copy_metadata_attributes(source, reference)
    assert source.attributes["restrictions"] == "a test restriction"


def test_non_standard_attribute():
    """Tests that an attribute not in the allowed list is not copied over."""
    # Source cube:
    source = stock.geodetic(shape=(1, 2))
    # Reference cube:
    reference = stock.geodetic(shape=(3, 4))
    reference.attributes["a value not in the allowed list"] = "not in the list"
    reference.rename("test cube")
    # Copy the metadata
    copy_metadata_attributes(source, reference)
    expected_msg = "a value not in the allowed list"
    with pytest.raises(KeyError, match=expected_msg):
        # Check the attribute hasn't been copied over
        source.attributes["a value not in the allowed list"]


def test_different_attribute_list():
    """Tests that a different attribute list will copy over those attributes."""
    # Source cube:
    source = stock.geodetic(shape=(1, 2))
    # Reference cube:
    reference = stock.geodetic(shape=(3, 4))
    reference.attributes["test-attribute"] = "an attribute not in the standard list."
    reference.rename("test cube")
    copy_metadata_attributes(source, reference, metadata_to_copy=["test-attribute"])
    assert (
        source.attributes["test-attribute"]
        == "test cube = an attribute not in the standard list."
    )


def test_same_attributes():
    """Tests that if both cubes have the same attribute, nothing happens."""
    # Source cube:
    source = stock.geodetic(shape=(1, 2))
    source.attributes["restrictions"] = "a test restriction"
    # Reference cube
    reference = stock.geodetic(shape=(3, 4))
    reference.attributes["restrictions"] = "a test restriction"
    # Copy the metadata
    copy_metadata_attributes(source, reference)
    # Check that the attribute is unchanged
    assert source.attributes["restrictions"] == "a test restriction"


def test_different_whitespace():
    """Tests that attributes with different whitespace will be registered as equal."""
    # Source cube:
    source = stock.geodetic(shape=(1, 2))
    source.attributes["restrictions"] = "a test restriction"
    # Reference cube
    reference = stock.geodetic(shape=(3, 4))
    reference.attributes["restrictions"] = "a      test restriction      "
    # Copy the metadata
    copy_metadata_attributes(source, reference)
    # Check that the attribute is unchanged
    assert source.attributes["restrictions"] == "a test restriction"

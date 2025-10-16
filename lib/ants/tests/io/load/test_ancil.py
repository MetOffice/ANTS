# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import tempfile

import ants
import ants.tests
import iris.fileformats
from ants.fileformats.ancil import mule
from ants.io.load import ants_format_agent


def test_correct_specification_used_between_version_3_1_and_version_5_2_filetype():
    """Tests that the correct FileSpecification is being used with an xUM
    Fieldsfile (FF) ancillary"""
    test_file = ants.tests.get_data_path("load_files/middle_um_version_ancil")
    with ants_format_agent():
        with open(test_file, "rb") as buffer:
            used_spec = iris.fileformats.FORMAT_AGENT.get_spec(test_file, buffer)
            assert used_spec.name == "xUM Fieldsfile (FF) ancillary"
            assert used_spec.priority == 4


def test_correct_specification_used_post_version_5_2_filetype():
    """Tests that the correct FileSpecification is being used with an xUM
    Fieldsfile (FF) post v5.2"""
    test_file = ants.tests.get_data_path("load_files/ancil_file_with_pseudo_levels")
    with ants_format_agent():
        with open(test_file, "rb") as buffer:
            used_spec = iris.fileformats.FORMAT_AGENT.get_spec(test_file, buffer)
            assert used_spec.name == "xUM Fieldsfile (FF) post v5.2"
            assert used_spec.priority == 5


def test_correct_specification_used_pre_version_3_1_filetype():
    """Tests that the correct FileSpecification is being used with an xUM
    Fieldsfile (FF) pre v3.1"""
    test_file = ants.tests.get_data_path("load_files/pre_um_3_1_ancil")
    with ants_format_agent():
        with open(test_file, "rb") as buffer:
            used_spec = iris.fileformats.FORMAT_AGENT.get_spec(test_file, buffer)
            assert used_spec.name == "xUM Fieldsfile (FF) pre v3.1"
            assert used_spec.priority == 6


@ants.tests.skip_mule
def test_pseudo_level_order_preserved_ancil():
    """Loads an ancil file, modifies the pseudo levels and saves this to a
    temporary file. The file is loaded and the order of the pseudo levels
    are checked."""
    file_path = ants.tests.get_data_path("load_files/ancil_file_with_pseudo_levels")
    raw_ancil_file = mule.AncilFile.from_file(file_path)
    # Change pseudolevels to non numerical order
    raw_ancil_file.fields[3].lbuser5 = 302
    with tempfile.NamedTemporaryFile() as temp_file:
        raw_ancil_file.to_file(temp_file.name)
        loaded_cube = ants.io.load.load_cube(temp_file.name)
    pseudo_level = loaded_cube.coord("pseudo_level")
    pseudo_level_points = pseudo_level.points.tolist()
    assert pseudo_level_points == [1, 2, 3, 302, 5, 6, 7, 8, 9]


def test_grid_staggering():
    """Loads an ancil file, then tests that the grid staggering attribute has
    been added corretly"""
    file_path = ants.tests.get_data_path("load_files/ancil_file_with_pseudo_levels")
    cubey = ants.io.load.load_cube(file_path)
    assert cubey.attributes["grid_staggering"] == 6


def test_forecast_period_removal():
    """Loads an ancil file, adds a forecast period coordinate and saves this to a
    temporary file. The file is loaded and the coordinates are checked to ensure
    forecast period is removed.
    """
    file_path = ants.tests.get_data_path("load_files/ancil_file_with_pseudo_levels")
    ancil_data = iris.load_cube(file_path)
    ancil_data.add_aux_coord(iris.coords.AuxCoord(0, long_name="forecast_period"))
    with tempfile.NamedTemporaryFile() as temp_file:
        ants.io.save.ancil(ancil_data, temp_file.name)
        result = ants.io.load.load_cube(temp_file.name)
    result_coords = [c.name() for c in result.coords()]
    assert "forecast_period" not in result_coords


def test_forecast_reference_time():
    """Loads an ancil file, add a forecast reference time coordinate and saves this to
    a temporary file. The file is loaded and the coordinates are checked to ensure
    forecast reference time is removed.
    """
    file_path = ants.tests.get_data_path("load_files/ancil_file_with_pseudo_levels")
    ancil_data = iris.load_cube(file_path)
    ancil_data.add_aux_coord(
        iris.coords.AuxCoord(0, long_name="forecast_reference_time")
    )
    with tempfile.NamedTemporaryFile() as temp_file:
        ants.io.save.ancil(ancil_data, temp_file.name)
        result = ants.io.load.load_cube(temp_file.name)
    result_coords = [c.name() for c in result.coords()]
    assert "forecast_reference_time" not in result_coords

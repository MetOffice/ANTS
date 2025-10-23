# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import tempfile

import ants.tests
import iris.fileformats
import pytest
from ants.io.load import ants_format_agent


def test_correct_pp_specification_used():
    """Tests that the correct FileSpecification is being used with a pp file."""
    test_file = ants.tests.get_data_path("load_files/contains_pseudo_levels.pp")
    with ants_format_agent():
        with open(test_file, "rb") as buffer:
            used_spec = iris.fileformats.FORMAT_AGENT.get_spec(test_file, buffer)
            assert used_spec.name == "UM Post Processing file (PP)"
            assert used_spec.priority == 6


@ants.tests.skip_mule
def test_pseudo_level_order_preserved():
    """Loads a pp file, modifies the pseudo levels and saves this to a temporary file.
    The file is loaded and the order of the pseudo levels are checked."""
    import mule.pp
    file_path = ants.tests.get_data_path("load_files/contains_pseudo_levels.pp")
    pp_fields = mule.pp.fields_from_pp_file(file_path)
    # Change pseudolevels to non numerical order
    pp_fields[3].lbuser5 = 302
    with tempfile.NamedTemporaryFile(suffix=".pp") as temp_file:
        mule.pp.fields_to_pp_file(temp_file.name, pp_fields)
        loaded_cube = ants.io.load.load_cube(temp_file.name)
    pseudo_level = loaded_cube.coord("pseudo_level")
    pseudo_level_points = pseudo_level.points.tolist()
    assert pseudo_level_points == [1, 2, 3, 302, 5, 6, 7, 8, 9]


@ants.tests.skip_mule
@pytest.mark.xfail
def test_pseudo_level_orders_with_iris():
    """Loads a pp file, modifies the pseudo levels and saves this to a temporary file.
    The file is loaded with iris and the order of the pseudo levels are checked."""
    file_path = ants.tests.get_data_path("load_files/contains_pseudo_levels.pp")
    import mule.pp
    pp_fields = mule.pp.fields_from_pp_file(file_path)
    # Change pseudolevels to non numerical order
    pp_fields[3].lbuser5 = 302
    with tempfile.NamedTemporaryFile(suffix=".pp") as temp_file:
        mule.pp.fields_to_pp_file(temp_file.name, pp_fields)
        loaded_cube = iris.load_cube(temp_file.name)
    pseudo_level = loaded_cube.coord("pseudo_level")
    pseudo_level_points = pseudo_level.points.tolist()
    assert pseudo_level_points == [1, 2, 3, 302, 5, 6, 7, 8, 9]


def test_forecast_period_removal():
    """Loads a pp file, adds a forecast period coordinate and saves this to a
    temporary file. The file is loaded and the coordinates are checked to ensure
    forecast period is removed.
    """
    file_path = ants.tests.get_data_path("load_files/contains_pseudo_levels.pp")
    pp_data = iris.load_cube(file_path)
    pp_data.add_aux_coord(iris.coords.AuxCoord(0, long_name="forecast_period"))
    with tempfile.NamedTemporaryFile(suffix=".pp") as temp_file:
        iris.save(pp_data, temp_file.name)
        result = ants.io.load.load_cube(temp_file.name)
    result_coords = [c.name() for c in result.coords()]
    assert "forecast_period" not in result_coords


def test_forecast_reference_time():
    """Loads a pp file, add a forecast reference time coordinate and saves this to a
    temporary file. The file is loaded and the coordinates are checked to ensure
    forecast reference time is removed.
    """
    file_path = ants.tests.get_data_path("load_files/contains_pseudo_levels.pp")
    pp_data = iris.load_cube(file_path)
    pp_data.add_aux_coord(iris.coords.AuxCoord(0, long_name="forecast_reference_time"))
    with tempfile.NamedTemporaryFile(suffix=".pp") as temp_file:
        iris.save(pp_data, temp_file.name)
        result = ants.io.load.load_cube(temp_file.name)
    result_coords = [c.name() for c in result.coords()]
    assert "forecast_reference_time" not in result_coords

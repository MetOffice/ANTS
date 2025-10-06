# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

import warnings

import ants
import ants.tests
import iris.fileformats
from ants.fileformats.namelist import apply_um_conventions
from ants.fileformats.namelist.umgrid import CAPGridRegular, VerticalLevels
from ants.io.load import ants_format_agent

try:
    from f90nml import Namelist
except Exception as _F90NML_IMPORT_ERROR:
    f90nml = None
    msg = (
        ' {}\nUnable to import "f90nml", proceeding without the '
        "capabilities it provides.  See install.rst"
    )
    warnings.warn(msg.format(str(_F90NML_IMPORT_ERROR)))


def test_correct_specification_used_horizontal_namelist():
    """Tests that the correct FileSpecification is being used with a horizontal
    namelist. This wrapped in the same context manager that is used to
    temporarily modify the iris FORMAT_AGENT when ants.io.load is called"""
    test_file = ants.tests.get_data_path("load_files/horizontal_namelist")
    with ants_format_agent():
        with open(test_file, "rb") as buffer:
            used_spec = iris.fileformats.FORMAT_AGENT.get_spec(test_file, buffer)
            assert used_spec.name == "Namelist horizontal definition"
            assert used_spec.priority == 4


def test_correct_specification_used_vertical_namelist():
    """Tests that the correct FileSpecification is being used with a vertical
    namelist."""
    test_file = ants.tests.get_data_path("load_files/vertical_namelist")
    with ants_format_agent():
        with open(test_file, "rb") as buffer:
            used_spec = iris.fileformats.FORMAT_AGENT.get_spec(test_file, buffer)
            assert used_spec.name == "Namelist vertical definition"
            assert used_spec.priority == 4


def test_horizontal_namelist_load():
    """Test calling the load function will give the same results as
    manually creating the cube."""
    test_file = ants.tests.get_data_path("load_files/horizontal_namelist")
    # Generate a basic cube the same as would be done in the core code
    # if given this file
    groups = {
        "grid": Namelist(
            [
                ("points_lambda_targ", 96),
                ("points_phi_targ", 73),
                ("lambda_origin_targ", 0.0),
                ("phi_origin_targ", 90.0),
                ("phi_pole", 90.0),
                ("lambda_pole", 0.0),
                ("rotated", False),
                ("delta_lambda_targ", 3.75),
                ("delta_phi_targ", 2.5),
                ("igrid_targ", 3),
            ]
        )
    }
    constructed_cube = CAPGridRegular(groups).get_cube()
    apply_um_conventions(constructed_cube)
    loaded_cube = ants.io.load.load(test_file)[0]
    assert loaded_cube == constructed_cube


def test_vertical_namelist_load():
    """Test calling the load function will give the same results as
    manually creating the cube."""
    test_file = ants.tests.get_data_path("load_files/vertical_namelist")
    # Generate a basic cube the same as would be done in the core code
    # if given this file
    groups = {
        "vertlevs": Namelist(
            [
                ("z_top_of_model", 39254.833576),
                ("first_constant_r_rho_level", 30),
                (
                    "eta_theta",
                    [
                        0.0,
                        0.0005095,
                        0.002038,
                        0.0045854,
                        0.0081519,
                        0.0127373,
                        0.0183417,
                        0.0249651,
                        0.0326074,
                        0.0412688,
                        0.0509491,
                        0.0616485,
                        0.0733668,
                        0.086104,
                        0.0998603,
                        0.1146356,
                        0.1304298,
                        0.147243,
                        0.1650752,
                        0.1839264,
                        0.2037966,
                        0.2246857,
                        0.2465938,
                        0.2695209,
                        0.293467,
                        0.3184321,
                        0.3444162,
                        0.3714396,
                        0.3998142,
                        0.4298913,
                        0.4620737,
                        0.4968308,
                        0.534716,
                        0.5763897,
                        0.6230643,
                        0.6772068,
                        0.7443435,
                        0.8383348,
                        1.0,
                    ],
                ),
                (
                    "eta_rho",
                    [
                        0.0002547,
                        0.0012737,
                        0.0033117,
                        0.0063686,
                        0.0104446,
                        0.0155395,
                        0.0216534,
                        0.0287863,
                        0.0369381,
                        0.046109,
                        0.0562988,
                        0.0675076,
                        0.0797354,
                        0.0929822,
                        0.1072479,
                        0.1225327,
                        0.1388364,
                        0.1561591,
                        0.1745008,
                        0.1938615,
                        0.2142411,
                        0.2356398,
                        0.2580574,
                        0.281494,
                        0.3059496,
                        0.3314242,
                        0.3579279,
                        0.3856269,
                        0.4148527,
                        0.4459825,
                        0.4794523,
                        0.5157734,
                        0.5555529,
                        0.599727,
                        0.6501355,
                        0.7107751,
                        0.7913392,
                        0.9191674,
                    ],
                ),
            ]
        )
    }
    constructed_cube = VerticalLevels(groups).get_cube(True)
    loaded_cube = ants.io.load.load(test_file)[0]
    assert loaded_cube == constructed_cube

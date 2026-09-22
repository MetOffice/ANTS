# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests.stock
from ants.utils.cube import is_single_level


def test_geodetic():
    cube = ants.tests.stock.geodetic((5, 5))
    assert is_single_level(cube) is True


def test_geodetic_transposed():
    cube = ants.tests.stock.geodetic((5, 5))
    cube.transpose()
    assert is_single_level(cube) is True


def test_simple_4d_with_hybrid_height():
    cube = ants.tests.stock.simple_4d_with_hybrid_height()
    assert is_single_level(cube) is False


def test_simple_3d_time_varying():
    cube = ants.tests.stock.simple_3d_time_varying()
    assert is_single_level(cube) is False


def test_time_and_latitude():
    # construct cube to have time and latitude coordinates only
    cube = ants.tests.stock.simple_3d_time_varying()[..., 0]
    assert cube.ndim == 2
    assert is_single_level(cube) is False

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.io.save as save
import ants.tests
import ants.utils
import iris.cube


def test_multiple_cubes_different_history():
    foo = ants.tests.stock.geodetic([2, 2])
    foo.rename("foo")
    foo_history = "1985-01-01T00:00:00: foo history"
    foo.attributes["history"] = foo_history

    bar = ants.tests.stock.geodetic([2, 2])
    bar.rename("bar")
    bar_history = "1985-01-01T00:12:00: bar history"
    bar.attributes["history"] = bar_history

    cubes = ants.utils.cube.as_cubelist(foo)
    cubes.append(bar)

    save._update_history_cmd(cubes)

    for acube in cubes:
        assert foo_history in acube.attributes["history"]
        assert bar_history in acube.attributes["history"]


def test_single_cube_no_history_gain_history():
    foo = ants.tests.stock.geodetic([2, 2])
    foo.rename("foo")
    assert foo.attributes == {}
    save._update_history_cmd(foo)
    assert "history" in foo.attributes


def test_single_cube_append_history():
    foo = ants.tests.stock.geodetic([2, 2])
    foo.rename("foo")
    foo_history = "1985-01-01T00:00:00: foo history"
    foo.attributes["history"] = foo_history

    save._update_history_cmd(foo)
    assert foo_history in foo.attributes["history"]
    assert foo.attributes["history"] != foo_history


def test_one_cube_histoy():
    """Tests that if only one cube in a CubeList has history, all cubes will get it."""
    cube1 = ants.tests.stock.geodetic([2, 2])
    cube1.attributes["history"] = "the history of cube1"
    cube2 = ants.tests.stock.geodetic([2, 2])
    cube3 = ants.tests.stock.geodetic([2, 2])
    cubelist = iris.cube.CubeList([cube1, cube2, cube3])
    save._update_history_cmd(cubelist)
    assert cube3.attributes["history"] == cube1.attributes["history"]

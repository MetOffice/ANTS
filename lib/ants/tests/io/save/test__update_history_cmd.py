# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.io.save as save
import ants.tests
import ants.utils


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

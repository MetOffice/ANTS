# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import copy
import unittest.mock as mock

import ants.tests
import iris
from ants.io.save import _update_history_cmd as update_history_cmd


class TestAll(ants.tests.TestCase):
    def setUp(self):
        self.cube = iris.cube.Cube(0)
        self.another_cube = iris.cube.Cube(0)
        self.isodate_pattern = r"\d{4,4}-\d{2,2}-\d{2,2}T\d{2,2}:\d{2,2}:" r"\d{2,2}: "
        patch = mock.patch(
            "sys.argv", new=["/path/to/program/executable", "arg1", "arg2"]
        )
        self.patch_sysarg = patch.start()
        self.addCleanup(patch.stop)

    def test_commands(self):
        update_history_cmd(self.cube)
        pattern = self.isodate_pattern + "executable arg1 arg2"
        self.assertRegex(self.cube.attributes["history"], pattern)

    def test_user_provided_contextual_information(self):
        stub_config = copy.copy(ants.config.GlobalConfiguration())
        stub_config.__init__()
        stub_config["ants_metadata"]["history"] = "user supplied string"
        patch = mock.patch("ants.config.CONFIG", new=stub_config)
        with patch:
            update_history_cmd(self.cube)
        pattern = (
            self.isodate_pattern + "executable arg1 arg2 " + r"\(user supplied string\)"
        )
        self.assertRegex(self.cube.attributes["history"], pattern)

    def test_cubes_with_same_history(self):
        history_string = "Add history for test purposes"
        self.cube.attributes["history"] = history_string
        self.another_cube.attributes["history"] = history_string
        self.assertIsNone(
            update_history_cmd(iris.cube.CubeList([self.cube, self.another_cube]))
        )

    def test_cubes_with_different_history(self):
        history_string = "Add history for test purposes"
        another_history_string = "Add a different history string for test purposes"
        self.cube.attributes["history"] = history_string
        self.another_cube.attributes["history"] = another_history_string
        cubes = iris.cube.CubeList([self.cube, self.another_cube])
        update_history_cmd(cubes)
        for acube in cubes:
            self.assertIn(history_string, acube.attributes["history"])
            self.assertIn(another_history_string, acube.attributes["history"])

# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import os
from unittest import mock

import ants
import ants.tests
import iris
from ants.decomposition import _FileCleanup
from ants.utils.cube import _delete_temporary_file, defer_cube


def _cleanup(cube):
    if isinstance(cube, iris.cube.Cube):
        cubes = iris.cube.CubeList([cube])
    else:
        cubes = cube
    for cc in cubes:
        cc._fh_cleanup = _FileCleanup(cc._fh)


class TestAll(ants.tests.TestCase):
    @ants.tests.enable_all_lazy_data
    def test_cube(self):
        cube = iris.cube.Cube([0])
        self.assertFalse(cube.has_lazy_data())
        cube = defer_cube(cube)
        _cleanup(cube)
        self.assertTrue(cube.has_lazy_data())

    @ants.tests.enable_all_lazy_data
    def test_cubes(self):
        cube = [iris.cube.Cube([0]), iris.cube.Cube([1])]
        cubes = defer_cube(cube)
        _cleanup(cubes)
        self.assertIs(len(cubes), 2)
        for cube in cubes:
            self.assertTrue(cube.has_lazy_data())

    def test_slice_cube(self):
        # Show that slicing our cube won't remove the temporary data as long
        # as keep onto the original cube.
        cube = iris.cube.Cube([0, 1])
        cube = defer_cube(cube)
        _cleanup(cube)

        filename = cube._fh
        cube[0].data
        self.assertTrue(os.path.exists(filename))

    def test_no_history_update(self):
        cube = iris.cube.Cube([0, 1])
        with mock.patch("ants.io.save._update_history_cmd") as mock_history:
            defer_cube(cube)
        mock_history.assert_not_called()

    # These mocks are to remove the creation of temporary file, since this
    # test is going to disable the deletion of that temporary file:
    @mock.patch("ants.utils.cube.save")
    @mock.patch("ants.io.load.load_cube")
    def test_delete_registered_with_atexit(self, *args):
        cube = iris.cube.Cube([0, 1])
        # This mock sets up testing that the atexit.register is called with
        # the right filename:
        with mock.patch(
            "ants.utils.cube.tempfile.NamedTemporaryFile", return_value=MockTempFile()
        ):
            # And this mock is the one that checks we're calling
            # atexit.register correctly:
            with mock.patch("atexit.register") as mock_register:
                defer_cube(cube)
        mock_register.assert_called_once_with(
            ants.utils.cube._delete_temporary_file, "mock_temp_file"
        )

    def test_delete_temporary_file(self):
        """If there is a file, remove it."""
        with mock.patch("os.remove") as mock_remove:
            _delete_temporary_file("foo")
        mock_remove.assert_called_once_with("foo")

    def test_delete_temporary_file_error(self):
        """If there is not a file, do nothing."""
        with mock.patch("os.remove", side_effect=FileNotFoundError):
            self.assertIsNone(_delete_temporary_file("foo"))


class MockTempFile:
    """
    Mock temporary file that sets up the name property for testing, but has no
    functionality.

    The name property is set to the value 'mock_temp_file'.

    """

    def __init__(self, suffix=None):
        self.name = "mock_temp_file"

    def close(self):
        pass


if __name__ == "__main__":
    ants.tests.main()

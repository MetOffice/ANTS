# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest
import unittest.mock as mock

import ants.tests
from ants.fileformats.namelist import f90nml, load_cap_horizontal


@unittest.skipIf(f90nml is None, "f90nml package not available")
class TestExceptions_f90nml(ants.tests.TestCase):
    """f90nml performs no meaningful exception handling so we wrap it."""

    def setUp(self):
        patch = mock.patch("f90nml.read")
        self.patch_f90nml = patch.start()
        self.addCleanup(patch.stop)

    def test_f90nml_returns_none(self):
        self.patch_f90nml.return_value = None
        msg = 'Invalid Fortran namelist file: "dummy_filename" no groups ' "found."
        with self.assertRaisesRegex(IOError, msg):
            next(load_cap_horizontal("dummy_filename"))

    def test_f90nml_raises_exception(self):
        exceptions = [StopIteration, ValueError, AssertionError]

        msg = 'Invalid Fortran namelist file: "dummy_filename".'
        for exception in exceptions:
            self.patch_f90nml.side_effect = exception
            with self.assertRaisesRegex(IOError, msg):
                next(load_cap_horizontal("dummy_filename"))


class TestExceptions_namelist(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.fileformats.namelist._read_namelist")
        self.patch_read_namelist = patch.start()
        self.addCleanup(patch.stop)

    def test_duplicate_groups(self):
        # Handling of the case where we return two groups with the same name.
        # Since f90nml returns dictionaries, this can only happen when parsing
        # more than one file.
        filenames = ["dummy_filename1", "dummy_filename2"]
        self.patch_read_namelist.side_effect = [{"group1": 1}, {"group1": 2}]
        msg = "Cannot handle duplicate namelist groups."
        with self.assertRaisesRegex(RuntimeError, msg):
            next(load_cap_horizontal(filenames))

    def test_missing_any_valid_group(self):
        self.patch_read_namelist.return_value = {"group1": 1}
        msg = "No supported groups found"
        with self.assertRaisesRegex(ValueError, msg):
            next(load_cap_horizontal("dummy_filename"))


class TestInterface(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.fileformats.namelist._read_namelist")
        self.patch_read_namelist = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.fileformats.namelist.CAPGridRegular")
        self.patch_CAPGrid = patch.start()
        self.patch_CAPGrid().get_cube.return_value = mock.sentinel.cube
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.fileformats.namelist.apply_um_conventions")
        self.patch_um_concentions = patch.start()
        self.addCleanup(patch.stop)

    def test_apply_um_conventions_call(self):
        self.patch_read_namelist.return_value = {"grid": mock.sentinel.grid}
        next(load_cap_horizontal("dummy_filename"))
        self.patch_um_concentions.assert_called_once_with(mock.sentinel.cube)

    def test_callback_arguments(self):
        groups = {"grid": mock.sentinel.grid}
        groups2 = {"grid2": mock.sentinel.grid}
        self.patch_read_namelist.side_effect = [groups, groups2]

        my_callback = mock.Mock()

        with mock.patch("iris.io.run_callback") as run_callback_patch:
            next(
                load_cap_horizontal(
                    ["dummy_filename", "dummy_filename2"], callback=my_callback
                )
            )
        run_callback_patch.assert_called_once_with(
            my_callback,
            mock.sentinel.cube,
            {"grid": mock.sentinel.grid, "grid2": mock.sentinel.grid},
            ["dummy_filename", "dummy_filename2"],
        )


if __name__ == "__main__":
    ants.tests.main()

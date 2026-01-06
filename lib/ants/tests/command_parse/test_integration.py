# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Stub doc for testing.
"""
import argparse
import unittest.mock as mock

import ants.tests
from ants import exceptions
from ants.command_parse import AntsArgParser


class TestAntsArgParser(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.config.CONFIG.parse_configuration")
        self.mock_config = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.config.filepath_readable")
        self.mock_filepath_readable = patch.start()
        self.mock_filepath_readable.side_effect = lambda x: x
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.config.dirpath_writeable")
        self.mock_dirpath_writeable = patch.start()
        self.mock_dirpath_writeable.side_effect = lambda x: x
        self.addCleanup(patch.stop)

    def test_default_args(self):
        """Tests that the default arguments are as expected."""
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lsm",
            "-o",
            "/path/to/output",
        ]

        def path_check(filename, **kwargs):
            return filename

        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=True)
            args = parser.parse_args()

        target_args = argparse.Namespace(
            ants_config=None,
            land_threshold=None,
            target_lsm="/path/to/lsm",
            output="/path/to/output",
            sources=["/path/to/source"],
            netcdf_only=False,
            ignore_metadata_files=False,
        )
        self.assertFalse(self.mock_config.called)
        self.assertEqual(args, target_args)

    def test_add_args(self):
        """Tests that an argument can be added to the parser."""
        new = ["program", "/path/to/source", "-o", "/path/to/output", "new_arg_value"]
        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser()
            parser.add_argument("new_arg")
            args = parser.parse_args()
        target_args = argparse.Namespace(
            sources=["/path/to/source"],
            output="/path/to/output",
            ants_config=None,
            netcdf_only=False,
            ignore_metadata_files=False,
            new_arg="new_arg_value",
        )
        self.assertEqual(args, target_args)

    def test_parse_docs(self):
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lbm",
            "-o",
            "/path/to/output",
        ]
        target_doc = "\nStub doc for testing.\n"
        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser()
        self.assertEqual(parser.description, target_doc)

    def test_no_lbm(self):
        new = ["program", "/path/to/source", "-o", "/path/to/output"]
        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=False)
            args = parser.parse_args()
        self.assertIs(args.ants_config, None)

    def test_missing_lbm(self):
        new = ["program", "/path/to/source", "-o", "/path/to/output"]
        with mock.patch("sys.argv", new=new):
            with mock.patch("sys.exit") as sys_exit:
                with mock.patch("sys.stderr"):
                    parser = AntsArgParser(target_lsm=True)
                    parser.parse_args()
        sys_exit.assert_called_once_with(2)

    def test_configuration_parse(self):
        config_path = "/path/to/config/file"
        new = [
            "program",
            "/path/to/source",
            "-o",
            "/path/to/output",
            "--ants-config",
            config_path,
        ]
        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=False)
            parser.parse_args()
        self.mock_config.assert_called_once_with(config_path)

    def test_output_directory(self):
        new = ["program", "/path/to/source", "-o", "/path/to/output/file.nc"]
        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=False)
            args = parser.parse_args()
        self.assertEqual(args.output, "/path/to/output/file.nc")
        self.mock_dirpath_writeable.assert_called_once_with("/path/to/output/file.nc")

    def test_invalid_output_args(self):
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lsm",
            "-o",
            "/path/to/source",
        ]

        with mock.patch("sys.argv", new=new):
            with self.assertRaises(exceptions.InvalidOutputPathException):
                parser = AntsArgParser(target_lsm=True)
                parser.parse_args()

    def test_invalid_output_same_file(self):
        new = ["program", "/path/to/source/file.nc", "-o", "/path/to/source/file.nc"]
        with mock.patch("sys.argv", new=new):
            with self.assertRaises(exceptions.InvalidOutputPathException):
                parser = AntsArgParser(target_lsm=False)
                parser.parse_args()
        self.mock_dirpath_writeable.assert_called_once()

    def test_time_constraint_args(self):
        """Tests that using time constraint arguments will be correctly parsed."""
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lbm",
            "-o",
            "/path/to/output",
            "--begin",
            "2016",
            "--end",
            "2021",
        ]

        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=True, time_constraints=True)
            args = parser.parse_args()

        target_args = argparse.Namespace(
            ants_config=None,
            land_threshold=None,
            target_lsm="/path/to/lbm",
            output="/path/to/output",
            sources=["/path/to/source"],
            begin=2016,
            end=2021,
            netcdf_only=False,
            ignore_metadata_files=False,
        )
        self.assertFalse(self.mock_config.called)
        self.assertEqual(args, target_args)

    def test_time_constraint_flags(self):
        """Tests that using time constraint flags will be correctly parsed."""
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lbm",
            "-o",
            "/path/to/output",
            "-b",
            "1990",
            "-e",
            "1996",
        ]

        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=True, time_constraints=True)
            args = parser.parse_args()

        target_args = argparse.Namespace(
            ants_config=None,
            land_threshold=None,
            target_lsm="/path/to/lbm",
            output="/path/to/output",
            sources=["/path/to/source"],
            begin=1990,
            end=1996,
            netcdf_only=False,
            ignore_metadata_files=False
        )
        self.assertFalse(self.mock_config.called)
        self.assertEqual(args, target_args)

    def test_time_constraint_input(self):
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lbm",
            "-o",
            "/path/to/output",
            "--begin",
            "21",
            "--end",
            "16",
        ]

        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=True, time_constraints=True)
            with self.assertRaises(exceptions.TimeConstraintFormatException):
                parser.parse_args()

    def test_time_constraint_args_order(self):
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lbm",
            "-o",
            "/path/to/output",
            "--begin",
            "2021",
            "--end",
            "2016",
        ]

        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=True, time_constraints=True)
            with self.assertRaises(exceptions.TimeConstraintUnorderedException):
                parser.parse_args()

    def test_both_time_constraints_exist(self):
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lbm",
            "-o",
            "/path/to/output",
            "--begin",
            "2016",
        ]

        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=True, time_constraints=True)
            with self.assertRaises(exceptions.TimeConstraintMissingException):
                parser.parse_args()

    def test_set_ignore_metadata_files_flag(self):
        "Tests that ignore_metadata_files will be set to True when passed in."
        new = [
            "program",
            "/path/to/source",
            "--target-lsm",
            "/path/to/lsm",
            "-o",
            "/path/to/output",
            "--ignore-metadata-files"
        ]
        with mock.patch("sys.argv", new=new):
            parser = AntsArgParser(target_lsm=True)
            args = parser.parse_args()

        target_args = argparse.Namespace(
            ants_config=None,
            land_threshold=None,
            target_lsm="/path/to/lsm",
            output="/path/to/output",
            sources=["/path/to/source"],
            netcdf_only=False,
            ignore_metadata_files=True,
        )
        self.assertFalse(self.mock_config.called)
        self.assertEqual(args, target_args)

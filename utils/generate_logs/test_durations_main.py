# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import argparse
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from durations_main import (
    parse_arguments,
    valid_file,
    valid_output_file_name,
    validate_sql_lite_db,
)


class TestArgparseCustomTypeCheckers:
    """Test the custom argparse ``type`` checker functions."""

    @pytest.mark.parametrize(
        "output_file_path",
        [
            ("output_with_no_suffix"),
            ("output.txt"),
            ("output.md"),
            ("output.tiff"),
            ("output_with.double.suffix"),
        ],
    )
    def test_valid_output_file_name_does_not_raise_for_a_valid_file_name(
        self, output_file_path
    ):
        """Test a valid file path does not raise an error.

        The output_file_path is located in a tempfile.TemporaryDirectory then cast as a
        string to replicate the user's argparse input.
        """
        with tempfile.TemporaryDirectory() as temp_directory:
            file_name = Path(temp_directory) / output_file_path
            actual = valid_output_file_name(str(file_name))
            assert actual == file_name

    def test_valid_output_file_name_returns_a_path_object(self):
        """Test a valid file path is returned as a Path object."""
        with tempfile.TemporaryDirectory() as temp_directory:
            actual = valid_output_file_name(str(Path(temp_directory) / "output.txt"))
            assert isinstance(actual, Path)

    def test_valid_output_file_name_raises_for_a_directory(self):
        """Test a directory raises the expected error."""
        with tempfile.TemporaryDirectory() as temp_directory:
            with pytest.raises(argparse.ArgumentTypeError):
                valid_output_file_name(temp_directory)

    def test_valid_output_file_name_raises_for_an_invalid_parent(self):
        """Test a file path with an invalid parent directory raises the expected
        error.
        """
        with tempfile.TemporaryDirectory() as temp_directory:
            output_file_name = Path(temp_directory) / "invalid_directory" / "output.txt"
            with pytest.raises(argparse.ArgumentTypeError):
                valid_output_file_name(output_file_name)

    def test_valid_file_does_not_raise_for_a_valid_file_path(self):
        """Test a valid file does not raise an error.

        The test creates a synthetic ``temp_txt_file`` in a ``TemporaryDirectory`` where
        the path is a Pathlib path object. Synthetic text is written to the file. To
        replicate a user's input, ``temp_txt_file`` is passed as a string.
        """
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_txt_file = Path(temp_directory) / "temp.txt"
            temp_txt_file.write_text("I am some text!")
            actual = valid_file(str(temp_txt_file))
            assert actual == temp_txt_file

    def test_valid_file_returns_a_path_object(self):
        """Test a valid file is returned as a Path object."""
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_txt_file = Path(temp_directory) / "temp.txt"
            temp_txt_file.write_text("I am some text!")
            actual = valid_file(str(temp_txt_file))
            assert isinstance(actual, Path)

    def test_valid_file_raises_for_a_non_existent_file(self):
        """Test a file that doesn't exist raises the expected error."""
        a_directory = "i do not exist"
        with pytest.raises(argparse.ArgumentTypeError):
            valid_file(a_directory)


@pytest.fixture
def mock_sys_argv_valid(synthetic_cylc_db):
    """Fixture to patch `sys.argv` with valid command line arguments.

    The fixture uses ``unittest.mock.patch`` to mock ``sys.argv`` with a list of
    arguments valid for ``parse_arguments``.

    The ``mock_sys_argv_fixture`` uses the ``synthetic_cylc_db`` fixture as a valid
    SQLite file and a creates a valid output directory ``synthetic_dir`` in a
    ``TemporaryDirectory`. These are both pathlib Paths which are passed as strings to
    replicate a user's command line input.

    Yield is used to avoid setting the value of ``sys.argv`` for all tests in the
    module, and to allow the ``tempfile.TemporaryDirectory`` context manager
    to stay open for the duration of a test.

    """
    with tempfile.TemporaryDirectory() as temp_directory:
        synthetic_output_file = Path(temp_directory) / "output.txt"
        valid_cli_arguments = [
            "executable-or-executed-script",
            str(synthetic_cylc_db),
            str(synthetic_output_file),
            "trac",
        ]
        with patch("sys.argv", valid_cli_arguments):
            yield


class TestParseArguments:
    """
    Test ``parse_arguments``.

    Argparse ``type`` and ``choice`` validation are not tested. They are assumed to work
    as expected

    """

    def test_parsed_arguments_return_type(self, mock_sys_argv_valid):
        """Test return type is a Namespace."""
        parsed_arguments = parse_arguments()
        assert isinstance(parsed_arguments, argparse.Namespace)

    def test_positional_argument_path_to_cylc_db_valid(self, mock_sys_argv_valid):
        """Test a valid argument for ``path_to_cylc_db`` passes correctly.

        The assert uses ``pathlib.Path.name`` as ``synthetic_cylc_db`` is created in
        ``tempfile.TempDirectory`` and the full path is not available.
        """
        parsed_arguments = parse_arguments()
        assert parsed_arguments.path_to_cylc_db.name == "synthetic_cylc_db"

    def test_positional_argument_output_file_name_valid(self, mock_sys_argv_valid):
        """Test a valid argument for ``output_file_name`` passes correctly.

        The assert uses ``pathlib.Path.name`` as ``synthetic_dir/output.txt`` is created
        in a ``temp_directory`` and the full path is not available.
        """
        parsed_arguments = parse_arguments()
        assert parsed_arguments.output_file_name.name == "output.txt"

    def test_positional_argument_output_format_trac(self, mock_sys_argv_valid):
        """Test ``trac`` is a valid ``output_format`` value."""
        parsed_arguments = parse_arguments()
        assert parsed_arguments.output_format == "trac"

    def test_positional_argument_output_format_github(self, synthetic_cylc_db):
        """Test ``github`` is a valid ``output_format`` value."""
        with tempfile.TemporaryDirectory() as temp_directory:
            synthetic_output_file = Path(temp_directory) / "output.txt"
            valid_cli_arguments_trac_replaced_by_github = [
                "--executable-or-executed-script",
                str(synthetic_cylc_db),
                str(synthetic_output_file),
                "github",
                "-d 1",
            ]
            with patch("sys.argv", valid_cli_arguments_trac_replaced_by_github):
                parsed_arguments = parse_arguments()
            assert parsed_arguments.output_format == "github"

    def test_default_argument_for_cylc_version(self, mock_sys_argv_valid):
        """Test ``8`` is the ``cylc_version`` value if no argument is CLI arg is passed.

        Also tests that ``8`` is a valid argparse ``choice`` for ``cylc-version``.

        """
        parsed_arguments = parse_arguments()
        assert parsed_arguments.cylc_version == 8

    def test_cylc_seven_is_valid_argument_for_cylc_version(self, synthetic_cylc_db):
        """Test ``7`` is a valid ``cylc_version`` value."""
        with tempfile.TemporaryDirectory() as temp_directory:
            synthetic_output_file = Path(temp_directory) / "output.txt"
            valid_cli_arguments_and_cylc_version_set_to_seven = [
                "--executable-or-executed-script",
                str(synthetic_cylc_db),
                str(synthetic_output_file),
                "trac",
                "-c 7",
                "-d 1",
            ]
            with patch("sys.argv", valid_cli_arguments_and_cylc_version_set_to_seven):
                parsed_arguments = parse_arguments()
            assert parsed_arguments.cylc_version == 7

    def test_duration_flag_default_argument(self, mock_sys_argv_valid):
        """Test the default value of ``duration_flag``."""
        parsed_arguments = parse_arguments()
        assert parsed_arguments.duration_flag == 10

    @pytest.mark.parametrize(
        "valid_input, expected_output",
        [
            (1, 1),
            (100, 100),
            (1000, 1000),
        ],
    )
    def test_duration_flag_valid_arguments(
        self, synthetic_cylc_db, valid_input, expected_output
    ):
        """Test valid arguments return the expected ``duration_flag`` value."""
        with tempfile.TemporaryDirectory() as temp_directory:
            synthetic_output_file = Path(temp_directory) / "output.txt"
            valid_cli_arguments_with_valid_duration_flag = [
                "--executable-or-executed-script",
                str(synthetic_cylc_db),
                str(synthetic_output_file),
                "trac",
                f"-d {valid_input}",
            ]
            with patch("sys.argv", valid_cli_arguments_with_valid_duration_flag):
                parsed_arguments = parse_arguments()
            assert parsed_arguments.duration_flag == expected_output


class TestValidateSqLiteDbFile:
    def test_validate_sql_lite_db_on_valid_sqlite_file(self, synthetic_cylc_db):
        """Test a valid SQLite db passes as valid and returns a pathlib Path object.

        Uses the fixture ``synthetic_cylc_db`` which is a pathlib Path to a SQLite db
        file created in a ``tempfile.TempDirectory``.
        """
        synthetic_cylc_db_path_as_a_string = str(synthetic_cylc_db.resolve())
        actual = validate_sql_lite_db(synthetic_cylc_db_path_as_a_string)
        assert actual is None

    # TODO: This doesn't raises for an empty file? E.g. ``temp_txt_file.touch()``
    def test_validate_sql_lite_db_on_a_txt_file(self):
        """Test a non SQLite file raises an error."""
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_txt_file = Path(temp_directory) / "temp.txt"
            temp_txt_file.write_text("I am some text!")
            with pytest.raises(ValueError):
                validate_sql_lite_db(temp_txt_file)

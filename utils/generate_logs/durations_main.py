#!/usr/bin/env python
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""Generate a log file of cylc workflow test durations.

The module contains an entry point ``main`` function, an argparse ``parse_arguments``,
function argparse ``type`` validator functions and a ``validate_sql_lite_db`` function.

"""
import argparse
import logging
import sqlite3
from pathlib import Path

from durations_extract_format import TableMaker
from durations_logger import logger, set_console_handler_log_level


def valid_output_file_name(output_file_name: str) -> Path:
    """Check a string will resolve to a valid file path. Cast to a pathlib Path.

    The function converts the string to a pathlib Path. It calls the pathlib
    ``expanduser`` method to replace the "~" (if used) and calls the ``resolve`` method
    to make the path absolute. The function confirms that the path isn't a directory and
    checks a "parent" can be ascertained and that the parent is a valid directory.

    No suffix checking is proscribed. The help text suggests the user pass the filename
    with a ".txt" suffix.

    Parameters
    ----------
    output_file_name
        A string that is expected to resolve to a valid file path.

    Returns
    -------
    Path
        The ``output_file_name`` as a Path object.

    Raises
    ------
    ArgumentTypeError
        If ``output_file_name`` is a directory, or has a parent that is an invalid
        directory.
    """
    output_file_name_as_a_path_object = Path(output_file_name).expanduser().resolve()

    if output_file_name_as_a_path_object.is_dir():
        raise argparse.ArgumentTypeError(
            f"'{output_file_name_as_a_path_object}' is directory, not a file."
        )
    parent = output_file_name_as_a_path_object.parent

    if not parent.is_dir():
        raise argparse.ArgumentTypeError(
            f"'{output_file_name_as_a_path_object}' seems to have the parent '{parent}'"
            " which does not appear to be a valid directory"
        )

    return output_file_name_as_a_path_object


def valid_file(path_to_a_file: str) -> Path:
    """Check a string is a path to a valid file. Cast to a pathlib Path.

    Parameters
    ----------
    path_to_directory
        A string that is expected to be a path to a valid file.

    Returns
    -------
    Path
        The ``path_to_a_file`` as a Path object.

    Raises
    ------
    ArgumentTypeError
        If ``path_to_a_file`` is not a valid path to a file.

    """
    path_to_a_file_as_pathlib_object = Path(path_to_a_file).resolve()
    if not path_to_a_file_as_pathlib_object.is_file():
        raise argparse.ArgumentTypeError(
            f"'{path_to_a_file}' does not appear to be a file"
        )
    return path_to_a_file_as_pathlib_object


def parse_arguments() -> argparse.Namespace:
    """Set up parser and parse command line arguments.

    Each parsed argument is validated by argparse ``type``. The paths ``cylc_db`` and
    ``output_directory`` call custom functions to validate ``type``.

    ``output_format`` and ``cylc`` are additionally validated by argparse ``choice``
    choices.

    Returns
    -------
    Namespace
        The parsed arguments as an argparse Namespace object.

    Examples
    --------
    Example command line usage which would result in parsed arguments:

        $ meow path/to/cylc_db path/to/output_dir trac -c 8 - d 5 -v

    Returns an ``argparse.Namespace`` object with the attributes ``path_to_cylc_db``,
    ``path_to_output_directory``, ``output_format``, ``cylc_version``, ``duration_flag``
    and ``verbosity``.
    """
    parser = argparse.ArgumentParser(
        description="Generate a log of cylc workflow test durations.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "path_to_cylc_db",
        type=valid_file,
        help="Path to a Rose Stem test workflow Cylc db file",
    )
    parser.add_argument(
        "output_file_name",
        type=valid_output_file_name,
        help="Filename to save the formatted output. A .txt suffix is recommended but "
        "not enforced",
    )
    parser.add_argument(
        "output_format",
        type=str,
        choices=["trac", "github"],
        help="The required markup format e.g. trac WikiFormatting or GitHub Markdown",
    )
    parser.add_argument(
        "--cylc-version",
        "-c",
        type=int,
        choices=[7, 8],
        default=8,
        help="Cylc version that created the db (default: 8)",
    )
    parser.add_argument(
        "--duration-flag",
        "-d",
        type=int,
        default=10,
        help="Test durations over this value will be highlighted in the output. Enter a"
        " numeric value in whole minutes (default: 10)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Output debug logging to the console (-v only currently supported)",
    )
    arguments = parser.parse_args()
    return arguments


def validate_sql_lite_db(path_to_a_file: Path) -> None:
    """Validate an SQLite db file using ``PRAGMA quick_check``.

    Note
    ----
    In intended usage ``path_to_file`` is assumed to exist, having passed argparse
    custom ``type`` validation. Attempting to connect with sqlite3 therefore will not
    create a new database. No tear down is required.

    Parameters
    ----------
    path_to_a_file
        Path to an existing file as a pathlib Path object.

    Raises
    ------
    ValueError
        If the provided string is not a valid SQLlite db.

    """
    logger.debug(f"VALIDATING {path_to_a_file} is a SQLite database")
    connection = sqlite3.connect(path_to_a_file)
    cursor = connection.cursor()
    try:
        # Capture the SQLite table names for debugging.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.debug(f"{path_to_a_file} contains: {tables}")
        cursor.execute("PRAGMA quick_check")
    except sqlite3.DatabaseError as error:
        message = (
            "File does not appear to be a valid SQLite database: "
            f"'{path_to_a_file}', {error}"
        )
        logger.critical(message)
        raise ValueError(message)
    finally:
        connection.close()


def main() -> None:
    """Entry point.

    Collects the parsed arguments. Sets the debug level based on the verbose parsed
    argument. Instantiates a TableMaker instance then calls the ``driver`` method. The
    driver method will extract, prepare and format the data. The ``driver`` then outputs
    the final table as a .txt file.

    """
    arguments = parse_arguments()
    if arguments.verbose > 0:
        set_console_handler_log_level(logging.DEBUG)
    logger.debug("==== RUN START ====")
    logger.debug("RUNNING durations_main.main")
    logger.debug(f"Parsed arguments: {arguments}")
    validate_sql_lite_db(arguments.path_to_cylc_db)
    logger.debug("INSTANTIATING TaskDurationsExtractorFormatter")
    task_durations = TableMaker(
        arguments.path_to_cylc_db,
        arguments.output_file_name,
        arguments.output_format,
        arguments.cylc_version,
        arguments.duration_flag,
    )
    task_durations.driver()


if __name__ == "__main__":
    main()

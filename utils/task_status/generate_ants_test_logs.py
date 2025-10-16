"""This is the main script that should be run. It retrieves ANTS test logs from
 a database and writes them to a target directory in the user defined format 
 (Trac or Github)."""

import argparse
from generate_github_summary import generate_github_summary
from generate_trac_summary import generate_trac_summary
from generate_formatted_github_table import generate_formatted_github_table
from generate_formatted_trac_table import generate_formatted_trac_table
from retrieve_task_states import retrieve_task_states
from output_logs_to_file import output_logs_to_file
from verify_file_created import verify_file_created
import os


def parse_arguments():
    """
    Parses the arguments passed to the script via the command line.

    Returns
    -------
    argparse.Namespace object
        Contains the arguments provided by the user.

    Examples
    --------
    >>> arguments = parse_arguments("path/to/db", "output/destination/path", "text_format")
    >>> print(arguments.db_path)
    "path/to/db"
    >>> print(arguments.output_destination)
    "output/destination/path"
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "db_path", type=str, help="The filepath to the cylc run database"
    )
    parser.add_argument(
        "output_destination",
        type=str,
        help="The full target path (and name) where you would like the"
        "generated test log file",
    )
    parser.add_argument(
        "text_format",
        type=str,
        choices=["trac", "gh"],
        help="The type of formatting you would like for " "the text",
    )

    args = parser.parse_args()
    return args


def generate_task_logs(text_format, db_path, output_destination):
    """
    Generates a log file (test_results_logs.txt) from a user defined
    cylc-run database.

    Parameters
    ----------
    text_format : str
        The format of the output file.

    db_path : "str"
        The location of the database to be converted.

    output_destination : str
        The target location where the converted database should be stored.

    Returns
    -------
    None
    """

    # Validate the database file exists
    if not os.path.isfile(db_path):
        raise FileNotFoundError(
            f"No file exists at the database path you provided:\n {db_path}\n"
        )

    # Validate filename doesn't contain special characters other than "."
    special_characters = "!@#$%^&*()-+?£=,<>"
    for character in str(output_destination):
        if character in special_characters:
            raise ValueError(
                f'Please remove the special character ("{character}") you have in your target filepath and try again.'
            )

    rows = retrieve_task_states(db_path)

    if text_format == "trac":

        summary = generate_trac_summary(rows)

        table = generate_formatted_trac_table(rows)

    elif text_format == "gh":

        summary = generate_github_summary(rows)

        table = generate_formatted_github_table(rows)

        output_logs_to_file(output_destination, summary, table)
        verify_file_created(output_destination)


if __name__ == "__main__":

    arguments = parse_arguments()

    generate_task_logs(
        arguments.text_format, arguments.db_path, arguments.output_destination
    )

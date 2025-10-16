# test test output logs are accurate
from tempfile import NamedTemporaryFile, TemporaryDirectory

from output_logs_to_file import output_logs_to_file


def test_output_logs_to_file():

    with TemporaryDirectory() as temporary_output_directory:
        with NamedTemporaryFile(dir=temporary_output_directory) as tmp_file:

            temporary_output_destination = tmp_file.name

            summary = "Synthetic summary."
            table = "Synthetic table."
            expected_output = summary + table

            output_logs_to_file(temporary_output_destination, summary, table)

            with open(temporary_output_destination, "r") as file:
                result = file.read()

    expected = expected_output
    assert result == expected

"""Verify output file was created at user defined destination."""

from pathlib import Path


def verify_file_created(output_destination):
    my_file = Path(output_destination)

    if my_file.is_file():
        print(
            f"\nThe ANTs test logs were successfully written to this"
            f" location:\n{my_file}\n"
        )

    elif not my_file.is_file():
        print(f"\nFailed to generate output file in this location:\n" f"{my_file}\n")

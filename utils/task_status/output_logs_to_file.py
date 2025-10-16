"""Print logs to output file at user defined destination."""


def output_logs_to_file(output_destination, summary, table):
    """
    Writes the test logs file to the chosen destination.

    Parameters
    ----------
    output_destination : str
        The full target directory (including filename).
    summary : str
        The formatted summary text to be written to the output file.
    table : str
        The formatted table to be written to the output file.
    Returns
    -------
    None
        This script writes strings to a user defined output file.

    """

    with open(output_destination, "w") as output_file:
        output_file.write(summary + table)

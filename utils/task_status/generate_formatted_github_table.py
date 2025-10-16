"""Generate formatted table with title from test results database rows."""


def generate_formatted_github_table(rows):
    """
    Generates the table section for the test log output (formatted for Github).

    Parameters
    ----------
    rows : List of tuples consisting of task names and task states.

    Returns
    -------
    final_table : str
        The formatted table section of the test logs.


    """

    failed_tasks = []
    succeeded_tasks = []

    for row in rows:
        if row[1] == "failed":
            failed_tasks.append(f"| **{row[0]}** | **{row[1]}** |")

        elif row[1] == "succeeded":
            succeeded_tasks.append(f"| {row[0]} | {row[1]} |")

    final_table = (
        "## Test Results - Detail ##\n"
        + "| Task Name | Status |\n"
        + "|:-|:-|\n"
        + "\n".join(failed_tasks)
        + "\n"
        + "\n".join(succeeded_tasks)
    )

    return final_table

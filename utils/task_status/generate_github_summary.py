"""Generate formatted summary from ANTS test results database rows."""


def generate_github_summary(rows):
    """
    Generates the summary section for the test log output (formatted for GitHub).

    Parameters
    ----------
    rows : List of tuples consisting of task names and task states.

    Returns
    -------
    str
      The formatted summary section of the test logs.

    """

    succeeded_tasks = 0
    failed_tasks = 0
    make_text_bold = ""

    for row in rows:

        if row[1] == "succeeded":
            succeeded_tasks += 1

        elif row[1] == "failed":
            failed_tasks += 1
            make_text_bold = "**"

    final_summary = (
        "\n\n----\n\n\n"
        "## Test Results - Summary ##\n"
        f"Total tasks run: {len(rows)}\n"
        "| Tasks | Total |\n"
        "|:-|:-|\n"
        f"| Succeeded | {succeeded_tasks} |\n"
        f"| {make_text_bold}Failed{make_text_bold} |"
        f" {make_text_bold}{failed_tasks}{make_text_bold} |\n\n"
    )

    return final_summary

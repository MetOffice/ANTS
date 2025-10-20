from generate_formatted_github_table import generate_formatted_github_table
from synthetic_data import rows_with_a_failure


def test_generate_formatted_github_table():
    expected_output = (
        "## Test Results - Detail ##\n" + "| Task Name | Status |\n" + "|:-|:-|"
        "| **process_1** | "
        "**failed** |\n| process_2 | succeeded |\n| "
        "process_3 | succeeded |"
    )

    actual = generate_formatted_github_table(rows_with_a_failure)
    expected = expected_output
    assert actual == expected

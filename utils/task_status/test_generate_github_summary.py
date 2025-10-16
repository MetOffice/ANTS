from generate_github_summary import generate_github_summary
from synthetic_data import rows_all_succeeded, rows_with_a_failure


def test_generate_github_summary_with_a_failed_task():
    expected_output = (
        "\n\n----\n\n\n"
        "## Test Results - Summary ##\n"
        "Total tasks run: 3\n"
        "| Tasks | Total |\n"
        "|:-|:-|\n"
        "| Succeeded | 2 |\n"
        "| **Failed** | **1** |\n\n"
    )

    actual = generate_github_summary(rows_with_a_failure)
    expected = expected_output
    assert actual == expected


def test_generate_github_summary():
    expected_output = (
        "\n\n----\n\n\n"
        "## Test Results - Summary ##\n"
        "Total tasks run: 3\n"
        "| Tasks | Total |\n"
        "|:-|:-|\n"
        "| Succeeded | 3 |\n"
        "| Failed | 0 |\n\n"
    )

    actual = generate_github_summary(rows_all_succeeded)
    expected = expected_output
    assert actual == expected

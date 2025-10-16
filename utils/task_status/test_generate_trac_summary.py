from generate_trac_summary import generate_trac_summary
from synthetic_data import rows_all_succeeded, rows_with_a_failure


def test_generate_trac_summary_with_a_failed_task():
    expected_output = (
        "\n\n----\n\n\n"
        "=== Test Results - Summary ===\n"
        "Total tasks run: 3\n"
        " || **Task** || **Status** ||\n"
        " || Tasks Succeeded || 2 ||\n"
        " || **Tasks Failed** || **1** ||\n\n"
    )

    actual = generate_trac_summary(rows_with_a_failure)
    expected = expected_output
    assert actual == expected


def test_generate_trac_summary_with_all_tasks_passed():
    expected_output = (
        "\n\n----\n\n\n"
        "=== Test Results - Summary ===\n"
        "Total tasks run: 3\n"
        " || **Task** || **Status** ||\n"
        " || Tasks Succeeded || 3 ||\n"
        " || Tasks Failed || 0 ||\n\n"
    )

    actual = generate_trac_summary(rows_all_succeeded)
    expected = expected_output
    assert actual == expected

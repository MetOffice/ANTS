# test retrieval of values from a mock database
from pathlib import Path

from retrieve_task_states import retrieve_task_states

test_directory_path = Path(__file__).parent.absolute()

db_path = test_directory_path / "fakedb.db"


def test_retrieve_task_states():

    expected_output = [
        ("foo3", "failed"),
        ("foo1", "succeeded"),
        ("foo2", "succeeded"),
        ("foo4", "succeeded"),
    ]

    actual = retrieve_task_states(db_path)
    expected = expected_output
    assert actual == expected

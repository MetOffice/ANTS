# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import sqlite3
import tempfile
from pathlib import Path

import pytest
from synthetic_data_for_testing import SYNTHETIC_TASK_DATA


@pytest.fixture
def synthetic_cylc_db():
    """Create a synthetic db with fifteen rows of data in a ``TemporaryDirectory``.

    The synthetic db will have two tables: ``task_jobs`` and ``task_states``. The
    ``task_jobs`` table contains 16 rows.  The ``task_states`` table contains 15 rows.

    The ``task_jobs`` table contains the task ``install_cold`` twice, replicating two
    runs of this task.  The ``task states`` table excludes the initial run, as a Cylc
    db ``task_states`` table contains each task only once, listed with the task's final
    run.

    Yield is used to allow ``tempfile.TemporaryDirectory`` context manager to stay open
    for the duration of a test.
    """
    with tempfile.TemporaryDirectory() as temp_directory:
        path_to_synthetic_db = Path(temp_directory) / "synthetic_cylc_db"
        connection = sqlite3.connect(path_to_synthetic_db)
        cursor = connection.cursor()
        create_task_jobs_table(cursor)
        create_task_states_table(cursor)
        connection.commit()
        connection.close()
        yield path_to_synthetic_db


def create_task_jobs_table(cursor: sqlite3.Cursor) -> None:
    """Create a table ``task_jobs`` in a SQLite database.

    The function runs an sqlite3 command to create the table. It creates a list of
    tuples containing row data and inserts them into the table with
    ``cursor.executemany`` (which requires data as a list of tuples).

    The ``task_jobs`` table will contain 16 rows of data, including one task -
    "install_cold" - which appears twice. This represents a task which a user has
    manually paused/killed and then re-run. The "submit_num" field is "1" for the
    initial run and "2" for the user initiated re-run.

    Parameters
    ----------
    cursor
        An sqlite3 Cursor connected to a database.

    """
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS task_jobs (name TEXT NOT NULL,
            time_run TEXT NOT NULL, time_run_exit TEXT NOT NULL,
            submit_num TEXT NOT NULL)"""
    )
    rows_to_insert_as_tuples = [
        (row["name"], row["time_run"], row["time_run_exit"], row["submit_num"])
        for row in SYNTHETIC_TASK_DATA
    ]
    cursor.executemany(
        """INSERT INTO task_jobs (name, time_run, time_run_exit, submit_num)
            VALUES (?, ?, ?, ?)""",
        rows_to_insert_as_tuples,
    )


def create_task_states_table(cursor: sqlite3.Cursor) -> None:
    """Create a table ``task_states`` in a SQLite database.

    The function runs an sqlite3 command to create the table. It creates a list of
    tuples containing row data and inserts them into the table with
    ``cursor.executemany`` (which requires data as a list of tuples).

    A Cylc db ``task_states`` table includes each task only once - with "submit_num"
    representing the last submission of that task. To replicate this, the function
    excludes multiple runs of tasks. SYNTHETIC_TASK_DATA includes only one task with
    multiple runs: the initial run of "install_cold" is excluded.

    Parameters
    ----------
    cursor
        An sqlite3 Cursor connected to a database.

    """
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS task_states
            (name TEXT NOT NULL,  submit_num TEXT NOT NULL)"""
    )
    rows_to_insert_as_tuples = [
        (row["name"], row["submit_num"])
        for row in SYNTHETIC_TASK_DATA
        if (row["name"], row["submit_num"]) != ("install_cold", "1")
    ]
    cursor.executemany(
        """INSERT INTO task_states (name, submit_num) VALUES (?, ?)""",
        rows_to_insert_as_tuples,
    )

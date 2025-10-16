"""Returns rows from the selected database."""

import sqlite3


def retrieve_task_states(db_path):
    """
    Retrieves data from a cylc run database file.

    Parameters
    ----------
    db_path : str

    Returns
    -------
    rows : A list of tuples.
        Task names and their task states extracted from the database.

    Examples
    --------
    >>> retrieve_task_states(db_path)
    rows = [('task_foo1', 'status_foo1'), ('task_foo2', 'status_foo2')]

    """
    con = sqlite3.connect(f"{db_path}")
    cur = con.cursor()

    cur.execute("SELECT name, status FROM task_states ORDER BY status;")
    rows = cur.fetchall()

    con.close()
    return rows

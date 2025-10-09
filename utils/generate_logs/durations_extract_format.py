# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""Extract, prepare and format Cylc SQLite db data as a table.

The data is processed as follows:

               ---------         ---------         --------
cylc_db ----> | Extract | ----> | Prepare | ----> | Format | ----> output.txt
               ---------         ---------         --------

This functionality resides in a ``TableMaker`` class with a single public method
``driver``.

``driver`` calls three secondary drivers ``_extract_driver``, ``_prepare_driver`` and
``_format_driver``.

Notes
-----
This design allows for ``TableMaker`` to become a base class. Tables of differing data
could then inherit from ``TableMaker`` e.g ``TaskDurationsTable`` or
``TaskSuccessFailTable``.

``TaskDurationsTable`` and ``TaskSuccessFailTable`` would then implement versions of
``_extract_driver``, ``_prepare_driver`` and ``_format_driver`` tailored to different
data.

Classes:
    TableMaker:         Extract, prepare, format and output a table.
    TaskDurationRow:    Helper dataclass for storing rows of task duration related data.
    DataTable:          Helper dataclass for storing table elements.

"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from durations_logger import logger


@dataclass
class DataTable:
    """A dataclass for the elements of a data table.

    The class attributes are lists of strings of renderable GitHub/Trac markup content.
    Casting to a string converts them into a single, renderable string.

    Parameters
    ----------
    table_summary_section
        A summary of task duration related statistics.
    column_header_row:
        The headers for the table columns.
    formatted_rows:
        The extracted, formatted data as formatted rows.

    """

    table_summary_section: list
    column_header_row: list
    formatted_rows: list

    def __str__(self):
        return "\n".join(
            self.table_summary_section + self.column_header_row + self.formatted_rows
        )


@dataclass
class TaskDurationRow:
    """A dataclass for rows of task duration related data.

    Initialisation requires three columns of data in the "raw" format output by the
    Cylc db. These are ``raw_task_name``, ``raw_time_run`` and ``raw_run_exit``.

    Further columns are added incrementally. (Data within the object isn't overwritten
    to aid extensibility). These rows initialise as None.

    Parameters
    ----------
    raw_task_name
        The Cylc db ``task_name``column in it's original format.
    raw_time_run
        The Cylc db ``time_run`` column in it's original format.
    raw_time_run_exit
        The Cylc db ``time_run_exit`` column in it's original format.
    time_run
        ``raw_time_run`` converted to a datetime object.
    time_run_exit
        ``raw_time_run_exit`` converted to a datetime object.
    run_duration
        The difference between ``time_run`` and ``time_run_exit`` as a
        timedelta object.
    run_duration_baseline
        A comparative  baseline ``run_duration`` for the task as a timedelta
        object.

    """

    raw_task_name: str
    raw_time_run: str
    raw_time_run_exit: str
    time_run: Optional[datetime] = None
    time_run_exit: Optional[datetime] = None
    run_duration: Optional[timedelta] = None
    run_duration_baseline: Optional[timedelta] = None


class CylcDatabaseError(Exception):
    """A custom exception to indicate a problem with the Cylc db.

    To be used with a custom message.

    Parameters
    ----------
    msg : str
        Human readable string describing the exception.
    code : :obj:`int`, optional
        Numeric error code.

    """

    pass


class TableMaker:
    """Extract, prepare and format a Cylc SQLite db as a table.

    The class has a single public method ``driver``. ``driver`` calls three secondary
    drivers ``_extract_driver``, ``_prepare_driver`` and ``_format_driver``.

        ``driver``
            |
            v
      --------------------       ---------------------      -------------------
     | ``extract_driver`` | --> | ``prepare_driver`` | --> | ``format_driver`` |
      --------------------       ---------------------      -------------------
                                                                     |
                                                                     v
                                                                 output.txt
    Attributes
    ----------
    SQL_QUERY_FOR_CYLC_EIGHT : str
        The sqlite3 query for a Cylc 8 db file.
    SQL_QUERY_FOR_CYLC_SEVEN: str
        The sqlite3 query for a Cylc 7 db file.

    """

    _SQL_QUERY_FOR_CYLC_EIGHT = (
        "SELECT task_jobs.name, task_jobs.time_run, task_jobs.time_run_exit "
        "FROM task_jobs "
        "JOIN task_states "
        "ON task_jobs.name = task_states.name "
        "AND task_jobs.submit_num = task_states.submit_num"
    )
    _SQL_QUERY_FOR_CYLC_SEVEN = "Not implemented"

    def __init__(
        self,
        path_to_cylc_db: Path,
        output_file_name: Path,
        output_format: str,
        cylc_version: int,
        duration_flag: int,
    ):
        """Initialiser for a TableMaker instance.

        Parameters are assumed to have passed argparse ``choice`` and ``type``
        validation. ``path_to_cylc_db`` is assumed to have been validated as an SQLite
        file.

        Parameters
        ----------
        path_to_cylc_db
            A path to a valid SQLite database as a pathlib Path.
        output_file_name
            The file name specified by the user as a pathlib Path.
        output_format
            Either "trac" or "github" as a string.
        cylc_version
            Either 7 or 8 as an int.
        duration_flag
            Duration in minutes above which tests results are highlighted.
        """
        self.path_to_cylc_db = path_to_cylc_db
        self.output_file_name = output_file_name
        self.output_format = output_format
        self.cylc_version = cylc_version
        self.duration_flag = duration_flag

    def driver(self) -> None:
        """Driver method to extract, prepare, format and output table data.

        Public method for TableMaker functionality. The method sets the appropriate
        ``sql_query``. The method then calls the drivers for "extract", "prepare" and
        "format" steps. Finally, ``driver`` writes to the result to the
        ``output_file_name``.

        """
        logger.debug("RUNNING driver...")
        sql_query = self._get_sql_query()
        raw_rows = self._extract_driver(sql_query)
        prepared_rows = self._prepare_driver(raw_rows)
        formatted_table_as_string = self._format_driver(prepared_rows)
        self._write_table_to_file(formatted_table_as_string)

    def _get_sql_query(self):
        """Get the ``sql_query`` based on Cylc version passed by the user.

        Returns
        -------
        str
           The appropriate sql_query for the cylc version, from the class constant.

        """
        logger.debug("SETTING SQL QUERY")
        if self.cylc_version == 8:
            sql_query = self._SQL_QUERY_FOR_CYLC_EIGHT
        else:
            sql_query = self._SQL_QUERY_FOR_CYLC_SEVEN
        logger.debug(f"SQL Query set to: '{sql_query}'")
        return sql_query

    def _extract_driver(self, sql_query) -> list[tuple]:
        """Driver function for "extract" stage of table data preparation.

        Extracts required raw task data from a Cylc SQLite database.

        Parameters
        ----------
        sql_query
            An SQLite query as a string, set based on the user's selected Cylc version.

        Returns
        -------
        raw_data
            The raw output from a sqlite3 SQL query as a list of tuples; with each tuple
            equivalent to a row of three columns.

        Raises
        ------
        CylcDatabaseError:
            A custom exception. ``_extract_driver`` supplies a custom message suggesting
            the user might have selected the wrong Cylc version. (The file is already
            validated as a SQLite).

        """
        logger.debug("RUNNING extract driver...")
        logger.debug("EXTRACTING data/running SQL query")
        try:
            connection = sqlite3.connect(self.path_to_cylc_db)
            cursor = connection.cursor()
            cursor.execute(sql_query)
            raw_data = cursor.fetchall()
            connection.close()
            logger.debug(
                "Tuples extracted (as a list):\n"
                + "\n".join([str(row) for row in raw_data])
            )
        except sqlite3.DatabaseError as error:
            # TODO: Also need to handle database connection errors. Will they be the
            # same error?
            alternate_cylc_version = 7
            if self.cylc_version == 7:
                alternate_cylc_version = 8
            custom_error_message = (
                f"{self.path_to_cylc_db} is not a valid Cylc {self.cylc_version} "
                f"database. Perhaps it is a Cylc {alternate_cylc_version} db?, error: "
                f"{error}"
            )
            logger.debug(custom_error_message)
            raise CylcDatabaseError(custom_error_message)
        return raw_data

    def _prepare_driver(self, raw_data: list[tuple]) -> list[TaskDurationRow]:
        """Driver function for "prepare" stage of table data preparation.

        The method converts each raw data row into a TaskDurationRow dataclass object.
        Additional columns of data are then added incrementally. No data is overwritten
        to aid future extensibility.

        E.g. a ``raw_data`` row enters the method as a tuple with these three columns:

        | task_name |  time_run |  time_run_exit |

        It leaves the method as a TaskDurationRow with attributes representing these
        six columns:

        | raw_task_name | raw_time_run | raw_time_run_exit | time_run | time_run_exit | run_duration |  # noqa

        Parameters
        ----------
        raw_data
            The raw output from a sqlite3 SQL query as a list of tuples; with each tuple
            equivalent to a row of three columns.

        Returns
        -------
        prepared_rows_six_columns
            A list of TaskRowDuration objects each with the original three "raw_data"
            columns and additional columns added; equivalent to six columns.

        """
        logger.debug("RUNNING prepare driver...")
        # TODO: Add handling for empty data/an entirely empty table. Might need to go
        # in ``_extract_driver`` - does it the sqlite return a string/error???
        prepared_rows_three_columns = self._convert_to_row_objects(raw_data)
        # TODO: Add functionality here to segregate ""  and NULL rows for separate
        # formatting. Probably only time_run and time_run_exit? Would name ever be
        # blank???
        prepared_rows_five_columns = self._add_valid_datetime_columns(
            prepared_rows_three_columns
        )
        prepared_rows_six_columns = self._add_run_duration_column(
            prepared_rows_five_columns
        )
        return prepared_rows_six_columns

    # TODO: These debug statements will throw if a table is empty. Intention is to catch
    # earlier in ``_prepare_driver`` or ``_extract_driver``.
    def _convert_to_row_objects(self, raw_data: list[tuple]) -> list[TaskDurationRow]:
        """Convert a list of tuples (i.e. rows) into a list of TaskDurationRow objects.

        Parameters
        ----------
        raw_data
            A list of tuples/rows extracted by an SQLite3 query.

        Returns
        -------
        prepared_rows_with_three_columns
            A list of TaskDurationRows where each TaskDurationRow has three columns of
            original "raw" data, prefixed with ``raw_``.

        """
        logger.debug("Converting RAW ROWS to PREPARED ROWS")
        prepared_rows_with_three_columns = []
        for raw_row in raw_data:
            row = TaskDurationRow(raw_row[0], raw_row[1], raw_row[2])
            prepared_rows_with_three_columns.append(row)
        logger.debug(
            "First item in PREPARED ROWS (3 columns): "
            f"{prepared_rows_with_three_columns[0]}"
        )
        return prepared_rows_with_three_columns

    def _add_valid_datetime_columns(
        self, prepared_rows: list[TaskDurationRow]
    ) -> list[TaskDurationRow]:
        """Add datetime attributes to a list of TaskDurationRows.

        For each TaskDurationRow in a list, convert the attributes ``raw_time_run`` and
        ``raw_time_run_exit`` to valid datetime objects and add them to the
        TaskDurationRow object as additional attributes.

        The method assumes that the ``raw_time_run`` and ``raw_time_run_exit`` attribute
        of each TaskDurationRow  object can be converted to valid datetimes.

        Parameters
        ----------
        prepared_rows
            A list of TaskDurationRows with three columns.

        Returns
        -------
        prepared_rows
            A list of TaskDurationRows with five columns.

        """
        logger.debug("Adding TIME RUN and TIME RUN EXIT columns")
        for prepared_row in prepared_rows:
            prepared_row.time_run = (
                self._convert_zulutime_datetime_string_to_valid_datetime(
                    prepared_row.raw_time_run
                )
            )
            prepared_row.time_run_exit = (
                self._convert_zulutime_datetime_string_to_valid_datetime(
                    prepared_row.raw_time_run_exit
                )
            )
        logger.debug(f"First item in PREPARED ROWS (5 columns): {prepared_rows[0]}")
        return prepared_rows

    def _add_run_duration_column(
        self, prepared_rows: list[TaskDurationRow]
    ) -> list[TaskDurationRow]:
        """Add a ``run_duration`` attribute to a list of TaskDurationRows.

        Calculate the run duration by subtracting ``time_run`` from ``time_run_exit``
        and store as timedelta.

        Parameters
        ----------
        prepared_rows
            A list of TaskDurationRows with five columns.

        Returns
        -------
        prepared_rows
            A list of TaskDurationRows with six columns.

        """
        logger.debug("Adding RUN DURATION column")
        for prepared_row in prepared_rows:
            prepared_row.run_duration = (
                prepared_row.time_run_exit - prepared_row.time_run
            )
        logger.debug(f"First item in PREPARED ROWS (6 columns): {prepared_rows[0]}")
        return prepared_rows

    # TODO: Rework for non-Zulu time strings e.g. ``+01:00`` in Harold's sample data.
    # Probably this stays for the "Z" strings and we convert valid values elsewhere?
    def _convert_zulutime_datetime_string_to_valid_datetime(
        self, zulu_date_time: str
    ) -> datetime:
        """Convert an extracted "zulu time" datetime into a valid datetime object.

        sqlite3 seems to extract `Z` datetimes as ISO datetime strings that `datetime`
        is unable to convert.E.g. `2024-06-25T10:37:31Z`.

        This method replaces the `Z` UTC Zulutime indicator with "+00:00" and converts
        the result to a datetime object.

        Parameters
        ----------
        zulu_date_time

        Returns
        -------
        datetime_object
            The ``zulu_date_time`` string correctly rendered as a datetime.

        """
        valid_iso_formatted_datetime = zulu_date_time.replace("Z", "+00:00")
        datetime_object = datetime.fromisoformat(valid_iso_formatted_datetime)
        return datetime_object

    def _format_driver(self, prepared_rows):
        """Driver function for "format" stage of table data preparation.

        The method creates the component parts of a table as renderable markup format
        as selected by the user.

        The component parts of a table are collected together in a DataTable dataclass
        object with the attributes ``table_summary``, ``column_header_row`` and
        `row_extracts_in_table_format`.

        The methods are called as follows. First, non-format specific steps are taken.
        ``table_summary_statistics`` are generated and ``prepared_rows`` is sorted.

        Next, format specific steps are taken. Each format has equivalent methods
        suffixed with `_trac`, `_github` or `trac_or_github`.

        ``table_summary`` is created using the appropriate ``_generate_table_summary``
        method.

        The ``column_header_row`` methods create the appropriate column header rows.

        `row_extracts_in_table_format` is created through a number of incremental steps.
        Formatting is applied to each row based on the value of each TaskDurationRow's
        ``run_duration`` attribute. ``raw_task_name``and ``run_duration`` attributes
        are then extracted in a valid renderable format.

        Finally, the renderable DataTable attributes/table components are converted to
        a string.

        Parameters
        ----------
        prepared_rows
            A list of TaskDurationRow objects with six columns as attributes.

        Returns
        -------
        data_table_as_a_string
            A string that represents a renderable markdown version of a table and
            summary.

        """
        logger.debug("RUNNING format driver...")
        table_summary_statistics = self._generate_table_summary_statistics(
            prepared_rows
        )
        prepared_rows_sorted = self._sort_by_run_duration(prepared_rows)

        if self.output_format == "trac":
            logger.debug("Applying TRAC markup formatting logic...")
            table_summary = self._generate_table_summary_trac(table_summary_statistics)
            column_header_row = self._generate_column_header_row_trac()
            rows_with_formatted_cells = self._apply_design_one_format_entire_row_based_on_duration_trac_or_github(  # noqa
                prepared_rows_sorted
            )
            row_extracts_in_table_format = (
                self._extract_and_format_required_columns_by_row_trac(
                    rows_with_formatted_cells
                )
            )
        # The only valid ``output_format`` other than "trac" is "github".
        else:
            logger.debug("Applying GITHUB markup formatting logic...")
            table_summary = self._generate_table_summary_github(
                table_summary_statistics
            )
            column_header_row = self._generate_column_header_row_github()
            rows_with_formatted_cells = self._apply_design_one_format_entire_row_based_on_duration_trac_or_github(  # noqa
                prepared_rows_sorted
            )
            row_extracts_in_table_format = (
                self._extract_and_format_required_columns_by_row_github(
                    rows_with_formatted_cells
                )
            )
        data_table = DataTable(
            table_summary, column_header_row, row_extracts_in_table_format
        )
        logger.debug(f"CREATE DATA TABLE: {data_table}")
        data_table_as_a_string = str(data_table)
        logger.debug(
            f"CONVERT DATA TABLE to a string with line breaks:\n\n"
            f"{data_table_as_a_string}"
        )
        return data_table_as_a_string

    def _get_run_duration(self, row: TaskDurationRow) -> timedelta:
        """Return the run_duration attribute of a TaskDurationRow object.

        Parameters
        ----------
        row
            A TaskDurationRow.

        Returns
        -------
        run_duration
            The value of a TaskDurationRow's `run_duration` attribute as a timedelta.
        """
        return row.run_duration

    def _sort_by_run_duration(
        self, prepared_rows: list[TaskDurationRow], descending: bool = True
    ) -> None:
        """Sort a list of TaskDurationRows by ``run_duration``.

        The default sort order is descending.

        Parameters
        ----------
        prepared_rows
            A list of TaskDurationRows in an unsorted order.

        Returns
        -------
        prepared_rows
            A list of TaskDurationRows in a sorted order. (Default is descending).

        """
        logger.debug("SORTING by run duration")
        if descending:
            reverse = True
        else:
            reverse = False
        prepared_rows.sort(key=self._get_run_duration, reverse=reverse)
        logger.debug(
            "Sorted data is "
            f"{[(row.raw_task_name, row.run_duration) for row in prepared_rows]}"
        )
        return prepared_rows

    def _generate_table_summary_statistics(
        self, prepared_rows: list[TaskDurationRow]
    ) -> dict:
        """Generate summary statistics for a list of TaskDurationRows.

        Calculates "count_of_tasks", "sum_of_run_durations", "average_of_run_durations",
        "count_of_tasks_longer_than_duration_flag" and
        "count_of_tasks_shorter_than_duration_flag".

        Parameters
        ----------
        prepared_rows
            A list of TaskDurationRow objects.

        Returns
        -------
        summary_stats
            A dictionary of summary statistics.

        """
        count_of_tasks = len(prepared_rows)
        run_durations = [row.run_duration for row in prepared_rows]
        sum_of_run_durations = sum(run_durations, timedelta(0))
        average_of_run_durations = timedelta(
            seconds=round(sum_of_run_durations.seconds / count_of_tasks)
        )
        count_of_tasks_longer_than_duration_flag = len(
            [
                row
                for row in prepared_rows
                if row.run_duration >= timedelta(minutes=self.duration_flag)
            ]
        )
        count_of_tasks_shorter_than_duration_flag = len(
            [
                row
                for row in prepared_rows
                if row.run_duration < timedelta(minutes=self.duration_flag)
            ]
        )
        summary_stats = {
            "count_of_tasks": count_of_tasks,
            "sum_of_run_durations": sum_of_run_durations,
            "average_of_run_durations": average_of_run_durations,
            "count_of_tasks_longer_than_duration_flag": (
                count_of_tasks_longer_than_duration_flag
            ),
            "count_of_tasks_shorter_than_duration_flag": (
                count_of_tasks_shorter_than_duration_flag
            ),
        }
        logger.debug(f"GENERATED summary stats: {summary_stats}")
        return summary_stats

    def _generate_table_summary_trac(self, summary_statistics: dict) -> list[str]:
        """Generate a table summary in trac markup renderable format.

        Parameters
        ----------
        summary_statistics
            A dictionary of summary statistics.

        Returns
        -------
        table_summary
            A table summary as a list of renderable strings.

        """
        table_summary = [
            "=== Test Results - Summary 🏥⏱ ===\n",
            " ||= //Summary// =||= =||",
            f" || Total tests run ||  {summary_statistics.get('count_of_tasks')}  ||",
            f" || Average test run time ||  {summary_statistics.get('average_of_run_durations')}  ||",  # noqa
            f" || Over **{self.duration_flag}** mins ||  👉 **{summary_statistics.get('count_of_tasks_longer_than_duration_flag')}** 👈  ||",  # noqa
            f" || Under **{self.duration_flag}** mins ||  {summary_statistics.get('count_of_tasks_shorter_than_duration_flag')}  ||\n",  # noqa
        ]
        logger.debug(f"Table Summary (trac format): {table_summary}")
        return table_summary

    def _generate_table_summary_github(self, summary_statistics: dict) -> list[str]:
        """Generate a table summary in GitHub markup renderable format.

        Parameters
        ----------
        summary_statistics
            A dictionary of summary statistics.

        Returns
        -------
        table_summary
            A table summary as a list of renderable strings.

        """
        table_summary = [
            "## Test Results - Summary 🏥⏱\n",
            "| _Summary_ | |",
            "| :-| :-: |",
            f"| Total tests run | {summary_statistics.get('count_of_tasks')} |",
            f"| Average test run time | {summary_statistics.get('average_of_run_durations')} |",  # noqa
            f"| Over **{self.duration_flag}** mins | 👉 **{summary_statistics.get('count_of_tasks_longer_than_duration_flag')}** 👈 |",  # noqa
            f"| Under **{self.duration_flag}** mins | {summary_statistics.get('count_of_tasks_shorter_than_duration_flag')} |\n",  # noqa
        ]
        logger.debug(f"Table Summary (GitHub format): {table_summary}")
        return table_summary

    # TODO: Rename as ``_generate_table_header``.
    def _generate_column_header_row_trac(self) -> list[str]:
        """Generate a table header in trac markup renderable format.

        Returns
        -------
        header
            A table header as a list of renderable strings.

        """
        header = [
            "=== Test Results - Detail 🏥🔍 ===\n",
            " ||= //Test// =||= //Run Δt// =||",
        ]
        logger.debug(f"GENERATED header: {header}")
        return header

    def _generate_column_header_row_github(self) -> list[str]:
        """Generate a table header in GitHub markup renderable format.

        Returns
        -------
        header
            A table header as a list of renderable strings.

        """
        header = [
            "## Test Results - Detail 🏥🔍\n",
            "| _Test_ | _Run Δt_ |",
            "| :-|:- |",
        ]
        logger.debug(f"GENERATED header: {header}")
        return header

    def _apply_formatting_to_cell_value_trac_or_github(self, cell_value: str) -> str:
        """Apply formatting to a cell.

        Parameters
        ----------
        cell_value
            A cell value.

        Returns
        -------
        formatted_cell_value
            The formatted cell value.

        """
        formatting = "**"
        formatted_cell_value = f"{formatting}{cell_value}{formatting} 👈"
        return formatted_cell_value

    def _apply_design_one_format_entire_row_based_on_duration_trac_or_github(
        self,
        prepared_rows: list[TaskDurationRow],
    ) -> list[TaskDurationRow]:
        """Apply ``design_one`` for trac or GitHub.

        Design one bolds the values to be outputted in a row when ``run_duration`` is
        greater than ``self.duration_flag``. During formatting ``run_duration``
        timedeltas are cast to strings.

        Parameters
        ----------
        prepared_rows
            A list of TaskDurationRow objects.

        Returns
        -------
        prepared_rows
            A list of TaskDurationRows with formatting applied to ``raw_task_name``,
            ``run_duration`` and ``run_duration_baseline``.

        """
        logger.debug("APPLYING DESIGN ONE (all display cells formatted)")
        logger.debug(f"Prepared rows[0] going in: {prepared_rows[0]}")
        for row in prepared_rows:
            if row.run_duration >= timedelta(minutes=self.duration_flag):
                row.raw_task_name = self._apply_formatting_to_cell_value_trac_or_github(
                    row.raw_task_name
                )
                row.run_duration = self._apply_formatting_to_cell_value_trac_or_github(
                    str(row.run_duration)
                )
                row.run_duration_baseline = (
                    self._apply_formatting_to_cell_value_trac_or_github(
                        str(row.run_duration_baseline)
                    )
                )
        logger.debug(f"Prepared rows[0] coming out: {prepared_rows[0]}")
        return prepared_rows

    def _extract_and_format_required_columns_by_row_trac(
        self, rows_with_formatted_cells: list[TaskDurationRow]
    ) -> list[str]:
        """Extract required data and format as a valid trac markup table row.

        Extracts formatted values from a TaskDurationRow and converts them into a
        formatted table row.

        Parameters
        ----------
        rows_with_formatted_cells
            A list of TaskDurationRows with formatting applied ``raw_task_name``,
            ``run_duration`` and ``run_duration_baseline``.

        Returns
        -------
        row_extracts_in_table_format
            Extracted, formatted columns as a list of renderable strings.

        """
        logger.debug("EXTRACTING rows and FORMATTING as a table")
        row_extracts_in_table_format = []
        for row in rows_with_formatted_cells:
            formatted_row = f" || {row.raw_task_name} || {row.run_duration} ||"
            row_extracts_in_table_format.append(formatted_row)
        logger.debug(f"Formatted rows[0]: {formatted_row}")
        logger.debug(f"Type (Formatted columns[0]): {type(formatted_row[0])}")
        return row_extracts_in_table_format

    def _extract_and_format_required_columns_by_row_github(
        self, rows_with_formatted_cells: list[TaskDurationRow]
    ) -> list[str]:
        """Extract required data and format as a valid GitHub markup table row.

        Extracts formatted values from a TaskDurationRow and converts them into a
        formatted table row.

        Parameters
        ----------
        rows_with_formatted_cells
            A list of TaskDurationRows with formatting applied ``raw_task_name``,
            ``run_duration`` and ``run_duration_baseline``.

        Returns
        -------
        row_extracts_in_table_format
            Extracted, formatted columns as a list of renderable strings.

        """
        logger.debug("EXTRACTING rows and FORMATTING as a table")
        row_extracts_in_table_format = []
        for row in rows_with_formatted_cells:
            formatted_row = f"| {row.raw_task_name} | {row.run_duration} |"
            row_extracts_in_table_format.append(formatted_row)
        logger.debug(f"Formatted rows[0]: {formatted_row}")
        logger.debug(f"Type (Formatted columns[0]): {type(formatted_row[0])}")
        return row_extracts_in_table_format

    def _write_table_to_file(self, formatted_table_as_string: str) -> None:
        """Write a string to the file specified in ``self.output_file_name``.

        If the file already exists it will be overwritten without warning.

        Parameters
        ----------
        formatted_table_as_a_string:
            The formatted table as a string for writing to a file.

        """
        logger.debug("WRITING to output_file_name")
        self.output_file_name.write_text(formatted_table_as_string)
        logger.debug(f"Duration log written to: {self.output_file_name}")
        print(f"Duration log written to: {self.output_file_name}")

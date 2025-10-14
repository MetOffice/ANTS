# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from durations_extract_format import (
    CylcDatabaseError,
    DataTable,
    TableMaker,
    TaskDurationRow,
)


class TestDataTable:
    """
    Test the DataTable dataclass.

    """

    @pytest.fixture(autouse=True)
    def synthetic_data_table(self):
        """
        A Pytest fixture that automatically attaches a synthetic ``DataTable`` instance
        to each test case in the ``TestDataTable`` class.

        The synthetic ``DataTable`` is created with three rows of data: ["a", "b"],
        ["c", "d"], and ["e", "f"].

        This fixture is automatically used (due to `autouse=True`) for each test method
        in the class. The ``DataTable`` instance is accessed in the test methods via
        `self.data_table`.
        """
        synthetic_table_elements = [["a", "b"], ["c", "d"], ["e", "f"]]
        synthetic_data_table = DataTable(
            synthetic_table_elements[0],
            synthetic_table_elements[1],
            synthetic_table_elements[2],
        )
        self.synthetic_data_table = synthetic_data_table

    def test_init_success_table_summary_section(self):
        """Assert ``table_summary_section`` initialises as expected."""
        assert self.synthetic_data_table.table_summary_section == ["a", "b"]

    def test_init_success_column_header_row(self):
        """Assert ``column_header`` initialises as expected."""
        assert self.synthetic_data_table.column_header_row == ["c", "d"]

    def test_init_success_table_formatted_rows(self):
        """Assert ``formatted_rows`` initialises as expected."""
        assert self.synthetic_data_table.formatted_rows == ["e", "f"]

    def test_data_table_to_string_success(self):
        """Test DataTable attributes of expected type convert to a string."""
        actual = str(self.synthetic_data_table)
        expected = "a\nb\nc\nd\ne\nf"
        assert actual == expected

    @pytest.mark.parametrize(
        "invalid_data",
        [
            ([["a", "b"], ["c", "d"], 1]),
            (["a", ["b", "c"], ["d", "e"]]),
        ],
    )
    def test_data_table_to_string_invalid_data(self, invalid_data):
        """Test DataTable attributes of expected type convert to a string.

        This should not happen as all user inputs are validated by this point. The test
        is a development aid.
        """
        data_table = DataTable(invalid_data[0], invalid_data[1], invalid_data[2])
        with pytest.raises(TypeError):
            str(data_table)


# TODO: Implement after we'd added functionality to segregate rows with blank or NULL
# fields.
class TestTaskDurationRow:
    pass


@pytest.fixture
def table_maker_synthetic_cylc_db(synthetic_cylc_db) -> TableMaker:
    """Instantiate a TableMaker object with a synthetic cylc db with 15 rows of data.

    Note
    ----
    A TableMaker can be instantiated with "invalid" values e.g. ``output_directory`` as
    ``a_directory`` because validation is assumed to have taken place before
    TableMaker instantiation (primarily by argparse).

    """
    arg_1 = synthetic_cylc_db
    arg_2 = "an_output_file_name"
    arg_3 = "trac"
    arg_4 = 8
    arg_5 = 1
    table_maker = TableMaker(arg_1, arg_2, arg_3, arg_4, arg_5)
    return table_maker


class TestTableMakerInitialisation:
    """Test an instantiated TableMaker instance initialises as expected.

    These tests double as tests of the ``table_maker_synthetic_cylc_db`` Pytest fixture.

    """

    def test_path_to_cylc_db(self, table_maker_synthetic_cylc_db, synthetic_cylc_db):
        assert table_maker_synthetic_cylc_db.path_to_cylc_db == synthetic_cylc_db

    def test_path_to_output_dir(self, table_maker_synthetic_cylc_db, synthetic_cylc_db):
        assert table_maker_synthetic_cylc_db.output_file_name == "an_output_file_name"

    def test_output_format(self, table_maker_synthetic_cylc_db, synthetic_cylc_db):
        assert table_maker_synthetic_cylc_db.output_format == "trac"

    def test_cylc_version(self, table_maker_synthetic_cylc_db, synthetic_cylc_db):
        assert table_maker_synthetic_cylc_db.cylc_version == 8

    def test_cylc_8_sql_query_class_attribute(self, table_maker_synthetic_cylc_db):
        """Test the Cylc 8 sql query is present as a class attribute."""
        expected = (
            "SELECT task_jobs.name, task_jobs.time_run, task_jobs.time_run_exit "
            "FROM task_jobs "
            "JOIN task_states "
            "ON task_jobs.name = task_states.name "
            "AND task_jobs.submit_num = task_states.submit_num"
        )
        actual = table_maker_synthetic_cylc_db._SQL_QUERY_FOR_CYLC_EIGHT
        assert actual == expected

    def test_cylc_7_sql_query_class_attribute(self, table_maker_synthetic_cylc_db):
        """Test the Cylc 7 sql query is present as a class attribute."""
        expected = "Not implemented"
        actual = table_maker_synthetic_cylc_db._SQL_QUERY_FOR_CYLC_SEVEN
        assert actual == expected


# TODO: First fix the datetime issue so I can use Harold's data to generate KGO.
class TestTableMakerDriver:
    pass


class TestTableMakerExtractDriver:
    """Test TableMaker ``_extract_driver`` method and sub-ordinate methods."""

    def test_set_cylc_eight_sql_query_selected(self, table_maker_synthetic_cylc_db):
        """Test a Cylc 8 sql query is correctly selected based on ``cylc_version``.

        Tests the ``table_maker_synthetic_cylc_db`` TableMaker instance generates the
        correct Cylc 8 sql query.

        """
        expected_sql_query = (
            "SELECT task_jobs.name, task_jobs.time_run, task_jobs.time_run_exit "
            "FROM task_jobs "
            "JOIN task_states "
            "ON task_jobs.name = task_states.name "
            "AND task_jobs.submit_num = task_states.submit_num"
        )
        actual_sql_query = table_maker_synthetic_cylc_db._get_sql_query()
        assert actual_sql_query == expected_sql_query

    def test_set_cylc_seven_sql_query_selected(self, table_maker_synthetic_cylc_db):
        """Test a Cylc 7 sql query is correctly selected based on ``cylc_version``.

        The test overwrites the ``table_maker_synthetic_cylc_db.cylc_version`` with
        ``7``.

        """
        table_maker_synthetic_cylc_db.cylc_version = 7
        sql_query = table_maker_synthetic_cylc_db._get_sql_query()
        assert sql_query == "Not implemented"

    def test_extract_driver_for_a_cylc_eight_db_returns_a_list(
        self,
        table_maker_synthetic_cylc_db,
    ):
        """Test ``_extract_driver`` on the ``table_maker_synthetic_cylc_db`` TableMaker
        instance. Tests ``_extract_driver`` returns a list.
        """
        cylc_8_sql_query = table_maker_synthetic_cylc_db._SQL_QUERY_FOR_CYLC_EIGHT
        actual = table_maker_synthetic_cylc_db._extract_driver(cylc_8_sql_query)
        assert isinstance(actual, list)

    def test_extract_driver_for_cylc_eight_db_returns_list_of_expected_length(
        self,
        table_maker_synthetic_cylc_db,
    ):
        """Test ``_extract_driver`` on the ``table_maker_synthetic_cylc_db`` TableMaker
        instance. Tests ``_extract_driver`` returns a list of expected length.

        This test also checks the ``__SQL_QUERY_FOR_CYLC_EIGHT`` is working correctly.
        ``synthetic_cylc_db`` contains 16 rows: one task replicates being run twice. The
        ``__SQL_QUERY_FOR_CYLC_EIGHT`` should exclude that run, leaving 15 rows.
        """
        cylc_8_sql_query = table_maker_synthetic_cylc_db._SQL_QUERY_FOR_CYLC_EIGHT
        actual = table_maker_synthetic_cylc_db._extract_driver(cylc_8_sql_query)
        assert len(actual) == 15

    def test_extract_driver_for_a_cylc_eight_db_item_content(
        self, table_maker_synthetic_cylc_db
    ):
        """Test ``_extract_driver`` on the ``table_maker_synthetic_cylc_db`` TableMaker
        instance. Tests ``_extract_driver`` returns the expected first item.

        This test also checks the ``__SQL_QUERY_FOR_CYLC_EIGHT`` is working correctly.
        ``synthetic_cylc_db`` contains 16 rows: one task replicates being run twice. The
        ``__SQL_QUERY_FOR_CYLC_EIGHT`` should exclude that run. ``expected_first_item``
        is actually the second row in the database, therefore confirming the initial run
        of "install_cold" is excluded.
        """
        cylc_8_sql_query = table_maker_synthetic_cylc_db._SQL_QUERY_FOR_CYLC_EIGHT
        raw_data = table_maker_synthetic_cylc_db._extract_driver(cylc_8_sql_query)
        actual_first_item = raw_data[0]
        expected_first_item = (
            "install_cold",
            "2024-06-24T15:17:49+01:00",
            "2024-06-24T15:17:59+01:00",
        )
        assert actual_first_item == expected_first_item

    def test_extract_driver_for_a_cylc_eight_db_item_type(
        self, table_maker_synthetic_cylc_db
    ):
        """Test ``_extract_driver`` on the ``table_maker_synthetic_cylc_db`` TableMaker
        instance. Tests ``_extract_driver`` returns a first item of the expected type.
        """
        cylc_8_sql_query = table_maker_synthetic_cylc_db._SQL_QUERY_FOR_CYLC_EIGHT
        raw_data = table_maker_synthetic_cylc_db._extract_driver(cylc_8_sql_query)
        actual_first_item = raw_data[0]
        assert isinstance(actual_first_item, tuple)

    def test_extract_driver_for_an_invalid_cylc_8_database_source(self):
        """Test ``_extract_driver`` raises the expected error for a non Cylc 8 db.

        The tests creates a valid SQLite db file with a table called ``task_jobs`` but
        the table is missing the ``task_run_exit`` column. The table contains no data.

        """
        with tempfile.TemporaryDirectory() as temp_directory:
            non_cylc_eight_db = Path(temp_directory) / "non_cylc_eight_db"
            connection = sqlite3.connect(non_cylc_eight_db)
            cursor = connection.cursor()
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS task_jobs
                (name TEXT NOT NULL, time_run TEXT NOT NULL, submit_num TEXT NOT NULL)
                """
            )
            connection.close()
            table_maker_instance_invalid_cylc_db = TableMaker(
                non_cylc_eight_db,
                "a_path_to_output_dir",
                "an_output_format",
                "-c 8",
                "-d 1",
            )
            cylc_8_sql_query = (
                table_maker_instance_invalid_cylc_db._SQL_QUERY_FOR_CYLC_EIGHT
            )
            with pytest.raises(CylcDatabaseError):
                table_maker_instance_invalid_cylc_db._extract_driver(cylc_8_sql_query)


class TestTableMakerPrepareDriver:
    """Test TableMaker ``_prepare_driver`` method and sub-ordinate methods.

    Creates the class attribute ``SAMPLE_RAW_TASK_DURATION_DATA`` for use as a simple
    test case in most tests.

    """

    SAMPLE_RAW_TASK_DURATION_DATA = [
        ("configure_process", "2024-06-25T10:37:36Z", "2024-06-25T10:37:39Z"),
        ("standardise_model_data", "2024-06-25T10:38:16Z", "2024-06-25T10:47:34Z"),
        (
            "process_radiation_budget",
            "2024-06-25T10:47:40Z",
            "2024-06-25T10:48:44Z",
        ),
    ]

    # TODO: First fix the datetime issue so I can use Harold's data to generate KGO.
    def test_prepare_driver(self):
        pass

    def test_convert_to_row_objects_returns_list(self, table_maker_synthetic_cylc_db):
        """Test ``_convert_to_row_objects`` for a list of tuples returns a list."""

        actual = table_maker_synthetic_cylc_db._convert_to_row_objects(
            self.SAMPLE_RAW_TASK_DURATION_DATA
        )
        assert isinstance(actual, list)

    def test_convert_to_row_objects_returns_list_of_task_row_objects(
        self, table_maker_synthetic_cylc_db
    ):
        """Test ``_convert_to_row_objects`` for a list of tuples returns a list of
        TaskDurationRows.
        """
        actual = table_maker_synthetic_cylc_db._convert_to_row_objects(
            self.SAMPLE_RAW_TASK_DURATION_DATA
        )
        assert all(isinstance(row, TaskDurationRow) for row in actual)

    @pytest.mark.parametrize(
        "attribute_name, expected_value",
        [
            ["raw_task_name", "configure_process"],
            ["raw_time_run", "2024-06-25T10:37:36Z"],
            ["raw_time_run_exit", "2024-06-25T10:37:39Z"],
        ],
    )
    def test_convert_to_row_objects_converted_task_duration_row_attributes(
        self, table_maker_synthetic_cylc_db, attribute_name, expected_value
    ):
        """Test the attributes of an item return by ``_convert_to_row_objects``.

        Uses the first item in the ``SAMPLE_RAW_TASK_DURATION_DATA`` class attribute.
        """
        converted_rows = table_maker_synthetic_cylc_db._convert_to_row_objects(
            self.SAMPLE_RAW_TASK_DURATION_DATA
        )
        actual_item = converted_rows[0]
        assert getattr(actual_item, attribute_name) == expected_value

    # TODO: Once NULL & empty rows are segregated this test can be moved or removed.
    @pytest.mark.parametrize(
        "row_with_empty_values, empty_attribute_value",
        [
            [[("", "arg_2", "arg_3")], "raw_task_name"],
            [[("arg_1", "", "arg_3")], "raw_time_run"],
            [[("arg_1", "arg_2", "")], "raw_time_run_exit"],
        ],
    )
    def test_convert_to_row_objects_empty_cell_values(
        self,
        table_maker_synthetic_cylc_db,
        row_with_empty_values,
        empty_attribute_value,
    ):
        """Assert empty values are handled correctly."""
        actual = table_maker_synthetic_cylc_db._convert_to_row_objects(
            row_with_empty_values
        )
        assert getattr(actual[0], empty_attribute_value) == ""

    @pytest.mark.parametrize(
        "attribute_name, expected_value",
        [
            ["time_run", datetime(2024, 6, 25, 10, 47, 40, tzinfo=timezone.utc)],
            ["time_run_exit", datetime(2024, 6, 25, 10, 48, 44, tzinfo=timezone.utc)],
        ],
    )
    def test_add_valid_datetime_columns(
        self, table_maker_synthetic_cylc_db, attribute_name, expected_value
    ):
        """Test ``_add_valid_datetime_columns`` adds two additional columns of the
        expected type and value to a TaskDurationRow object.
        """
        prepared_rows = [
            TaskDurationRow(
                "process_radiation_budget",
                "2024-06-25T10:47:40Z",
                "2024-06-25T10:48:44Z",
            )
        ]
        table_maker_synthetic_cylc_db._add_valid_datetime_columns(prepared_rows)
        prepared_row = prepared_rows[0]
        assert getattr(prepared_row, attribute_name) == expected_value

    @pytest.mark.parametrize(
        "attribute_name, expected_value",
        [
            ["time_run", " "],
            ["time_run_exit", " "],
        ],
    )
    @pytest.mark.skip(
        "Currently throws. This can be removed once NULL/empty cells are segregated."
    )
    def test_add_valid_datetime_columns_zero_values(
        self, table_maker_synthetic_cylc_db, attribute_name, expected_value
    ):
        """Test how ``_add_valid_datetime_columns`` handles empty values."""
        prepared_rows = [TaskDurationRow("process_radiation_budget", "", "")]
        table_maker_synthetic_cylc_db._add_valid_datetime_columns(prepared_rows)
        prepared_row = prepared_rows[0]
        assert getattr(prepared_row, attribute_name) == expected_value

    def test_add_run_duration_column(self, table_maker_synthetic_cylc_db):
        """Test ``_add_run_duration_column`` adds an additional column of the
        expected type and value to a TaskDurationRow object.
        """
        prepared_rows = [
            TaskDurationRow(
                "process_radiation_budget",
                "2024-06-25T10:47:40Z",
                "2024-06-25T10:48:44Z",
                datetime(2024, 6, 25, 10, 48, 00, tzinfo=timezone.utc),
                datetime(2024, 6, 25, 10, 48, 30, tzinfo=timezone.utc),
            )
        ]
        table_maker_synthetic_cylc_db._add_run_duration_column(prepared_rows)
        prepared_row = prepared_rows[0]
        assert prepared_row.run_duration == timedelta(seconds=30)

    def test_convert_to_datetime_value(self, table_maker_synthetic_cylc_db):
        extracted_datetime = "2024-06-25T10:37:31Z"
        expected = datetime(2024, 6, 25, 10, 37, 31, tzinfo=timezone.utc)
        converted_datetime = table_maker_synthetic_cylc_db._convert_zulutime_datetime_string_to_valid_datetime(  # noqa
            extracted_datetime
        )
        assert converted_datetime == expected

    def test_convert_to_datetime_type(self, table_maker_synthetic_cylc_db):
        extracted_datetime = "2024-06-25T10:37:31Z"
        converted_datetime = table_maker_synthetic_cylc_db._convert_zulutime_datetime_string_to_valid_datetime(  # noqa
            extracted_datetime
        )
        assert isinstance(converted_datetime, datetime)


@pytest.fixture
def prepared_rows_with_five_columns():
    """A Pytest fixture to create a list of TaskDurationRows with five columns.

    This represents the expected state of a TaskDurationRow once it has passed through
    the ``_prepare_driver``.

    """
    prepared_row_1 = TaskDurationRow(
        "configure_process",
        "2024-06-25T10:37:36Z",
        "2024-06-25T10:37:39Z",
        datetime(2024, 6, 25, 10, 37, 36, tzinfo=timezone.utc),
        datetime(2024, 6, 25, 10, 37, 39, tzinfo=timezone.utc),
        timedelta(seconds=3),
    )
    prepared_row_2 = TaskDurationRow(
        "standardise_model_data",
        "2024-06-25T10:38:16Z",
        "2024-06-25T10:47:34Z",
        datetime(2024, 6, 25, 10, 38, 16, tzinfo=timezone.utc),
        datetime(2024, 6, 25, 10, 47, 35, tzinfo=timezone.utc),
        timedelta(seconds=558),
    )
    prepared_row_3 = TaskDurationRow(
        "process_radiation_budget",
        "2024-06-25T10:47:40Z",
        "2024-06-25T10:48:44Z",
        datetime(2024, 6, 25, 10, 47, 40, tzinfo=timezone.utc),
        datetime(2024, 6, 25, 10, 48, 44, tzinfo=timezone.utc),
        timedelta(seconds=64),
    )
    prepared_rows = [prepared_row_1, prepared_row_2, prepared_row_3]
    return prepared_rows


class TestTableMakerFormatDriver:
    """Test TableMaker ``_format_driver`` method and sub-ordinate methods.

    The tests here uses ``table_maker_synthetic_cylc_db`` as a TableMaker instance
    purely to access it's methods; they don't use any of the data it is initialised
    with. # TODO: Should we create a separate synthetic instance for purity?

    """

    # TODO: First fix the datetime issue so I can use Harold's data to generate KGO.
    def test_format_driver(self):
        pass

    def test_get_run_duration(self, table_maker_synthetic_cylc_db):
        """Test the method used to sort TaskDurationRows."""
        a_prepared_row = TaskDurationRow(
            "process_radiation_budget",
            "2024-06-25T10:47:40Z",
            "2024-06-25T10:48:44Z",
            datetime(2024, 6, 25, 10, 48, 00, tzinfo=timezone.utc),
            datetime(2024, 6, 25, 10, 48, 30, tzinfo=timezone.utc),
            timedelta(seconds=30),
        )
        actual = table_maker_synthetic_cylc_db._get_run_duration(a_prepared_row)
        expected = timedelta(seconds=30)
        assert actual == expected

    def test_sort_by_run_duration(
        self, prepared_rows_with_five_columns, table_maker_synthetic_cylc_db
    ):
        """Test ``_sort_by_run_duration`` on the unsorted
        ``prepared_rows_with_five_columns.``

        """
        sorted_table = table_maker_synthetic_cylc_db._sort_by_run_duration(
            prepared_rows_with_five_columns
        )
        expected_sort_order_of_run_durations = [
            timedelta(seconds=558),
            timedelta(seconds=64),
            timedelta(seconds=3),
        ]
        actual_sorted_run_durations = [row.run_duration for row in sorted_table]
        assert actual_sorted_run_durations == expected_sort_order_of_run_durations

    def test_generate_summary_table_statistics(
        self, prepared_rows_with_five_columns, table_maker_synthetic_cylc_db
    ):
        """Test ``_generate_summary_table_statistics`` on
        ``prepared_rows_with_five_columns.``

        """
        actual = table_maker_synthetic_cylc_db._generate_table_summary_statistics(
            prepared_rows_with_five_columns
        )
        expected = {
            "average_of_run_durations": timedelta(seconds=208),
            "count_of_tasks": 3,
            "sum_of_run_durations": timedelta(seconds=625),
            "count_of_tasks_longer_than_duration_flag": 2,
            "count_of_tasks_shorter_than_duration_flag": 1,
        }
        assert actual == expected

    def test_generate_table_summary_trac(self, table_maker_synthetic_cylc_db):
        summary_statistics = {
            "average_of_run_durations": timedelta(seconds=208),
            "count_of_tasks": 3,
            "sum_of_run_durations": timedelta(seconds=625),
            "count_of_tasks_longer_than_duration_flag": 2,
            "count_of_tasks_shorter_than_duration_flag": 1,
        }
        actual = table_maker_synthetic_cylc_db._generate_table_summary_trac(
            summary_statistics
        )
        expected = [
            "=== Test Results - Summary 🏥⏱ ===\n",
            " ||= //Summary// =||= =||",
            " || Total tests run ||  3  ||",
            " || Average test run time ||  0:03:28  ||",
            " || Over **1** mins ||  👉 **2** 👈  ||",
            " || Under **1** mins ||  1  ||\n",
        ]
        assert actual == expected

    def test_generate_table_summary_github(self, table_maker_synthetic_cylc_db):
        summary_statistics = {
            "average_of_run_durations": timedelta(seconds=208),
            "count_of_tasks": 3,
            "sum_of_run_durations": timedelta(seconds=625),
            "count_of_tasks_longer_than_duration_flag": 2,
            "count_of_tasks_shorter_than_duration_flag": 1,
        }
        actual = table_maker_synthetic_cylc_db._generate_table_summary_github(
            summary_statistics
        )
        expected = [
            "## Test Results - Summary 🏥⏱\n",
            "| _Summary_ | |",
            "| :-| :-: |",
            "| Total tests run | 3 |",
            "| Average test run time | 0:03:28 |",
            "| Over **1** mins | 👉 **2** 👈 |",
            "| Under **1** mins | 1 |\n",
        ]
        assert actual == expected

    def test_generate_column_header_row_content_trac(
        self, table_maker_synthetic_cylc_db
    ):
        actual = table_maker_synthetic_cylc_db._generate_column_header_row_trac()
        expected = [
            "=== Test Results - Detail 🏥🔍 ===\n",
            " ||= //Test// =||= //Run Δt// =||",
        ]
        assert actual == expected

    def test_generate_column_header_row_content_github(
        self, table_maker_synthetic_cylc_db
    ):
        actual = table_maker_synthetic_cylc_db._generate_column_header_row_github()
        expected = [
            "## Test Results - Detail 🏥🔍\n",
            "| _Test_ | _Run Δt_ |",
            "| :-|:- |",
        ]
        assert actual == expected

    def test_generate_column_header_row_trac_is_a_list(
        self, table_maker_synthetic_cylc_db
    ):
        actual = table_maker_synthetic_cylc_db._generate_column_header_row_trac()
        assert isinstance(actual, list)

    def test_generate_column_header_row_github_is_a_list(
        self, table_maker_synthetic_cylc_db
    ):
        actual = table_maker_synthetic_cylc_db._generate_column_header_row_github()
        assert isinstance(actual, list)

    def test_apply_formatting_to_cell_value_trac_or_github(
        self, table_maker_synthetic_cylc_db
    ):
        synthetic_cell_value = "1:00"
        actual = table_maker_synthetic_cylc_db._apply_formatting_to_cell_value_trac_or_github(  # noqa
            synthetic_cell_value
        )
        assert actual == "**1:00** 👈"

    def test_apply_formatting_to_cell_value_trac_or_github_none(
        self, table_maker_synthetic_cylc_db
    ):
        """
        Test ``None`` values can pass through ``_apply_formatting_to_cell_value.``

        E.g. the TaskDurationRow default value for ``run_duration_baseline`` is set to
        None. If this isn't used, the None value can still pass.
        """
        synthetic_cell_value = None
        actual = table_maker_synthetic_cylc_db._apply_formatting_to_cell_value_trac_or_github(  # noqa
            synthetic_cell_value
        )
        assert actual == "**None** 👈"

    def test_apply_design_one_format_entire_row_based_on_duration_trac_or_github(
        self, prepared_rows_with_five_columns, table_maker_synthetic_cylc_db
    ):
        """Applies formatting to all rows in ``prepared_rows_with_five_columns.

        Checks the correct values have been formatted in a sample row.
        """
        formatted_rows = table_maker_synthetic_cylc_db._apply_design_one_format_entire_row_based_on_duration_trac_or_github(  # noqa
            prepared_rows_with_five_columns
        )
        first_formatted_row = formatted_rows[1]
        actual_formatted_cells = (
            first_formatted_row.raw_task_name,
            first_formatted_row.run_duration,
        )
        assert actual_formatted_cells == (
            "**standardise_model_data** 👈",
            "**0:09:18** 👈",
        )

    def test_extract_and_format_required_columns_by_row_trac(
        self, table_maker_synthetic_cylc_db
    ):
        """Test ``_extract_and_format_required_columns_by_row`` on three formatted rows.

        The test creates three synthetic TaskDurationRows in the state expected when
        they've been formatted. (A ``duration_flag`` of 1 minute is assumed).

        """
        prepared_row_1 = TaskDurationRow(
            "**standardise_model_data** 👈",
            "",
            "",
            run_duration="**0:09:18** 👈",
        )
        prepared_row_2 = TaskDurationRow(
            "**process_radiation_budget** 👈",
            "",
            "",
            run_duration="**0:01:04** 👈",
        )
        prepared_row_3 = TaskDurationRow(
            "configure_process",
            "",
            "",
            run_duration="0:00:03",
        )
        formatted_rows = [prepared_row_1, prepared_row_2, prepared_row_3]
        actual = table_maker_synthetic_cylc_db._extract_and_format_required_columns_by_row_trac(  # noqa
            formatted_rows
        )
        expected = [
            " || **standardise_model_data** 👈 || **0:09:18** 👈 ||",
            " || **process_radiation_budget** 👈 || **0:01:04** 👈 ||",
            " || configure_process || 0:00:03 ||",
        ]
        assert actual == expected

    def test_extract_and_format_required_columns_by_row_github(
        self, table_maker_synthetic_cylc_db
    ):
        prepared_row_1 = TaskDurationRow(
            "**standardise_model_data** 👈",
            "",
            "",
            run_duration="**0:09:18** 👈",
        )
        prepared_row_2 = TaskDurationRow(
            "**process_radiation_budget** 👈",
            "",
            "",
            run_duration="**0:01:04** 👈",
        )
        prepared_row_3 = TaskDurationRow(
            "configure_process",
            "",
            "",
            run_duration="0:00:03",
        )
        formatted_rows = [prepared_row_1, prepared_row_2, prepared_row_3]
        actual = table_maker_synthetic_cylc_db._extract_and_format_required_columns_by_row_github(  # noqa
            formatted_rows
        )
        expected = [
            "| **standardise_model_data** 👈 | **0:09:18** 👈 |",
            "| **process_radiation_budget** 👈 | **0:01:04** 👈 |",
            "| configure_process | 0:00:03 |",
        ]
        assert actual == expected

    @pytest.mark.parametrize(
        "synthetic_file_name",
        [
            ("output_with_no_suffix"),
            ("output.txt"),
            ("output.md"),
            ("output.tiff"),
            ("output_with.double.suffix"),
        ],
    )
    def test_write_table_to_file(
        self, table_maker_synthetic_cylc_db, synthetic_file_name
    ):
        """Test ``write_table_to_file`` writes a string to a variety of valid file
        paths.

        The test locates `synthetic_file_name`` in a "TemporaryDirectory" and uses it to
        overwrite the ``output_file_name`` attribute of
        ``table_maker_synthetic_cylc_db``.

        The ``write_table_to_file`` method is called with a synthetic string. The
        pathlib ``read_text`` method is used to assert the synthetic string has been
        written correctly.
        """
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_synthetic_file = Path(temp_directory) / synthetic_file_name
            table_maker_synthetic_cylc_db.output_file_name = temp_synthetic_file
            table_maker_synthetic_cylc_db._write_table_to_file("I am a string.")
            assert temp_synthetic_file.read_text() == "I am a string."

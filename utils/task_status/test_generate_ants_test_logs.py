from generate_ants_test_logs import generate_task_logs
from pathlib import Path
from tempfile import NamedTemporaryFile
import unittest
from unittest.mock import patch


def test_generate_task_logs_file_is_generated_with_github_formatting():

    text_format = "gh"

    current_dir = Path(__file__).parent.resolve()
    fake_db_path = current_dir / "fakedb.db"

    with NamedTemporaryFile() as temporary_file:

        target_file_path = Path(temporary_file.name)

        generate_task_logs(text_format, fake_db_path, target_file_path)

        assert target_file_path.is_file()


@patch("generate_ants_test_logs.retrieve_task_states", return_value=[])
class Test_generate_ants_test_logs_with_trac_formatting(unittest.TestCase):

    def test_retrieve_task_states_called_once(self, mock_retrieve_task_states):
        with NamedTemporaryFile() as temporary_file1, NamedTemporaryFile() as temporary_file2:

            replica_db_path = Path(temporary_file1.name)
            replica_target_file_path = Path(temporary_file2.name)
            generate_task_logs("trac", replica_db_path, replica_target_file_path)
            mock_retrieve_task_states.assert_called_once_with(replica_db_path)

    @patch("generate_ants_test_logs.generate_trac_summary", return_value="")
    def test_generate_trac_summary_called_once(
        self, mock_generate_trac_summary, mock_retrieve_task_states
    ):
        with NamedTemporaryFile() as temporary_file1, NamedTemporaryFile() as temporary_file2:

            replica_db_path = Path(temporary_file1.name)
            replica_target_file_path = Path(temporary_file2.name)
            generate_task_logs("trac", replica_db_path, replica_target_file_path)
            mock_generate_trac_summary.assert_called_once_with(
                mock_retrieve_task_states.return_value
            )

    def test_generate_formatted_trac_table_called_once(self, mock_retrieve_task_states):
        with patch(
            "generate_ants_test_logs.generate_trac_summary"
        ) as mock_generate_trac_summary:
            with patch(
                "generate_ants_test_logs.generate_formatted_trac_table"
            ) as mock_generate_formatted_trac_table:
                mock_generate_trac_summary.return_value = ""
                mock_generate_formatted_trac_table.return_value = ""

                with NamedTemporaryFile() as temporary_file1, NamedTemporaryFile() as temporary_file2:

                    replica_db_path = Path(temporary_file1.name)
                    replica_target_file_path = Path(temporary_file2.name)
                    generate_task_logs(
                        "trac", replica_db_path, replica_target_file_path
                    )
                    mock_generate_formatted_trac_table.assert_called_once_with(
                        mock_retrieve_task_states.return_value
                    )


@patch("generate_ants_test_logs.retrieve_task_states", return_value=[])
class Test_generate_ants_test_logs_with_github_formatting(unittest.TestCase):

    def test_retrieve_task_states_called_once(self, mock_retrieve_task_states):
        with NamedTemporaryFile() as temporary_file1, NamedTemporaryFile() as temporary_file2:

            replica_db_path = Path(temporary_file1.name)
            replica_target_file_path = Path(temporary_file2.name)
            generate_task_logs("gh", replica_db_path, replica_target_file_path)
            mock_retrieve_task_states.assert_called_once_with(replica_db_path)

    @patch("generate_ants_test_logs.generate_github_summary", return_value="")
    def test_generate_github_summary_called_once(
        self, mock_generate_github_summary, mock_retrieve_task_states
    ):
        with NamedTemporaryFile() as temporary_file1, NamedTemporaryFile() as temporary_file2:

            replica_db_path = Path(temporary_file1.name)
            replica_target_file_path = Path(temporary_file2.name)
            generate_task_logs("gh", replica_db_path, replica_target_file_path)
            mock_generate_github_summary.assert_called_once_with(
                mock_retrieve_task_states.return_value
            )

    def test_generate_formatted_github_table_called_once(
        self, mock_retrieve_task_states
    ):
        with patch(
            "generate_ants_test_logs.generate_github_summary"
        ) as mock_generate_github_summary:
            with patch(
                "generate_ants_test_logs.generate_formatted_github_table"
            ) as mock_generate_formatted_github_table:
                mock_generate_github_summary.return_value = ""
                mock_generate_formatted_github_table.return_value = ""
                with NamedTemporaryFile() as temporary_file1, NamedTemporaryFile() as temporary_file2:

                    replica_db_path = Path(temporary_file1.name)
                    replica_target_file_path = Path(temporary_file2.name)
                    generate_task_logs("gh", replica_db_path, replica_target_file_path)
                    mock_generate_formatted_github_table.assert_called_once_with(
                        mock_retrieve_task_states.return_value
                    )

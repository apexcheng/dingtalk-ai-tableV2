import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "aitable.py"
SPEC = importlib.util.spec_from_file_location("aitable_cli", SCRIPT_PATH)
AITABLE_CLI = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AITABLE_CLI)


class TestCli(unittest.TestCase):
    def run_cli(self, argv):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = AITABLE_CLI.main(argv)
        output = stdout.getvalue().strip()
        self.assertTrue(output)
        return exit_code, json.loads(output)

    def test_all_subcommands_dispatch(self):
        cases = [
            ("list-bases", ["--limit", "20", "--cursor", "cursor_1"], "handle_list_bases"),
            ("search-bases", ["--query", "评价", "--limit", "20"], "handle_search_bases"),
            ("get-tables", ["--base-id", "base12345", "--table-id", "tbl_1"], "handle_get_tables"),
            ("get-base", ["--base-id", "base12345"], "handle_get_base"),
            ("get-fields", ["--base-id", "base12345", "--table-id", "tbl_1", "--field-id", "fld_1"], "handle_get_fields"),
            ("create-fields", ["--base-id", "base12345", "--table-id", "tbl_1", "--field", '{"fieldName":"状态","type":"text"}'], "handle_create_fields"),
            ("resolve-table", ["--base-id", "base12345", "--table-name", "评价收集表"], "handle_resolve_table"),
            ("resolve-field", ["--base-id", "base12345", "--table-id", "tbl_1", "--field-name", "状态"], "handle_resolve_field"),
            ("resolve-option", ["--base-id", "base12345", "--table-id", "tbl_1", "--field-name", "状态", "--option-name", "进行中"], "handle_resolve_option"),
            ("build-filter", ["--operator", "eq", "--field-id", "fld_1", "--value", "1"], "handle_build_filter"),
            ("query-records", ["--base-id", "base12345", "--table-id", "tbl_1", "--output", "out/query.jsonl"], "handle_query_records"),
            ("create-records", ["--base-id", "base12345", "--table-id", "tbl_1", "--record", '{"cells":{"fld_1":"张三"}}'], "handle_create_records"),
            ("update-records", ["--base-id", "base12345", "--table-id", "tbl_1", "--record", '{"recordId":"rec_1","cells":{"fld_1":"李四"}}'], "handle_update_records"),
            ("delete-records", ["--base-id", "base12345", "--table-id", "tbl_1", "--record-id", "rec_1"], "handle_delete_records"),
            ("process-records-with-marker", ["--base-id", "base12345", "--table-id", "tbl_1", "--output", "out/process.jsonl"], "handle_process_records_with_marker"),
            ("process-date-range-with-marker", ["--base-id", "base12345", "--table-id", "tbl_1", "--date-field-id", "fld_date", "--start-date", "2026-06-01", "--end-date", "2026-06-02", "--output-dir", "out/daily"], "handle_process_date_range_with_marker"),
            ("prepare-attachment-upload", ["--base-id", "base12345", "--file-name", "example.png", "--size", "12345"], "handle_prepare_attachment_upload"),
        ]

        for command, argv_tail, handler_name in cases:
            with self.subTest(command=command):
                with patch.object(AITABLE_CLI, handler_name, return_value={"handler": handler_name}) as mocked:
                    exit_code, payload = self.run_cli([command, *argv_tail])

                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["command"], command)
                self.assertEqual(payload["result"]["handler"], handler_name)
                mocked.assert_called_once()

    def test_parser_help_includes_base_search_commands(self):
        help_text = AITABLE_CLI.build_parser().format_help()
        self.assertIn("list-bases", help_text)
        self.assertIn("search-bases", help_text)

    def test_list_bases_passes_limit_and_cursor(self):
        with patch.object(AITABLE_CLI, "list_bases", return_value={"bases": []}) as mocked:
            exit_code, payload = self.run_cli([
                "list-bases",
                "--limit", "20",
                "--cursor", "cursor_1",
            ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked.assert_called_once_with(limit=20, cursor="cursor_1")

    def test_search_bases_requires_query(self):
        exit_code, payload = self.run_cli([
            "search-bases",
            "--limit", "20",
        ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "CliError")
        self.assertIn("query 不能为空", payload["error"]["message"])

    def test_search_bases_strips_query(self):
        with patch.object(AITABLE_CLI, "search_bases", return_value={"bases": []}) as mocked:
            exit_code, payload = self.run_cli([
                "search-bases",
                "--query", "  评价  ",
                "--limit", "20",
            ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked.assert_called_once_with(query="评价", limit=20, cursor=None)

    def test_query_records_with_output_only_returns_summary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "records.jsonl"
            mock_result = {
                "records": [
                    {"recordId": "rec_1", "cells": {"fld_1": "a"}},
                    {"recordId": "rec_2", "cells": {"fld_1": "b"}},
                    {"recordId": "rec_3", "cells": {"fld_1": "c"}},
                    {"recordId": "rec_4", "cells": {"fld_1": "d"}},
                ],
                "hasMore": True,
                "nextCursor": "cursor_2",
            }
            with patch.object(AITABLE_CLI, "safe_query_records", return_value=mock_result):
                exit_code, payload = self.run_cli([
                    "query-records",
                    "--base-id", "base12345",
                    "--table-id", "table12345",
                    "--output", str(output_path),
                ])

            lines = output_path.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["total"], 4)
        self.assertEqual(len(payload["result"]["preview"]), 3)
        self.assertEqual(payload["result"]["output"], str(output_path.resolve()))
        self.assertNotIn("records", payload["result"])
        self.assertEqual(len(lines), 4)

    def test_resolve_table_returns_unique_match(self):
        with patch.object(
            AITABLE_CLI,
            "resolve_table",
            return_value={"tableId": "tbl_1", "tableName": "评价收集表"},
        ) as mocked:
            exit_code, payload = self.run_cli([
                "resolve-table",
                "--base-id", "base12345",
                "--table-name", "评价收集表",
            ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["tableId"], "tbl_1")
        self.assertEqual(payload["result"]["tableName"], "评价收集表")
        mocked.assert_called_once_with(base_id="base12345", table_name="评价收集表")

    def test_resolve_table_not_found_returns_clear_error(self):
        with patch.object(AITABLE_CLI, "resolve_table", side_effect=ValueError("未找到表：评价收集表")):
            exit_code, payload = self.run_cli([
                "resolve-table",
                "--base-id", "base12345",
                "--table-name", "评价收集表",
            ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "ValueError")
        self.assertEqual(payload["error"]["message"], "未找到表：评价收集表")

    def test_resolve_table_duplicate_name_returns_clear_error(self):
        with patch.object(AITABLE_CLI, "resolve_table", side_effect=ValueError("找到多个同名表，请人工确认")):
            exit_code, payload = self.run_cli([
                "resolve-table",
                "--base-id", "base12345",
                "--table-name", "评价收集表",
            ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "ValueError")
        self.assertEqual(payload["error"]["message"], "找到多个同名表，请人工确认")

    def test_process_records_delete_does_not_use_marker_update(self):
        batches = [
            {"records": [{"recordId": "rec_1", "cells": {"fld_1": "a"}}, {"recordId": "rec_2", "cells": {"fld_1": "b"}}]},
            {"records": [{"recordId": "rec_3", "cells": {"fld_1": "c"}}]},
            {"records": []},
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "delete.jsonl"
            with patch.object(AITABLE_CLI, "safe_query_records", side_effect=batches) as query_mock, patch.object(AITABLE_CLI, "safe_delete_records") as delete_mock, patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=AssertionError("marker path should not be used")):
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--base-id", "base12345",
                    "--table-id", "table12345",
                    "--filters-json", '{"operator":"eq","operands":["fld_1","a"]}',
                    "--output", str(output_path),
                    "--action", "delete",
                ])

            lines = output_path.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["summary"]["action"], "delete")
        self.assertEqual(payload["result"]["summary"]["batchCount"], 2)
        self.assertEqual(payload["result"]["summary"]["recordCount"], 3)
        self.assertEqual(len(lines), 3)
        self.assertEqual(query_mock.call_count, 3)
        self.assertEqual(delete_mock.call_count, 2)

    def test_process_records_delete_requires_filters(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "delete.jsonl"
            with patch.object(AITABLE_CLI, "safe_query_records") as query_mock, patch.object(AITABLE_CLI, "safe_delete_records") as delete_mock:
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--base-id", "base12345",
                    "--table-id", "table12345",
                    "--output", str(output_path),
                    "--action", "delete",
                ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "CliError")
        self.assertIn("action=delete", payload["error"]["message"])
        query_mock.assert_not_called()
        delete_mock.assert_not_called()

    def test_process_date_range_with_marker_writes_daily_jsonl(self):
        def fake_process_records_with_marker(**kwargs):
            date_value = kwargs["task_name"].rsplit("_", 1)[-1]
            kwargs["process_batch"]([{"recordId": f"rec_{date_value}", "cells": {"date": date_value}}])
            return f"task_{date_value}"

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker):
                exit_code, payload = self.run_cli([
                    "process-date-range-with-marker",
                    "--base-id", "base12345",
                    "--table-id", "table12345",
                    "--date-field-id", "fld123456",
                    "--start-date", "2026-06-01",
                    "--end-date", "2026-06-02",
                    "--output-dir", tmp_dir,
                ])

            first_file = Path(payload["result"]["results"][0]["output"])
            second_file = Path(payload["result"]["results"][1]["output"])
            self.assertTrue(first_file.exists())
            self.assertTrue(second_file.exists())
            first_lines = first_file.read_text(encoding="utf-8").strip().splitlines()
            second_lines = second_file.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["summary"]["dayCount"], 2)
        self.assertEqual(payload["result"]["summary"]["recordCount"], 2)
        self.assertEqual(len(payload["result"]["results"]), 2)
        self.assertEqual(len(first_lines), 1)
        self.assertEqual(len(second_lines), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

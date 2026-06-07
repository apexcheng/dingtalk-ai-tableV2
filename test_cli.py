import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "aitable.py"
SPEC = importlib.util.spec_from_file_location("aitable_cli", SCRIPT_PATH)
AITABLE_CLI = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AITABLE_CLI)


class TestCli(unittest.TestCase):
    def setUp(self):
        # These tests predate the heavy-field auto-exclusion feature; they assume
        # the CLI just runs without ever calling get_tables. Provide a safe default
        # schema so tests that don't care about field selection keep working.
        self._default_light_patcher = patch.object(
            AITABLE_CLI,
            'fetch_light_field_ids',
            return_value=(['fld_default_a', 'fld_default_b'], []),
        )
        self._default_light_patcher.start()

    def tearDown(self):
        self._default_light_patcher.stop()

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

    def test_parse_json_value_handles_non_string_values(self):
        cases = [
            (123, 123),
            (True, True),
            (["a", "b"], ["a", "b"]),
            ({"k": "v"}, {"k": "v"}),
            ("plain string", "plain string"),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(AITABLE_CLI.parse_json_value(value), expected)

    def test_process_records_default_action_uses_export_with_marker(self):
        def fake_process_records_with_marker(**kwargs):
            kwargs["process_batch"]([])
            return "task_marker_1"

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "process.json"
            output_path = Path(tmp_dir) / "process.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filters": {"operator": "eq", "operands": ["fld_1", "a"]},
                        "output": str(output_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker):
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["summary"]["action"], "export-with-marker")
        self.assertEqual(payload["result"]["taskMarker"], "task_marker_1")

    def test_process_records_input_update_action_can_take_effect(self):
        def fake_process_records_with_marker(**kwargs):
            kwargs["process_batch"]([{"recordId": "rec_1", "cells": {"fld_1": "a"}}])
            return "task_marker_2"

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "process_update.json"
            output_path = Path(tmp_dir) / "process_update.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filters": {"operator": "eq", "operands": ["fld_1", "a"]},
                        "output": str(output_path),
                        "action": "update",
                        "updateCells": {"fld_1": "b"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker) as mocked_process, patch.object(AITABLE_CLI, "safe_update_records") as mocked_update:
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["summary"]["action"], "update")
        self.assertEqual(payload["result"]["taskMarker"], "task_marker_2")
        self.assertEqual(mocked_process.call_count, 1)
        self.assertEqual(mocked_update.call_count, 1)

    def test_process_records_update_empty_update_cells_fails_before_output_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "process_update_empty.json"
            output_path = Path(tmp_dir) / "process_update_empty.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filters": {"operator": "eq", "operands": ["fld_1", "a"]},
                        "output": str(output_path),
                        "action": "update",
                        "updateCells": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            exit_code, payload = self.run_cli([
                "process-records-with-marker",
                "--input", str(input_path),
            ])

            file_exists = output_path.exists()

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "CliError")
        self.assertIn("action=update 时必须提供非空 updateCells", payload["error"]["message"])
        self.assertFalse(file_exists)

    def test_process_records_input_delete_action_can_take_effect(self):
        batches = [
            {"records": [{"recordId": "rec_1", "cells": {"fld_1": "a"}}]},
            {"records": []},
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "process_delete.json"
            output_path = Path(tmp_dir) / "process_delete.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filters": {"operator": "eq", "operands": ["fld_1", "a"]},
                        "output": str(output_path),
                        "action": "delete",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "safe_query_records", side_effect=batches) as mocked_query, patch.object(AITABLE_CLI, "safe_delete_records") as mocked_delete:
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["summary"]["action"], "delete")
        self.assertEqual(mocked_query.call_count, 2)
        self.assertEqual(mocked_delete.call_count, 1)

    def test_process_records_without_filters_or_sort_fails_before_output_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "should_not_exist.jsonl"
            input_path = Path(tmp_dir) / "process_invalid.json"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "output": str(output_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            exit_code, payload = self.run_cli([
                "process-records-with-marker",
                "--input", str(input_path),
            ])

            file_exists = output_path.exists()

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "CliError")
        self.assertIn("process-records-with-marker 仅适用于带 filters 的场景；无过滤条件不要使用", payload["error"]["message"])
        self.assertFalse(file_exists)

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

    def test_process_date_range_update_empty_update_cells_fails_before_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "daily"
            input_path = Path(tmp_dir) / "process_date_update_empty.json"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "dateFieldId": "fld123456",
                        "startDate": "2026-06-01",
                        "endDate": "2026-06-02",
                        "outputDir": str(output_dir),
                        "action": "update",
                        "updateCells": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker") as process_mock, patch.object(AITABLE_CLI, "safe_update_records") as update_mock:
                exit_code, payload = self.run_cli([
                    "process-date-range-with-marker",
                    "--input", str(input_path),
                ])

            output_exists = output_dir.exists()
            first_file_exists = (output_dir / "2026-06-01.jsonl").exists()
            second_file_exists = (output_dir / "2026-06-02.jsonl").exists()

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "CliError")
        self.assertIn("action=update 时必须提供非空 updateCells", payload["error"]["message"])
        self.assertFalse(output_exists)
        self.assertFalse(first_file_exists)
        self.assertFalse(second_file_exists)
        process_mock.assert_not_called()
        update_mock.assert_not_called()

    def test_process_date_range_update_non_empty_update_cells_still_works(self):
        def fake_process_records_with_marker(**kwargs):
            date_value = kwargs["task_name"].rsplit("_", 1)[-1]
            kwargs["process_batch"]([{"recordId": f"rec_{date_value}", "cells": {"date": date_value}}])
            return f"task_{date_value}"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "daily"
            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker) as process_mock, patch.object(AITABLE_CLI, "safe_update_records") as update_mock:
                exit_code, payload = self.run_cli([
                    "process-date-range-with-marker",
                    "--base-id", "base12345",
                    "--table-id", "table12345",
                    "--date-field-id", "fld123456",
                    "--start-date", "2026-06-01",
                    "--end-date", "2026-06-02",
                    "--output-dir", str(output_dir),
                    "--action", "update",
                    "--update-cells-json", '{"fld_1":"b"}',
                ])

            first_file = Path(payload["result"]["results"][0]["output"])
            second_file = Path(payload["result"]["results"][1]["output"])
            first_lines = first_file.read_text(encoding="utf-8").strip().splitlines()
            second_lines = second_file.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["summary"]["action"], "update")
        self.assertEqual(payload["result"]["summary"]["dayCount"], 2)
        self.assertEqual(len(payload["result"]["results"]), 2)
        self.assertEqual(len(first_lines), 1)
        self.assertEqual(len(second_lines), 1)
        self.assertEqual(process_mock.call_count, 2)
        self.assertEqual(update_mock.call_count, 2)

    def test_query_records_input_filter_singular_is_passed_as_filters(self):
        filter_obj = {"operator": "eq", "operands": ["fld_1", "a"]}

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "query_filter.json"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filter": filter_obj,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked:
                exit_code, payload = self.run_cli([
                    "query-records",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked.assert_called_once()
        _, kwargs = mocked.call_args
        self.assertEqual(kwargs["filters"], filter_obj)

    def test_query_records_input_filters_plural_still_works(self):
        filters_obj = {"operator": "eq", "operands": ["fld_1", "a"]}

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "query_filters.json"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filters": filters_obj,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked:
                exit_code, payload = self.run_cli([
                    "query-records",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked.assert_called_once()
        _, kwargs = mocked.call_args
        self.assertEqual(kwargs["filters"], filters_obj)

    def test_query_records_filters_json_overrides_input_filter(self):
        input_filter = {"operator": "eq", "operands": ["fld_1", "a"]}
        cli_filter = {"operator": "eq", "operands": ["fld_1", "b"]}

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "query_override.json"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filter": input_filter,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked:
                exit_code, payload = self.run_cli([
                    "query-records",
                    "--input", str(input_path),
                    "--filters-json", json.dumps(cli_filter, ensure_ascii=False),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked.assert_called_once()
        _, kwargs = mocked.call_args
        self.assertEqual(kwargs["filters"], cli_filter)

    def test_process_records_with_marker_input_filter_singular_is_passed_as_filters(self):
        filter_obj = {"operator": "eq", "operands": ["fld_1", "a"]}

        def fake_process_records_with_marker(**kwargs):
            kwargs["process_batch"]([])
            return "task_marker_filter_singular"

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "process_filter.json"
            output_path = Path(tmp_dir) / "process_filter.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filter": filter_obj,
                        "output": str(output_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker) as mocked:
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["taskMarker"], "task_marker_filter_singular")
        mocked.assert_called_once()
        _, kwargs = mocked.call_args
        self.assertEqual(kwargs["filters"], filter_obj)

    def test_process_records_with_marker_input_filters_plural_still_works(self):
        filters_obj = {"operator": "eq", "operands": ["fld_1", "a"]}

        def fake_process_records_with_marker(**kwargs):
            kwargs["process_batch"]([])
            return "task_marker_filters_plural"

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "process_filters.json"
            output_path = Path(tmp_dir) / "process_filters.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filters": filters_obj,
                        "output": str(output_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker) as mocked:
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["taskMarker"], "task_marker_filters_plural")
        mocked.assert_called_once()
        _, kwargs = mocked.call_args
        self.assertEqual(kwargs["filters"], filters_obj)

    def test_process_records_with_marker_filters_json_overrides_input_filter(self):
        input_filter = {"operator": "eq", "operands": ["fld_1", "a"]}
        cli_filter = {"operator": "eq", "operands": ["fld_1", "b"]}

        def fake_process_records_with_marker(**kwargs):
            kwargs["process_batch"]([])
            return "task_marker_override"

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "process_override.json"
            output_path = Path(tmp_dir) / "process_override.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "filter": input_filter,
                        "output": str(output_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker) as mocked:
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--input", str(input_path),
                    "--filters-json", json.dumps(cli_filter, ensure_ascii=False),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["taskMarker"], "task_marker_override")
        mocked.assert_called_once()
        _, kwargs = mocked.call_args
        self.assertEqual(kwargs["filters"], cli_filter)

    def test_process_date_range_with_marker_input_filter_singular_is_passed_as_filters(self):
        filter_obj = {"operator": "eq", "operands": ["fld_1", "a"]}
        captured_filters = []

        def fake_process_records_with_marker(**kwargs):
            captured_filters.append(kwargs["filters"])
            kwargs["process_batch"]([])
            return "task_marker_date_filter"

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "date_range_filter.json"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "dateFieldId": "fld123456",
                        "startDate": "2026-06-01",
                        "endDate": "2026-06-01",
                        "filter": filter_obj,
                        "outputDir": tmp_dir,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker):
                exit_code, payload = self.run_cli([
                    "process-date-range-with-marker",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(captured_filters), 1)
        # base filter must be preserved and merged with the day filter via and_filter
        outer_operator = captured_filters[0]["operator"]
        self.assertEqual(outer_operator, "and")
        # the user-supplied filter must appear among the operands
        self.assertIn(filter_obj, captured_filters[0]["operands"])

    def test_process_date_range_with_marker_input_filters_plural_still_works(self):
        filters_obj = {"operator": "eq", "operands": ["fld_1", "a"]}
        captured_filters = []

        def fake_process_records_with_marker(**kwargs):
            captured_filters.append(kwargs["filters"])
            kwargs["process_batch"]([])
            return "task_marker_date_filters"

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "date_range_filters.json"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "dateFieldId": "fld123456",
                        "startDate": "2026-06-01",
                        "endDate": "2026-06-01",
                        "filters": filters_obj,
                        "outputDir": tmp_dir,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker):
                exit_code, payload = self.run_cli([
                    "process-date-range-with-marker",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(captured_filters), 1)
        outer_operator = captured_filters[0]["operator"]
        self.assertEqual(outer_operator, "and")
        self.assertIn(filters_obj, captured_filters[0]["operands"])

    def test_process_date_range_with_marker_filters_json_overrides_input_filter(self):
        input_filter = {"operator": "eq", "operands": ["fld_1", "a"]}
        cli_filter = {"operator": "eq", "operands": ["fld_1", "b"]}
        captured_filters = []

        def fake_process_records_with_marker(**kwargs):
            captured_filters.append(kwargs["filters"])
            kwargs["process_batch"]([])
            return "task_marker_date_override"

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "date_range_override.json"
            input_path.write_text(
                json.dumps(
                    {
                        "baseId": "base12345",
                        "tableId": "table12345",
                        "dateFieldId": "fld123456",
                        "startDate": "2026-06-01",
                        "endDate": "2026-06-01",
                        "filter": input_filter,
                        "outputDir": tmp_dir,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker):
                exit_code, payload = self.run_cli([
                    "process-date-range-with-marker",
                    "--input", str(input_path),
                    "--filters-json", json.dumps(cli_filter, ensure_ascii=False),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(captured_filters), 1)
        outer_operator = captured_filters[0]["operator"]
        self.assertEqual(outer_operator, "and")
        self.assertIn(cli_filter, captured_filters[0]["operands"])
        self.assertNotIn(input_filter, captured_filters[0]["operands"])


class TestHeavyFieldAutoExclusion(unittest.TestCase):
    """query-records / process-* 默认从 get_tables 拉字段表，剔除 attachment / image / picture / file。"""

    def run_cli(self, argv):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = AITABLE_CLI.main(argv)
        return exit_code, json.loads(stdout.getvalue().strip())

    SAMPLE_FIELDS = [
        {"fieldId": "fld_text", "fieldName": "订单号", "type": "text"},
        {"fieldId": "fld_pic", "fieldName": "图片", "type": "attachment"},
        {"fieldId": "fld_date", "fieldName": "评价时间", "type": "date"},
        {"fieldId": "fld_image", "fieldName": "图片集", "type": "image"},
    ]

    def test_query_records_auto_excludes_heavy_fields(self):
        with patch.object(AITABLE_CLI, "fetch_light_field_ids", return_value=(
            ["fld_text", "fld_date"],
            [{"fieldId": "fld_pic", "fieldName": "图片", "type": "attachment"}],
        )) as mocked_fetch, patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked_query:
            exit_code, payload = self.run_cli([
                "query-records",
                "--base-id", "base12345",
                "--table-id", "table12345",
            ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked_fetch.assert_called_once_with("base12345", "table12345")
        _, kwargs = mocked_query.call_args
        self.assertEqual(kwargs["field_ids"], ["fld_text", "fld_date"])
        self.assertEqual(
            payload["result"]["excludedFields"],
            [{"fieldId": "fld_pic", "fieldName": "图片", "type": "attachment"}],
        )

    def test_query_records_user_field_ids_skips_auto_exclusion(self):
        with patch.object(AITABLE_CLI, "fetch_light_field_ids") as mocked_fetch, patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked_query:
            exit_code, payload = self.run_cli([
                "query-records",
                "--base-id", "base12345",
                "--table-id", "table12345",
                "--field-id", "fld_pic",
                "--field-id", "fld_date",
            ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked_fetch.assert_not_called()
        _, kwargs = mocked_query.call_args
        self.assertEqual(kwargs["field_ids"], ["fld_pic", "fld_date"])
        self.assertNotIn("excludedFields", payload["result"])

    def test_query_records_input_field_ids_skips_auto_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "q.json"
            input_path.write_text(json.dumps({
                "baseId": "base12345",
                "tableId": "table12345",
                "fieldIds": ["fld_pic"],
            }, ensure_ascii=False), encoding="utf-8")

            with patch.object(AITABLE_CLI, "fetch_light_field_ids") as mocked_fetch, patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked_query:
                exit_code, payload = self.run_cli([
                    "query-records",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked_fetch.assert_not_called()
        _, kwargs = mocked_query.call_args
        self.assertEqual(kwargs["field_ids"], ["fld_pic"])

    def test_query_records_include_heavy_fields_skips_auto_exclusion(self):
        with patch.object(AITABLE_CLI, "fetch_light_field_ids") as mocked_fetch, patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked_query:
            exit_code, payload = self.run_cli([
                "query-records",
                "--base-id", "base12345",
                "--table-id", "table12345",
                "--include-heavy-fields",
            ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked_fetch.assert_not_called()
        _, kwargs = mocked_query.call_args
        self.assertIsNone(kwargs["field_ids"])
        self.assertNotIn("excludedFields", payload["result"])

    def test_query_records_get_tables_failure_raises_instead_of_silently_returning_all_fields(self):
        # 拉不到 schema 也不能静默退回到“全字段”查询。
        with patch.object(AITABLE_CLI, "fetch_light_field_ids", side_effect=RuntimeError("无法获取字段结构")):
            exit_code, payload = self.run_cli([
                "query-records",
                "--base-id", "base12345",
                "--table-id", "table12345",
            ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("无法获取字段结构", payload["error"]["message"])

    def test_query_records_input_include_heavy_fields_camel_case_skips_auto_exclusion(self):
        with patch.object(AITABLE_CLI, "fetch_light_field_ids") as mocked_fetch, patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked_query:
            exit_code, payload = self.run_cli([
                "query-records",
                "--base-id", "base12345",
                "--table-id", "table12345",
                "--filters-json", '{"operator":"date_eq","operands":["fld_date","2026-06-03"]}',
                "--include-heavy-fields",
            ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked_fetch.assert_not_called()
        _, kwargs = mocked_query.call_args
        self.assertIsNone(kwargs["field_ids"])
        self.assertNotIn("excludedFields", payload["result"])

    def test_query_records_input_json_includeHeavyFields_skips_auto_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "q.json"
            input_path.write_text(json.dumps({
                "baseId": "base12345",
                "tableId": "table12345",
                "includeHeavyFields": True,
            }, ensure_ascii=False), encoding="utf-8")

            with patch.object(AITABLE_CLI, "fetch_light_field_ids") as mocked_fetch, patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked_query:
                exit_code, payload = self.run_cli([
                    "query-records",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked_fetch.assert_not_called()
        _, kwargs = mocked_query.call_args
        self.assertIsNone(kwargs["field_ids"])
        self.assertNotIn("excludedFields", payload["result"])

    def test_query_records_input_json_include_heavy_fields_snake_case_skips_auto_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "q.json"
            input_path.write_text(json.dumps({
                "baseId": "base12345",
                "tableId": "table12345",
                "include_heavy_fields": True,
            }, ensure_ascii=False), encoding="utf-8")

            with patch.object(AITABLE_CLI, "fetch_light_field_ids") as mocked_fetch, patch.object(AITABLE_CLI, "safe_query_records", return_value={"records": []}) as mocked_query:
                exit_code, payload = self.run_cli([
                    "query-records",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        mocked_fetch.assert_not_called()
        _, kwargs = mocked_query.call_args
        self.assertIsNone(kwargs["field_ids"])
        self.assertNotIn("excludedFields", payload["result"])

    def test_process_records_with_marker_auto_excludes_heavy_fields(self):
        def fake_process_records_with_marker(**kwargs):
            kwargs["process_batch"]([])
            return "task_marker_heavy"

        with patch.object(AITABLE_CLI, "fetch_light_field_ids", return_value=(
            ["fld_date"],
            [{"fieldId": "fld_pic", "fieldName": "图片", "type": "attachment"}],
        )), patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker) as mocked_process:
            exit_code, payload = self.run_cli([
                "process-records-with-marker",
                "--base-id", "base12345",
                "--table-id", "table12345",
                "--filters-json", '{"operator":"date_eq","operands":["fld_date","2026-06-03"]}',
                "--output", "/tmp/heavy_marker.jsonl",
            ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        _, kwargs = mocked_process.call_args
        self.assertEqual(kwargs["field_ids"], ["fld_date"])
        self.assertEqual(
            payload["result"]["excludedFields"],
            [{"fieldId": "fld_pic", "fieldName": "图片", "type": "attachment"}],
        )

    def test_process_records_with_marker_include_heavy_fields_skips_auto_exclusion(self):
        def fake_process_records_with_marker(**kwargs):
            kwargs["process_batch"]([])
            return "task_marker_full"

        with patch.object(AITABLE_CLI, "fetch_light_field_ids") as mocked_fetch, patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker) as mocked_process:
            exit_code, payload = self.run_cli([
                "process-records-with-marker",
                "--base-id", "base12345",
                "--table-id", "table12345",
                "--filters-json", '{"operator":"date_eq","operands":["fld_date","2026-06-03"]}',
                "--output", "/tmp/heavy_marker.jsonl",
                "--include-heavy-fields",
            ])

        self.assertEqual(exit_code, 0)
        mocked_fetch.assert_not_called()
        _, kwargs = mocked_process.call_args
        self.assertIsNone(kwargs["field_ids"])
        self.assertNotIn("excludedFields", payload["result"])

    def test_process_date_range_with_marker_auto_excludes_heavy_fields(self):
        captured = []

        def fake_process_records_with_marker(**kwargs):
            captured.append(kwargs["field_ids"])
            kwargs["process_batch"]([])
            return "task_marker_date"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "daily"
            with patch.object(AITABLE_CLI, "fetch_light_field_ids", return_value=(
                ["fld_date"],
                [{"fieldId": "fld_pic", "fieldName": "图片", "type": "attachment"}],
            )), patch.object(AITABLE_CLI, "process_records_with_marker", side_effect=fake_process_records_with_marker):
                exit_code, payload = self.run_cli([
                    "process-date-range-with-marker",
                    "--base-id", "base12345",
                    "--table-id", "table12345",
                    "--date-field-id", "fld_date",
                    "--start-date", "2026-06-03",
                    "--end-date", "2026-06-03",
                    "--output-dir", str(output_dir),
                ])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(captured, [["fld_date"]])
        self.assertEqual(
            payload["result"]["excludedFields"],
            [{"fieldId": "fld_pic", "fieldName": "图片", "type": "attachment"}],
        )


class TestClientTruncationDetection(unittest.TestCase):
    """client.py 会在 response 被 pipe buffer 截断时主动报 TruncatedResponseError。

    JSONDecodeError.msg 保留原始双引号。必须能匹配 "Expecting ',' delimiter"，
    不再被看作“普通 JSON 错误”。
    """

    def test_truncation_message_set_includes_comma_delimiter(self):
        # client.py 中的 truncation 匹配集合必须包含 "Expecting ',' delimiter" 字面串。
        # json.JSONDecodeError.msg 保留原始源里的双引号，不能写成单引号。
        import ast
        import dingtalk_ai_table.client as cli_mod
        with open(cli_mod.__file__, "r", encoding="utf-8") as f:
            source = f.read()
        # 提取 client.py 中 "in (" 后的元组字面量
        idx = source.find('exc.msg in (')
        self.assertGreaterEqual(idx, 0, "client.py 应包含 truncation 匹配集")
        end = source.find(')', idx)
        snippet = source[idx + len('exc.msg in ('):end]
        keywords = ast.literal_eval('(' + snippet + ')')
        self.assertIn("Expecting ',' delimiter", keywords)

    def test_truncation_message_actually_matches_python_json(self):
        # 真正验证：构造一个 JSON 文本，让 Python 抛出 "Expecting ',' delimiter"。
        # （"Expecting ',' delimiter" 在 Python 3.9 由两个连续 value 产生，msg 带双引号）
        import json
        try:
            json.loads(b'{"a": 1 2}')
        except json.JSONDecodeError as exc:
            self.assertEqual(exc.msg, "Expecting ',' delimiter")

    def test_pipe_buffer_truncation_raises_TruncatedResponseError(self):
        # 真实 mcporter 响应在 ~64KB 处被截断，JSON 以 "Expecting ',' delimiter" 报错。
        # client.py 必须能识别为截断，而不是当作“普通解析错误”丢掉。
        from dingtalk_ai_table.client import TruncatedResponseError, run_mcporter
        import dingtalk_ai_table.client as cli_mod

        # 构造一个 65000+ 字节的 JSON 文本，触发 comma delimiter 错误。
        # 两个连续 value 会产生 "Expecting ',' delimiter" 错误。
        # 长度要 >= 55KB 才会被 client.py 的 truncation 检测识别（超过 pipe buffer 阈值）。
        record = b'{"x":"' + b'Y' * 500 + b'"},'
        bad_json = b'{"data":{"records":[' + record * 110 + b' 1 2 3'  # ~56KB 字节

        with patch.object(cli_mod, "build_mcporter_env", return_value={}), \
             patch("subprocess.run") as mocked_run:
            mocked_run.return_value = SimpleNamespace(
                returncode=0,
                stdout=bad_json,
                stderr=b'',
            )
            with self.assertRaises(TruncatedResponseError):
                run_mcporter(["query_records", "--args", "{}"])


class TestMarkerSortForbidden(unittest.TestCase):
    """marker 系列命令禁止 sort——marker 回写会修改结果集，造成排序分页重复 / 漏数据。"""

    def run_cli(self, argv):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = AITABLE_CLI.main(argv)
        return exit_code, json.loads(stdout.getvalue().strip())

    def test_process_records_with_marker_rejects_cli_sort_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "p.json"
            output_path = Path(tmp_dir) / "p.jsonl"
            input_path.write_text(json.dumps({
                "baseId": "base12345",
                "tableId": "table12345",
                "filters": {"operator": "date_eq", "operands": ["fld_date", "2026-06-03"]},
                "output": str(output_path),
            }, ensure_ascii=False), encoding="utf-8")

            with patch.object(AITABLE_CLI, "process_records_with_marker") as mocked_process:
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--input", str(input_path),
                    "--sort-json", '[{"fieldId":"fld_date","direction":"ASC"}]',
                ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("process-records-with-marker 不支持 sort", payload["error"]["message"])
        self.assertIn("重复或漏数据", payload["error"]["message"])
        mocked_process.assert_not_called()

    def test_process_records_with_marker_rejects_input_json_sort(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "p.json"
            output_path = Path(tmp_dir) / "p.jsonl"
            input_path.write_text(json.dumps({
                "baseId": "base12345",
                "tableId": "table12345",
                "filters": {"operator": "date_eq", "operands": ["fld_date", "2026-06-03"]},
                "output": str(output_path),
                "sort": [{"fieldId": "fld_date", "direction": "ASC"}],
            }, ensure_ascii=False), encoding="utf-8")

            with patch.object(AITABLE_CLI, "process_records_with_marker") as mocked_process:
                exit_code, payload = self.run_cli([
                    "process-records-with-marker",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("process-records-with-marker 不支持 sort", payload["error"]["message"])
        mocked_process.assert_not_called()

    def test_process_date_range_with_marker_rejects_cli_sort_json(self):
        with patch.object(AITABLE_CLI, "process_records_with_marker") as mocked_process:
            exit_code, payload = self.run_cli([
                "process-date-range-with-marker",
                "--base-id", "base12345",
                "--table-id", "table12345",
                "--date-field-id", "fld_date",
                "--start-date", "2026-06-01",
                "--end-date", "2026-06-01",
                "--output-dir", "/tmp/sort_reject_test",
                "--sort-json", '[{"fieldId":"fld_date","direction":"ASC"}]',
            ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("process-date-range-with-marker 不支持 sort", payload["error"]["message"])
        self.assertIn("重复或漏数据", payload["error"]["message"])
        mocked_process.assert_not_called()

    def test_process_date_range_with_marker_rejects_input_json_sort(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "pdr.json"
            input_path.write_text(json.dumps({
                "sort": [{"fieldId": "fld_date", "direction": "ASC"}],
            }, ensure_ascii=False), encoding="utf-8")
            with patch.object(AITABLE_CLI, "process_records_with_marker") as mocked_process:
                exit_code, payload = self.run_cli([
                    "process-date-range-with-marker",
                    "--base-id", "base12345",
                    "--table-id", "table12345",
                    "--date-field-id", "fld_date",
                    "--start-date", "2026-06-01",
                    "--end-date", "2026-06-01",
                    "--output-dir", "/tmp/sort_reject_test2",
                    "--input", str(input_path),
                ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("process-date-range-with-marker 不支持 sort", payload["error"]["message"])
        mocked_process.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

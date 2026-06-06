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

    def test_process_records_with_marker_requires_output(self):
        exit_code, payload = self.run_cli([
            "process-records-with-marker",
            "--base-id", "base12345",
            "--table-id", "table12345",
            "--filters-json", '{"operator":"eq","operands":["fld123456","x"]}',
        ])

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "process-records-with-marker")

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

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["result"]["summary"]["dayCount"], 2)
            self.assertEqual(payload["result"]["summary"]["recordCount"], 2)
            self.assertEqual(len(payload["result"]["results"]), 2)

            first_file = Path(payload["result"]["results"][0]["output"])
            second_file = Path(payload["result"]["results"][1]["output"])
            self.assertTrue(first_file.exists())
            self.assertTrue(second_file.exists())
            self.assertEqual(len(first_file.read_text(encoding="utf-8").strip().splitlines()), 1)
            self.assertEqual(len(second_file.read_text(encoding="utf-8").strip().splitlines()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

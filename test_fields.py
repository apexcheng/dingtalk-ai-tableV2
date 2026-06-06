import unittest
from unittest.mock import patch

from dingtalk_ai_table.fields import get_table_by_name, list_bases, search_bases


class TestBaseQueryHelpers(unittest.TestCase):
    def test_list_bases_without_args_calls_mcporter(self):
        with patch("dingtalk_ai_table.fields.run_mcporter", return_value={"bases": []}) as mocked:
            result = list_bases()

        self.assertEqual(result, {"bases": []})
        mocked.assert_called_once_with(["list_bases"])

    def test_search_bases_strips_query_and_builds_args(self):
        with patch("dingtalk_ai_table.fields.run_mcporter", return_value={"bases": []}) as mocked:
            result = search_bases("  evaluation  ", limit=10, cursor="cursor_1")

        self.assertEqual(result, {"bases": []})
        mocked.assert_called_once()
        args = mocked.call_args.args[0]
        self.assertEqual(args[0], "search_bases")
        self.assertEqual(args[1], "--args")
        self.assertIn('"query": "evaluation"', args[2])
        self.assertIn('"limit": 10', args[2])
        self.assertIn('"cursor": "cursor_1"', args[2])


class TestGetTableByName(unittest.TestCase):
    def test_get_table_by_name_returns_unique_match(self):
        payload = {
            "tables": [
                {"tableId": "tbl_12345", "tableName": "  评价收集表  "},
                {"tableId": "tbl_67890", "tableName": "其他表"},
            ]
        }

        with patch("dingtalk_ai_table.fields.get_base", return_value=payload):
            result = get_table_by_name("base12345", "  评价收集表  ")

        self.assertEqual(result, {"tableId": "tbl_12345", "tableName": "评价收集表"})

    def test_get_table_by_name_supports_name_field_with_spaces(self):
        payload = {
            "tables": [
                {"tableId": "tbl_12345", "name": "  评价收集表  "},
            ]
        }

        with patch("dingtalk_ai_table.fields.get_base", return_value=payload):
            result = get_table_by_name("base12345", "评价收集表")

        self.assertEqual(result, {"tableId": "tbl_12345", "tableName": "评价收集表"})

    def test_get_table_by_name_raises_when_table_list_empty(self):
        payload = {"tables": []}

        with patch("dingtalk_ai_table.fields.get_base", return_value=payload):
            with self.assertRaisesRegex(
                ValueError,
                "get_base 未返回表列表，无法解析表名：评价收集表",
            ):
                get_table_by_name("base12345", "评价收集表")

    def test_get_table_by_name_raises_when_not_found(self):
        payload = {
            "tables": [
                {"tableId": "tbl_67890", "tableName": "其他表"},
            ]
        }

        with patch("dingtalk_ai_table.fields.get_base", return_value=payload):
            with self.assertRaisesRegex(ValueError, "未找到表：评价收集表"):
                get_table_by_name("base12345", "评价收集表")

    def test_get_table_by_name_raises_when_duplicate(self):
        payload = {
            "tables": [
                {"tableId": "tbl_12345", "tableName": "评价收集表"},
                {"tableId": "tbl_67890", "tableName": "评价收集表"},
            ]
        }

        with patch("dingtalk_ai_table.fields.get_base", return_value=payload):
            with self.assertRaisesRegex(ValueError, "找到多个同名表，请人工确认"):
                get_table_by_name("base12345", "评价收集表")


if __name__ == "__main__":
    unittest.main(verbosity=2)

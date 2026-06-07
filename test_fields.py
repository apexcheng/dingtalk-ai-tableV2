import unittest
from unittest.mock import patch

from dingtalk_ai_table.fields import (
    HEAVY_FIELD_TYPES,
    fetch_light_field_ids,
    get_table_by_name,
    list_bases,
    resolve_light_field_ids,
    search_bases,
)


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


class TestResolveLightFieldIds(unittest.TestCase):
    SAMPLE_FIELDS = [
        {"fieldId": "fld_text", "fieldName": "订单号", "type": "text"},
        {"fieldId": "fld_pic", "fieldName": "图片", "type": "attachment"},
        {"fieldId": "fld_date", "fieldName": "评价时间", "type": "date"},
        {"fieldId": "fld_sel", "fieldName": "店铺", "type": "singleSelect"},
        {"fieldId": "fld_image", "fieldName": "图片集", "type": "image"},
        {"fieldId": "fld_picture", "fieldName": "封面图", "type": "picture"},
        {"fieldId": "fld_file", "fieldName": "附件", "type": "file"},
        {"fieldId": "fld_rich", "fieldName": "备注", "type": "richText"},
        {"fieldId": "fld_unk", "fieldName": "未知类型字段", "type": "未知类型"},
        {"fieldId": "fld_no_type", "fieldName": "无 type 字段"},
    ]

    def test_heavy_types_constant(self):
        self.assertEqual(HEAVY_FIELD_TYPES, {"attachment", "image", "picture", "file"})

    def test_resolve_splits_heavy_and_light(self):
        light, excluded = resolve_light_field_ids(self.SAMPLE_FIELDS)
        self.assertEqual(light, [
            "fld_text", "fld_date", "fld_sel", "fld_rich", "fld_unk", "fld_no_type",
        ])
        excluded_ids = [item["fieldId"] for item in excluded]
        self.assertEqual(excluded_ids, ["fld_pic", "fld_image", "fld_picture", "fld_file"])
        # unknown / missing type 默认为轻字段
        self.assertNotIn("fld_unk", excluded_ids)
        self.assertNotIn("fld_no_type", excluded_ids)
        for item in excluded:
            self.assertIn("fieldId", item)
            self.assertIn("fieldName", item)
            self.assertIn("type", item)
            self.assertIn(item["type"], HEAVY_FIELD_TYPES)

    def test_empty_input(self):
        light, excluded = resolve_light_field_ids([])
        self.assertEqual(light, [])
        self.assertEqual(excluded, [])

    def test_skips_non_dict_entries(self):
        light, excluded = resolve_light_field_ids([None, "str", 123, {"fieldId": "ok", "type": "text"}])
        self.assertEqual(light, ["ok"])
        self.assertEqual(excluded, [])

    def test_fetch_light_field_ids_calls_get_tables(self):
        with patch("dingtalk_ai_table.fields.get_tables", return_value={
            "tables": [
                {"tableId": "tbl_1", "fields": self.SAMPLE_FIELDS},
            ]
        }) as mocked:
            light, excluded = fetch_light_field_ids("base12345", "tbl_1")
        mocked.assert_called_once_with("base12345", ["tbl_1"])
        self.assertIn("fld_pic", [item["fieldId"] for item in excluded])
        self.assertNotIn("fld_pic", light)

    def test_fetch_light_field_ids_raises_on_get_tables_error(self):
        # 拉不到 schema 不能静默回退到全字段查询——会误返重字段。
        with patch("dingtalk_ai_table.fields.get_tables", side_effect=RuntimeError("network down")):
            with self.assertRaisesRegex(
                RuntimeError,
                "无法获取字段结构，不能安全排除图片/附件字段",
            ):
                fetch_light_field_ids("base12345", "tbl_1")

    def test_fetch_light_field_ids_raises_on_empty_tables(self):
        with patch("dingtalk_ai_table.fields.get_tables", return_value={"tables": []}):
            with self.assertRaisesRegex(
                RuntimeError,
                "无法获取字段结构，不能安全排除图片/附件字段",
            ):
                fetch_light_field_ids("base12345", "tbl_1")

    def test_fetch_light_field_ids_raises_on_empty_fields(self):
        with patch("dingtalk_ai_table.fields.get_tables", return_value={
            "tables": [{"tableId": "tbl_1", "fields": []}],
        }):
            with self.assertRaisesRegex(
                RuntimeError,
                "无法获取字段结构，不能安全排除图片/附件字段",
            ):
                fetch_light_field_ids("base12345", "tbl_1")


if __name__ == "__main__":
    unittest.main(verbosity=2)

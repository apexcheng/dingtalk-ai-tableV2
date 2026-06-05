#!/usr/bin/env python3
"""
安全调用层测试
"""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from dingtalk_ai_table.attachments import build_attachment_cell_from_file_token, merge_attachments
from dingtalk_ai_table.fields import create_fields, get_fields, get_tables
from dingtalk_ai_table.files import safe_csv_load, safe_json_load
from dingtalk_ai_table.filters import date_eq_filter, eq_filter, iter_date_values, ne_filter
from dingtalk_ai_table.guards import (
    DEFAULT_QUERY_LIMIT,
    QUERY_MARK_FIELD_NAME,
    normalize_query_limit,
    validate_filter_tree,
    validate_get_fields_batch,
    validate_get_tables_batch,
    validate_no_cursor_with_filters_or_sort,
    validate_query_mark_field_name,
)
from dingtalk_ai_table.markers import (
    READONLY_MARKER_ERROR,
    build_task_marker,
    query_date_range_with_marker,
    query_with_marker,
)
from dingtalk_ai_table.records import create_records, delete_records, query_records, update_records


class TestQueryLimitRules(unittest.TestCase):
    def test_limit_none_defaults_to_100(self):
        self.assertEqual(normalize_query_limit(None), DEFAULT_QUERY_LIMIT)

    def test_limit_100_allowed(self):
        self.assertEqual(normalize_query_limit(100), 100)

    def test_limit_101_rejected(self):
        with self.assertRaisesRegex(ValueError, '最大只能是 100'):
            normalize_query_limit(101)


class TestCursorRules(unittest.TestCase):
    def setUp(self):
        self.base_id = 'base12345'
        self.table_id = 'table12345'
        self.sample_filter = eq_filter('fld123456', '进行中')

    def test_filters_and_cursor_rejected(self):
        with self.assertRaisesRegex(ValueError, '禁止传 cursor'):
            query_records(self.base_id, self.table_id, filters=self.sample_filter, cursor='next')

    def test_sort_and_cursor_rejected(self):
        with self.assertRaisesRegex(ValueError, '禁止传 cursor'):
            query_records(self.base_id, self.table_id, sort=[{'fieldId': 'fld123456'}], cursor='next')

    def test_filters_sort_cursor_rejected(self):
        with self.assertRaisesRegex(ValueError, '禁止传 cursor'):
            query_records(
                self.base_id,
                self.table_id,
                filters=self.sample_filter,
                sort=[{'fieldId': 'fld123456'}],
                cursor='next',
            )

    def test_cursor_allowed_without_filters_or_sort(self):
        with patch('dingtalk_ai_table.records.run_mcporter', return_value={'records': []}) as mocked_run:
            result = query_records(self.base_id, self.table_id, cursor='next')
        self.assertEqual(result, {'records': []})
        mocked_run.assert_called_once()

    def test_cursor_guard_without_filters_or_sort(self):
        validate_no_cursor_with_filters_or_sort(None, None, 'next')


class TestFilterValidation(unittest.TestCase):
    def test_filters_array_rejected(self):
        with self.assertRaisesRegex(ValueError, '不能是数组'):
            validate_filter_tree([])

    def test_filter_type_rejected(self):
        with self.assertRaisesRegex(ValueError, '禁止使用 filterType'):
            validate_filter_tree({'filterType': 'and', 'operator': 'eq', 'operands': ['fld123456', 'x']})

    def test_field_name_rejected(self):
        with self.assertRaisesRegex(ValueError, '不能使用 fieldName'):
            validate_filter_tree({'operator': 'eq', 'fieldName': '状态', 'operands': ['fld123456', 'x']})

    def test_supported_operators_allowed(self):
        validate_filter_tree(eq_filter('fld123456', '进行中'))
        validate_filter_tree(ne_filter('fld123456', '已完成'))
        validate_filter_tree(date_eq_filter('fld123456', '2026-06-05'))

    def test_unsupported_operator_rejected(self):
        for operator in ('gte', 'lte', 'is_after', 'is_before'):
            with self.subTest(operator=operator):
                with self.assertRaisesRegex(ValueError, operator):
                    validate_filter_tree({'operator': operator, 'operands': ['fld123456', 'x']})

    def test_invalid_date_eq_value_rejected(self):
        with self.assertRaisesRegex(ValueError, 'YYYY-MM-DD'):
            validate_filter_tree({'operator': 'date_eq', 'operands': ['fld123456', '2026/06/05']})

    def test_iter_date_values_only_returns_dates(self):
        self.assertEqual(iter_date_values('2026-06-05', '2026-06-07'), ['2026-06-05', '2026-06-06', '2026-06-07'])


class TestBatchLimits(unittest.TestCase):
    def setUp(self):
        self.base_id = 'base12345'
        self.table_id = 'table12345'

    def test_create_fields_over_15_rejected(self):
        fields = [{'fieldName': f'字段{index}', 'type': 'text'} for index in range(16)]
        with self.assertRaisesRegex(ValueError, '最多创建 15 个字段'):
            create_fields(self.base_id, self.table_id, fields)

    def test_create_records_over_100_rejected(self):
        records = [{'cells': {'fld123456': index}} for index in range(101)]
        with self.assertRaisesRegex(ValueError, '最多 100 条记录'):
            create_records(self.base_id, self.table_id, records)

    def test_update_records_over_100_rejected(self):
        records = [{'recordId': f'rec{index:05d}xx', 'cells': {'fld123456': index}} for index in range(101)]
        with self.assertRaisesRegex(ValueError, '最多 100 条记录'):
            update_records(self.base_id, self.table_id, records)

    def test_delete_records_over_100_rejected(self):
        record_ids = [f'record{index:05d}' for index in range(101)]
        with self.assertRaisesRegex(ValueError, '最多 100 条记录'):
            delete_records(self.base_id, self.table_id, record_ids)

    def test_get_tables_over_10_rejected(self):
        with self.assertRaisesRegex(ValueError, '最多 10 个 tableId'):
            get_tables(self.base_id, ['table12345'] * 11)

    def test_get_fields_over_10_rejected(self):
        with self.assertRaisesRegex(ValueError, '最多 10 个 fieldId'):
            get_fields(self.base_id, self.table_id, ['field12345'] * 11)

    def test_validate_get_tables_batch_over_10_rejected(self):
        with self.assertRaisesRegex(ValueError, '最多 10 个 tableId'):
            validate_get_tables_batch(['tbl123456'] * 11)

    def test_validate_get_fields_batch_over_10_rejected(self):
        with self.assertRaisesRegex(ValueError, '最多 10 个 fieldId'):
            validate_get_fields_batch(['fld123456'] * 11)


class TestQueryMarkerRules(unittest.TestCase):
    def test_query_mark_field_name_fixed(self):
        self.assertEqual(validate_query_mark_field_name(QUERY_MARK_FIELD_NAME), QUERY_MARK_FIELD_NAME)

    def test_query_mark_field_name_alias_rejected(self):
        for alias in ('处理标记', '同步标记', '回查标记', 'AI处理标记'):
            with self.subTest(alias=alias):
                with self.assertRaisesRegex(ValueError, QUERY_MARK_FIELD_NAME):
                    validate_query_mark_field_name(alias)

    def test_build_task_marker_contains_timestamp_and_task_name(self):
        marker = build_task_marker('export_orders', now=datetime(2026, 6, 5, 12, 34, 56))
        self.assertEqual(marker, 'task_20260605_123456_export_orders')

    def test_query_with_marker_readonly_rejected(self):
        with self.assertRaisesRegex(ValueError, READONLY_MARKER_ERROR):
            query_with_marker(
                base_id='base12345',
                table_id='table12345',
                process_batch=lambda batch: batch,
                filters=eq_filter('fld123456', '进行中'),
                readonly=True,
            )

    def test_query_date_range_with_marker_splits_by_day(self):
        with patch('dingtalk_ai_table.markers.query_with_marker', side_effect=['task_day_1', 'task_day_2']) as mocked_query:
            result = query_date_range_with_marker(
                base_id='base12345',
                table_id='table12345',
                date_field_id='fld123456',
                start_date='2026-06-05',
                end_date='2026-06-06',
                process_batch=lambda batch: batch,
                task_name='export_orders',
            )

        self.assertEqual(result, [
            {'date': '2026-06-05', 'taskMarker': 'task_day_1'},
            {'date': '2026-06-06', 'taskMarker': 'task_day_2'},
        ])
        self.assertEqual(mocked_query.call_count, 2)

        first_call = mocked_query.call_args_list[0].kwargs
        second_call = mocked_query.call_args_list[1].kwargs

        self.assertEqual(first_call['filters'], date_eq_filter('fld123456', '2026-06-05'))
        self.assertEqual(second_call['filters'], date_eq_filter('fld123456', '2026-06-06'))
        self.assertEqual(first_call['task_name'], 'export_orders_2026-06-05')
        self.assertEqual(second_call['task_name'], 'export_orders_2026-06-06')

    def test_query_date_range_with_marker_combines_existing_filters(self):
        base_filter = eq_filter('fld_status', '进行中')
        with patch('dingtalk_ai_table.markers.query_with_marker', return_value='task_day') as mocked_query:
            query_date_range_with_marker(
                base_id='base12345',
                table_id='table12345',
                date_field_id='fld123456',
                start_date='2026-06-05',
                end_date='2026-06-05',
                process_batch=lambda batch: batch,
                filters=base_filter,
            )

        expected_filters = {
            'operator': 'and',
            'operands': [
                base_filter,
                date_eq_filter('fld123456', '2026-06-05'),
            ],
        }
        self.assertEqual(mocked_query.call_args.kwargs['filters'], expected_filters)

    def test_query_date_range_with_marker_readonly_rejected(self):
        with self.assertRaisesRegex(ValueError, READONLY_MARKER_ERROR):
            query_date_range_with_marker(
                base_id='base12345',
                table_id='table12345',
                date_field_id='fld123456',
                start_date='2026-06-05',
                end_date='2026-06-05',
                process_batch=lambda batch: batch,
                readonly=True,
            )


class TestAttachmentRules(unittest.TestCase):
    def test_build_attachment_cell_from_file_token(self):
        self.assertEqual(build_attachment_cell_from_file_token('ft_xxx'), [{'fileToken': 'ft_xxx'}])

    def test_merge_attachments_appends_by_default(self):
        old_items = [{'fileToken': 'old'}]
        new_items = [{'fileToken': 'new'}]
        self.assertEqual(merge_attachments(old_items, new_items), [{'fileToken': 'old'}, {'fileToken': 'new'}])

    def test_merge_attachments_overwrite(self):
        old_items = [{'fileToken': 'old'}]
        new_items = [{'fileToken': 'new'}]
        self.assertEqual(merge_attachments(old_items, new_items, overwrite=True), [{'fileToken': 'new'}])


class TestFileSizeRules(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_json_file_size_limit(self):
        json_file = self.test_dir / 'big.json'
        json_file.write_text(json.dumps([{'fieldName': 'x', 'type': 'text'}]), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '文件过大'):
            safe_json_load(json_file, max_size=1)

    def test_csv_file_size_limit(self):
        csv_file = self.test_dir / 'big.csv'
        csv_file.write_text('a,b\n1,2\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '文件过大'):
            safe_csv_load(csv_file, max_size=1)


if __name__ == '__main__':
    unittest.main(verbosity=2)

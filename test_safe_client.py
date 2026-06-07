#!/usr/bin/env python3
"""Core safety boundary tests."""

import json
import unittest
from datetime import datetime
from unittest.mock import patch

from dingtalk_ai_table import (
    process_date_range_with_marker,
    process_records_with_marker,
    resolve_field_id,
    resolve_option_id,
    safe_create_records,
    safe_delete_records,
    safe_prepare_attachment_upload,
    safe_query_records,
    safe_update_records,
)
from dingtalk_ai_table.filters import and_filter, date_eq_filter, eq_filter, iter_date_values, ne_filter, or_filter
from dingtalk_ai_table.guards import (
    QUERY_MARK_FIELD_NAME,
    normalize_query_limit,
    validate_filter_tree,
    validate_query_mark_field_name,
)
from dingtalk_ai_table.markers import READONLY_MARKER_ERROR, _extract_record_id, build_task_marker, query_date_range_with_marker, query_with_marker
from dingtalk_ai_table.records import build_create_records_payload, build_update_records_payload, normalize_query_filters, query_records


class TestPublicEntryPoints(unittest.TestCase):
    def test_public_entry_points_are_callable(self):
        self.assertTrue(callable(resolve_field_id))
        self.assertTrue(callable(resolve_option_id))
        self.assertTrue(callable(safe_query_records))
        self.assertTrue(callable(safe_create_records))
        self.assertTrue(callable(safe_update_records))
        self.assertTrue(callable(safe_delete_records))
        self.assertTrue(callable(process_records_with_marker))
        self.assertTrue(callable(process_date_range_with_marker))
        self.assertTrue(callable(safe_prepare_attachment_upload))


class TestQueryLimits(unittest.TestCase):
    def test_limit_none_defaults_to_100(self):
        self.assertEqual(normalize_query_limit(None), 100)

    def test_limit_100_allowed(self):
        self.assertEqual(normalize_query_limit(100), 100)

    def test_limit_101_rejected(self):
        with self.assertRaisesRegex(ValueError, 'limit'):
            normalize_query_limit(101)

    def test_date_range_max_366_days(self):
        with self.assertRaisesRegex(ValueError, 'max 366 days'):
            iter_date_values('2026-01-01', '2027-01-02')


class TestFilters(unittest.TestCase):
    def test_filters_array_rejected(self):
        with self.assertRaisesRegex(ValueError, 'filters'):
            validate_filter_tree([])

    def test_filter_type_rejected(self):
        with self.assertRaisesRegex(ValueError, 'filterType'):
            validate_filter_tree({'filterType': 'and', 'operator': 'eq', 'operands': ['fld123456', 'x']})

    def test_field_name_rejected(self):
        with self.assertRaisesRegex(ValueError, 'fieldName'):
            validate_filter_tree({'operator': 'eq', 'fieldName': 'status', 'operands': ['fld123456', 'x']})

    def test_supported_operators_allowed(self):
        validate_filter_tree(eq_filter('fld123456', 'in progress'))
        validate_filter_tree(ne_filter('fld123456', 'done'))
        validate_filter_tree(date_eq_filter('fld123456', '2026-06-05'))

    def test_unsupported_operators_rejected(self):
        for operator in ('gte', 'lte', 'is_after', 'is_before'):
            with self.subTest(operator=operator):
                with self.assertRaisesRegex(ValueError, operator):
                    validate_filter_tree({'operator': operator, 'operands': ['fld123456', 'x']})

    def test_invalid_date_eq_value_rejected(self):
        with self.assertRaisesRegex(ValueError, 'YYYY-MM-DD'):
            validate_filter_tree({'operator': 'date_eq', 'operands': ['fld123456', '2026/06/05']})

    def test_iter_date_values_only_returns_dates(self):
        self.assertEqual(iter_date_values('2026-06-05', '2026-06-07'), ['2026-06-05', '2026-06-06', '2026-06-07'])


class TestQueryRecords(unittest.TestCase):
    def test_filters_and_cursor_allowed(self):
        # filters + cursor 是允许的（v1.3+），只有 sort + cursor 被禁。
        with patch('dingtalk_ai_table.records.run_mcporter', return_value={'records': []}) as mocked_run:
            query_records(
                'base12345',
                'table12345',
                filters=eq_filter('fld123456', 'in progress'),
                cursor='next',
            )
        mocked_run.assert_called_once()
        payload = json.loads(mocked_run.call_args.args[0][2])
        self.assertEqual(payload['cursor'], 'next')
        self.assertIn('filters', payload)

    def test_sort_and_cursor_rejected(self):
        with self.assertRaisesRegex(ValueError, 'sort.*cursor|cursor.*sort'):
            query_records('base12345', 'table12345', sort=[{'fieldId': 'fld123456'}], cursor='next')

    def test_cursor_allowed_without_filters_or_sort(self):
        with patch('dingtalk_ai_table.records.run_mcporter', return_value={'records': []}) as mocked_run:
            query_records('base12345', 'table12345', cursor='next')
        mocked_run.assert_called_once()
        payload = json.loads(mocked_run.call_args.args[0][2])
        self.assertEqual(payload['limit'], 100)

    def test_payload_structure(self):
        with patch('dingtalk_ai_table.records.run_mcporter', return_value={'records': []}) as mocked_run:
            query_records(
                'base12345',
                'table12345',
                filters=eq_filter('fld123456', 'in progress'),
                field_ids=['fld123456'],
                limit=100,
            )
        payload = json.loads(mocked_run.call_args.args[0][2])
        self.assertEqual(payload['baseId'], 'base12345')
        self.assertEqual(payload['tableId'], 'table12345')
        self.assertEqual(payload['limit'], 100)
        self.assertIn('filters', payload)
        self.assertEqual(payload['fieldIds'], ['fld123456'])


class TestQueryFilterNormalization(unittest.TestCase):
    """The MCP server requires compound top-level filters and silently
    ignores flat leaves. query_records() must auto-wrap leaves so the
    public API still accepts the flat shape produced by build-filter.
    """

    def test_none_passthrough(self):
        self.assertIsNone(normalize_query_filters(None))

    def test_date_eq_leaf_is_wrapped_in_and(self):
        leaf = date_eq_filter('fld_date', '2026-06-03')
        normalized = normalize_query_filters(leaf)
        self.assertEqual(normalized, {
            'operator': 'and',
            'operands': [{'operator': 'date_eq', 'operands': ['fld_date', '2026-06-03']}],
        })

    def test_eq_leaf_is_wrapped_in_and(self):
        leaf = eq_filter('fld123456', 'in progress')
        normalized = normalize_query_filters(leaf)
        self.assertEqual(normalized, {
            'operator': 'and',
            'operands': [{'operator': 'eq', 'operands': ['fld123456', 'in progress']}],
        })

    def test_ne_leaf_is_wrapped_in_and(self):
        leaf = ne_filter('fld123456', 'in progress')
        normalized = normalize_query_filters(leaf)
        self.assertEqual(normalized, {
            'operator': 'and',
            'operands': [{'operator': 'ne', 'operands': ['fld123456', 'in progress']}],
        })

    def test_existing_and_is_not_re_wrapped(self):
        compound = and_filter(eq_filter('fld_a', 'x'), date_eq_filter('fld_b', '2026-06-03'))
        normalized = normalize_query_filters(compound)
        self.assertEqual(normalized, compound)

    def test_existing_or_is_not_re_wrapped(self):
        compound = or_filter(eq_filter('fld_a', 'x'), eq_filter('fld_a', 'y'))
        normalized = normalize_query_filters(compound)
        self.assertEqual(normalized, compound)

    def test_query_records_sends_wrapped_payload(self):
        with patch('dingtalk_ai_table.records.run_mcporter', return_value={'records': []}) as mocked_run:
            query_records(
                'base12345',
                'table12345',
                filters=date_eq_filter('fld_date', '2026-06-03'),
                limit=10,
            )
        payload = json.loads(mocked_run.call_args.args[0][2])
        self.assertEqual(payload['filters'], {
            'operator': 'and',
            'operands': [{'operator': 'date_eq', 'operands': ['fld_date', '2026-06-03']}],
        })

    def test_query_records_preserves_existing_and(self):
        compound = and_filter(
            eq_filter('fld_a', 'x'),
            date_eq_filter('fld_b', '2026-06-03'),
        )
        with patch('dingtalk_ai_table.records.run_mcporter', return_value={'records': []}) as mocked_run:
            query_records(
                'base12345',
                'table12345',
                filters=compound,
                limit=10,
            )
        payload = json.loads(mocked_run.call_args.args[0][2])
        self.assertEqual(payload['filters'], compound)

    def test_query_records_does_not_use_filter_key(self):
        with patch('dingtalk_ai_table.records.run_mcporter', return_value={'records': []}) as mocked_run:
            query_records(
                'base12345',
                'table12345',
                filters=eq_filter('fld_a', 'x'),
                limit=10,
            )
        payload = json.loads(mocked_run.call_args.args[0][2])
        # MCP 参数名仍为 filters，绝不改成 filter。
        self.assertIn('filters', payload)
        self.assertNotIn('filter', payload)

    def test_safe_query_records_also_wraps_leaf(self):
        # 安全入口 (skill_api.safe_query_records) 也走 query_records，
        # 所以需要同样生效。
        with patch('dingtalk_ai_table.records.run_mcporter', return_value={'records': []}) as mocked_run:
            safe_query_records(
                'base12345',
                'table12345',
                filters=date_eq_filter('fld_date', '2026-06-03'),
                limit=10,
            )
        payload = json.loads(mocked_run.call_args.args[0][2])
        self.assertEqual(payload['filters'], {
            'operator': 'and',
            'operands': [{'operator': 'date_eq', 'operands': ['fld_date', '2026-06-03']}],
        })


class TestRecordPayloads(unittest.TestCase):
    def test_create_payload_structure(self):
        payload = build_create_records_payload('base12345', 'table12345', [{'cells': {'fld_name': 'Alice'}}])
        self.assertEqual(payload['baseId'], 'base12345')
        self.assertEqual(payload['tableId'], 'table12345')
        self.assertEqual(payload['records'][0]['cells']['fld_name'], 'Alice')

    def test_update_payload_structure(self):
        payload = build_update_records_payload('base12345', 'table12345', [{'recordId': 'rec12345', 'cells': {'fld_name': 'Bob'}}])
        self.assertEqual(payload['records'][0]['recordId'], 'rec12345')
        self.assertEqual(payload['records'][0]['cells']['fld_name'], 'Bob')


class TestQueryMarker(unittest.TestCase):
    def test_query_mark_field_name_fixed(self):
        self.assertEqual(validate_query_mark_field_name(QUERY_MARK_FIELD_NAME), QUERY_MARK_FIELD_NAME)

    def test_query_mark_field_name_alias_rejected(self):
        with self.assertRaisesRegex(ValueError, QUERY_MARK_FIELD_NAME):
            validate_query_mark_field_name('processing marker')

    def test_build_task_marker_contains_timestamp(self):
        marker = build_task_marker('export_orders', now=datetime(2026, 6, 5, 12, 34, 56))
        self.assertEqual(marker, 'task_20260605_123456_export_orders')

    def test_query_with_marker_readonly_rejected(self):
        with self.assertRaisesRegex(ValueError, READONLY_MARKER_ERROR):
            query_with_marker(
                base_id='base12345',
                table_id='table12345',
                process_batch=lambda batch: batch,
                filters=eq_filter('fld123456', 'in progress'),
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
        self.assertEqual(mocked_query.call_args_list[0].kwargs['filters'], date_eq_filter('fld123456', '2026-06-05'))
        self.assertEqual(mocked_query.call_args_list[1].kwargs['filters'], date_eq_filter('fld123456', '2026-06-06'))

    def test_extract_record_id_accepts_recordId(self):
        self.assertEqual(_extract_record_id({'recordId': 'rec12345'}), 'rec12345')

    def test_extract_record_id_accepts_id(self):
        # clean_payload 依赖该函数同时接受 id / recordId。
        self.assertEqual(_extract_record_id({'id': 'rec12345'}), 'rec12345')

    def test_extract_record_id_raises_when_missing(self):
        with self.assertRaisesRegex(ValueError, 'recordId'):
            _extract_record_id({})

    def test_query_with_marker_fallback_write_failure_raises(self):
        # 验证：marker 写入查询标记 fallback 单条重试也失败时，不能 except: pass，
        # 必须报错中断，避免漏写标记后 cursor 推进重复处理。
        from dingtalk_ai_table.client import TruncatedResponseError

        batch_record = {'recordId': 'rec12345', 'cells': {}}
        truncated = TruncatedResponseError('truncated', suggested_limit=None)

        with patch('dingtalk_ai_table.markers.ensure_query_mark_field', return_value='fld_mark_xx'), \
             patch('dingtalk_ai_table.markers.query_records', side_effect=[
                 # 第一次调用：拉取一批数据。
                 {'records': [batch_record]},
                 # 第二次调用：verify-by-record_ids 截断。
                 truncated,
                 # 第三次调用：fallback 单条重试，仍然报错。
                 RuntimeError('single record query failed'),
             ]), \
             patch('dingtalk_ai_table.markers.update_records') as mocked_update:
            with self.assertRaises(RuntimeError) as ctx:
                query_with_marker(
                    base_id='base12345',
                    table_id='table12345',
                    process_batch=lambda batch: batch,
                    filters=eq_filter('fld123456', 'in progress'),
                    task_name='export_orders',
                )

        message = str(ctx.exception)
        self.assertIn('rec12345', message)
        self.assertIn('漏数据', message)
        # 只可重试一次 fallback，不能再重试就崩。
        self.assertEqual(mocked_update.call_count, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)

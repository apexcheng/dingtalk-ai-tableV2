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
from dingtalk_ai_table.filters import date_eq_filter, eq_filter, iter_date_values, ne_filter
from dingtalk_ai_table.guards import (
    QUERY_MARK_FIELD_NAME,
    normalize_query_limit,
    validate_filter_tree,
    validate_query_mark_field_name,
)
from dingtalk_ai_table.markers import READONLY_MARKER_ERROR, build_task_marker, query_date_range_with_marker, query_with_marker
from dingtalk_ai_table.records import build_create_records_payload, build_update_records_payload, query_records


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
    def test_filters_and_cursor_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cursor'):
            query_records('base12345', 'table12345', filters=eq_filter('fld123456', 'in progress'), cursor='next')

    def test_sort_and_cursor_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cursor'):
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


if __name__ == '__main__':
    unittest.main(verbosity=2)

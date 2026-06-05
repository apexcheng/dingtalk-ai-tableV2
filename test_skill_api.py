#!/usr/bin/env python3
"""
skill_api 门面层测试
"""

import unittest
from unittest.mock import patch

from dingtalk_ai_table import (
    SKILL_API_FUNCTIONS,
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


class TestSkillApiExports(unittest.TestCase):
    def test_skill_api_function_list(self):
        self.assertEqual(SKILL_API_FUNCTIONS, (
            'resolve_field_id',
            'resolve_option_id',
            'safe_query_records',
            'safe_create_records',
            'safe_update_records',
            'safe_delete_records',
            'process_records_with_marker',
            'process_date_range_with_marker',
            'safe_prepare_attachment_upload',
        ))


class TestSkillApiForwarding(unittest.TestCase):
    def test_resolve_field_id_forwards(self):
        with patch('dingtalk_ai_table.skill_api.get_field_id_by_name', return_value='fld_xxx') as mocked:
            self.assertEqual(resolve_field_id('base_xxx', 'tbl_xxx', '状态'), 'fld_xxx')
        mocked.assert_called_once_with('base_xxx', 'tbl_xxx', '状态')

    def test_resolve_option_id_forwards(self):
        with patch('dingtalk_ai_table.skill_api.get_option_id_by_name', return_value='opt_xxx') as mocked:
            self.assertEqual(resolve_option_id('base_xxx', 'tbl_xxx', '状态', '进行中'), 'opt_xxx')
        mocked.assert_called_once_with('base_xxx', 'tbl_xxx', '状态', '进行中')

    def test_safe_query_records_forwards(self):
        with patch('dingtalk_ai_table.skill_api.query_records', return_value={'records': []}) as mocked:
            result = safe_query_records('base_xxx', 'tbl_xxx', limit=100)
        self.assertEqual(result, {'records': []})
        mocked.assert_called_once()

    def test_safe_create_records_forwards(self):
        records = [{'cells': {'fld_name': '张三'}}]
        with patch('dingtalk_ai_table.skill_api.create_records', return_value={'ok': True}) as mocked:
            result = safe_create_records('base_xxx', 'tbl_xxx', records)
        self.assertEqual(result, {'ok': True})
        mocked.assert_called_once_with('base_xxx', 'tbl_xxx', records)

    def test_safe_update_records_forwards(self):
        records = [{'recordId': 'rec_xxx', 'cells': {'fld_name': '李四'}}]
        with patch('dingtalk_ai_table.skill_api.update_records', return_value={'ok': True}) as mocked:
            result = safe_update_records('base_xxx', 'tbl_xxx', records)
        self.assertEqual(result, {'ok': True})
        mocked.assert_called_once_with('base_xxx', 'tbl_xxx', records)

    def test_safe_delete_records_forwards(self):
        record_ids = ['rec_xxx']
        with patch('dingtalk_ai_table.skill_api.delete_records', return_value={'ok': True}) as mocked:
            result = safe_delete_records('base_xxx', 'tbl_xxx', record_ids)
        self.assertEqual(result, {'ok': True})
        mocked.assert_called_once_with('base_xxx', 'tbl_xxx', record_ids)

    def test_process_records_with_marker_forwards(self):
        process_batch = lambda batch: batch
        with patch('dingtalk_ai_table.skill_api.query_with_marker', return_value='task_xxx') as mocked:
            result = process_records_with_marker('base_xxx', 'tbl_xxx', process_batch, task_name='export_orders')
        self.assertEqual(result, 'task_xxx')
        mocked.assert_called_once()

    def test_process_date_range_with_marker_forwards(self):
        process_batch = lambda batch: batch
        with patch('dingtalk_ai_table.skill_api.query_date_range_with_marker', return_value=[{'date': '2026-06-05', 'taskMarker': 'task_xxx'}]) as mocked:
            result = process_date_range_with_marker(
                'base_xxx',
                'tbl_xxx',
                'fld_date',
                '2026-06-05',
                '2026-06-05',
                process_batch,
            )
        self.assertEqual(result, [{'date': '2026-06-05', 'taskMarker': 'task_xxx'}])
        mocked.assert_called_once()

    def test_safe_prepare_attachment_upload_forwards(self):
        with patch('dingtalk_ai_table.skill_api.prepare_attachment_upload', return_value={'uploadUrl': 'https://example.com'}) as mocked:
            result = safe_prepare_attachment_upload('base_xxx', 'report.pdf', 1024, 'application/pdf')
        self.assertEqual(result, {'uploadUrl': 'https://example.com'})
        mocked.assert_called_once_with('base_xxx', 'report.pdf', 1024, 'application/pdf')


if __name__ == '__main__':
    unittest.main(verbosity=2)

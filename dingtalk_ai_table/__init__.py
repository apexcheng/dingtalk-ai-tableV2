"""
钉钉 AI 表格安全调用层。
"""

from .skill_api import (
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

__all__ = [
    'resolve_field_id',
    'resolve_option_id',
    'safe_query_records',
    'safe_create_records',
    'safe_update_records',
    'safe_delete_records',
    'process_records_with_marker',
    'process_date_range_with_marker',
    'safe_prepare_attachment_upload',
]

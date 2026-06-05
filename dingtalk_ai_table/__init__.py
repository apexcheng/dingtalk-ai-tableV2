"""
钉钉 AI 表格安全调用层。
"""

from .skill_api import (
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

from .attachments import (
    build_attachment_cell_from_file_token,
    merge_attachments,
    prepare_attachment_upload,
)
from .client import (
    build_mcporter_call,
    get_mcporter_version,
    parse_mcporter_version,
    run_mcporter,
)
from .fields import (
    build_create_fields_payload,
    ensure_query_mark_field,
    get_field_id_by_name,
    get_fields,
    get_option_id_by_name,
    normalize_field_config,
    validate_field_config,
)
from .files import (
    resolve_safe_path,
    safe_csv_load,
    safe_json_load,
    validate_file_extension,
)
from .filters import and_filter, date_eq_filter, eq_filter, iter_date_values, ne_filter, or_filter
from .guards import (
    DEFAULT_QUERY_LIMIT,
    MAX_FIELDS_PER_CREATE,
    MAX_FIELDS_PER_GET,
    MAX_QUERY_LIMIT,
    MAX_RECORDS_PER_BATCH,
    MAX_TABLES_PER_GET,
    QUERY_MARK_FIELD_NAME,
    RESOURCE_ID_PATTERN,
    SUPPORTED_FILTER_OPERATORS,
    normalize_query_limit,
    validate_filter_tree,
    validate_get_fields_batch,
    validate_get_tables_batch,
    validate_no_cursor_with_filters_or_sort,
    validate_query_mark_field_name,
    validate_record_batch,
    validate_resource_id,
)
from .markers import (
    READONLY_MARKER_ERROR,
    build_task_marker,
    query_date_range_with_marker,
    query_with_marker,
)
from .records import (
    build_create_records_payload,
    create_records,
    delete_records,
    extract_records,
    normalize_record,
    query_records,
    sanitize_record_value,
    update_records,
    validate_record,
)

__all__ = [
    'SKILL_API_FUNCTIONS',
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

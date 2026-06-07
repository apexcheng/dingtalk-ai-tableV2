import json
from typing import Any, Dict, List, Optional, Tuple, Union

from .client import run_mcporter
from .guards import (
    COMPOUND_FILTER_OPERATORS,
    SUPPORTED_FILTER_OPERATORS,
    ensure_resource_id,
    normalize_query_limit,
    validate_filter_tree,
    validate_no_cursor_with_filters_or_sort,
    validate_record_batch,
)

JsonValue = Optional[Union[str, int, float, bool, list, dict]]


def sanitize_record_value(value: Any) -> JsonValue:
    if value is None:
        return None
    if isinstance(value, (bool, int, float, list, dict)):
        return value
    if not isinstance(value, str):
        return value
    value = value.strip()
    if not value:
        return None
    return value


def validate_update_record_value(value: Any) -> None:
    if value is None:
        raise ValueError("update-records 当前不支持清空字段，请不要传 null 或空字符串")
    if isinstance(value, str) and not value.strip():
        raise ValueError("update-records 当前不支持清空字段，请不要传 null 或空字符串")


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if 'cells' in record and isinstance(record['cells'], dict):
        cells = record['cells']
    else:
        cells = record

    normalized = {}
    for key, value in cells.items():
        field_id = ensure_resource_id(key, 'fieldId')
        sanitized = sanitize_record_value(value)
        if sanitized is not None:
            normalized[field_id] = sanitized
    return {'cells': normalized}


def validate_record(record: Dict[str, Any], headers: List[str]) -> Tuple[bool, str]:
    del headers
    if not isinstance(record, dict):
        return False, '记录必须是对象'

    normalized = normalize_record(record)
    cells = normalized.get('cells', {})
    if not cells or not isinstance(cells, dict):
        return False, '记录必须包含非空 cells 对象'
    return True, ''


def build_create_records_payload(base_id: str, table_id: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        'baseId': base_id,
        'tableId': table_id,
        'records': [normalize_record(record) for record in records],
    }


def build_update_records_payload(base_id: str, table_id: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload_records = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('更新记录必须是对象')
        record_id = ensure_resource_id(record.get('recordId'), 'recordId')
        if 'cells' in record and isinstance(record['cells'], dict):
            cells_source = record['cells']
        else:
            cells_source = {key: value for key, value in record.items() if key != 'recordId'}
        for value in cells_source.values():
            validate_update_record_value(value)
        cells = normalize_record({'cells': cells_source})['cells']
        if not cells:
            raise ValueError('更新记录必须包含非空 cells 对象')
        payload_records.append({'recordId': record_id, 'cells': cells})
    return {
        'baseId': base_id,
        'tableId': table_id,
        'records': payload_records,
    }


def extract_records(result: Any) -> List[Dict[str, Any]]:
    if isinstance(result, dict):
        if isinstance(result.get('records'), list):
            return result['records']
        data = result.get('data')
        if isinstance(data, dict):
            if isinstance(data.get('records'), list):
                return data['records']
            if isinstance(data.get('items'), list):
                return data['items']
        if isinstance(result.get('items'), list):
            return result['items']
    if isinstance(result, list):
        return result
    return []


def normalize_query_filters(filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Wrap a flat leaf filter in a compound ``and`` for the MCP server.

    The current ``query_records`` MCP endpoint requires the top-level
    ``filters.operator`` to be a compound (``and`` / ``or``) and silently
    ignores flat leaves like ``{operator: date_eq, operands: [...]}``.
    This helper keeps the public filter shape unchanged for callers
    (``build-filter`` / CLI / input files) and only adapts the value
    right before it is sent to MCP.
    """
    if filters is None:
        return None

    operator = filters.get('operator') if isinstance(filters, dict) else None
    if operator in COMPOUND_FILTER_OPERATORS:
        return filters
    if operator in SUPPORTED_FILTER_OPERATORS:
        return {'operator': 'and', 'operands': [filters]}

    # Leave invalid shapes to validate_filter_tree so the real error surfaces.
    return filters


def query_records(
    base_id: str,
    table_id: str,
    record_ids: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    keyword: Optional[str] = None,
    sort: Optional[Any] = None,
    field_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    table_id = ensure_resource_id(table_id, 'tableId')
    query_limit = normalize_query_limit(limit)
    validate_no_cursor_with_filters_or_sort(filters, sort, cursor)
    validate_filter_tree(filters)
    payload_filters = normalize_query_filters(filters)

    payload = {
        'baseId': base_id,
        'tableId': table_id,
        'limit': query_limit,
    }

    if record_ids is not None:
        validate_record_batch(record_ids)
        payload['recordIds'] = [ensure_resource_id(record_id, 'recordId') for record_id in record_ids]
    if payload_filters is not None:
        payload['filters'] = payload_filters
    if keyword is not None:
        payload['keyword'] = keyword
    if sort is not None:
        payload['sort'] = sort
    if field_ids is not None:
        payload['fieldIds'] = [ensure_resource_id(field_id, 'fieldId') for field_id in field_ids]
    if cursor is not None:
        payload['cursor'] = cursor

    return run_mcporter(['query_records', '--args', json.dumps(payload, ensure_ascii=False)])


def create_records(base_id: str, table_id: str, records: List[Dict[str, Any]]) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    table_id = ensure_resource_id(table_id, 'tableId')
    validate_record_batch(records)
    payload = build_create_records_payload(base_id, table_id, records)
    return run_mcporter(['create_records', '--args', json.dumps(payload, ensure_ascii=False)], timeout=120)


def update_records(base_id: str, table_id: str, records: List[Dict[str, Any]]) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    table_id = ensure_resource_id(table_id, 'tableId')
    validate_record_batch(records)
    payload = build_update_records_payload(base_id, table_id, records)
    return run_mcporter(['update_records', '--args', json.dumps(payload, ensure_ascii=False)], timeout=120)


def delete_records(base_id: str, table_id: str, record_ids: List[str]) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    table_id = ensure_resource_id(table_id, 'tableId')
    validate_record_batch(record_ids)
    payload = {
        'baseId': base_id,
        'tableId': table_id,
        'recordIds': [ensure_resource_id(record_id, 'recordId') for record_id in record_ids],
    }
    return run_mcporter(['delete_records', '--args', json.dumps(payload, ensure_ascii=False)], timeout=120)

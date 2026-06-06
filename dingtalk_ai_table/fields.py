import json
from typing import Any, Dict, List, Optional, Tuple

from .client import run_mcporter
from .guards import (
    QUERY_MARK_FIELD_NAME,
    ensure_resource_id,
    validate_field_batch,
    validate_get_fields_batch,
    validate_get_tables_batch,
    validate_query_mark_field_name,
    validate_resource_id,
)

ALLOWED_FIELD_TYPES = {
    'text', 'number', 'singleSelect', 'multipleSelect', 'date', 'currency',
    'user', 'department', 'group', 'progress', 'rating', 'checkbox',
    'attachment', 'url', 'richText', 'telephone', 'email', 'idCard',
    'barcode', 'geolocation', 'primaryDoc', 'formula', 'unidirectionalLink',
    'bidirectionalLink', 'creator', 'lastModifier', 'createdTime', 'lastModifiedTime'
}
FIELD_TYPE_ALIASES = {
    'phone': 'telephone',
}


def normalize_field_config(field: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(field)
    if 'fieldName' not in normalized and 'name' in normalized:
        normalized['fieldName'] = normalized.pop('name')
    normalized['type'] = FIELD_TYPE_ALIASES.get(normalized.get('type', 'text'), normalized.get('type', 'text'))
    return normalized


def validate_field_config(field: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(field, dict):
        return False, '字段配置必须是对象'

    field = normalize_field_config(field)
    if 'fieldName' not in field:
        return False, '缺少必需字段：fieldName'
    if not isinstance(field['fieldName'], str) or not field['fieldName'].strip():
        return False, 'fieldName 必须是非空字符串'

    field_type = field.get('type', 'text')
    if field_type not in ALLOWED_FIELD_TYPES:
        return False, f'不支持的字段类型：{field_type}'

    config = field.get('config')
    if config is not None and not isinstance(config, dict):
        return False, 'config 必须是对象'

    if field_type in {'singleSelect', 'multipleSelect'}:
        options = (config or {}).get('options')
        if not options or not isinstance(options, list):
            return False, 'singleSelect / multipleSelect 必须提供 config.options 数组'

    if field_type in {'unidirectionalLink', 'bidirectionalLink'}:
        linked_sheet_id = (config or {}).get('linkedSheetId')
        if not linked_sheet_id or not validate_resource_id(linked_sheet_id):
            return False, '关联字段必须提供合法的 config.linkedSheetId'

    return True, ''


def build_create_fields_payload(base_id: str, table_id: str, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload_fields = []
    for field in fields:
        normalized = normalize_field_config(field)
        item = {
            'fieldName': normalized['fieldName'].strip(),
            'type': normalized.get('type', 'text')
        }
        if 'config' in normalized and normalized['config'] is not None:
            item['config'] = normalized['config']
        payload_fields.append(item)
    return {
        'baseId': base_id,
        'tableId': table_id,
        'fields': payload_fields,
    }


def _extract_tables(result: Any) -> List[Dict[str, Any]]:
    if isinstance(result, dict):
        if isinstance(result.get('tables'), list):
            return result['tables']
        base = result.get('base')
        if isinstance(base, dict) and isinstance(base.get('tables'), list):
            return base['tables']
        data = result.get('data')
        if isinstance(data, dict):
            if isinstance(data.get('tables'), list):
                return data['tables']
            base = data.get('base')
            if isinstance(base, dict) and isinstance(base.get('tables'), list):
                return base['tables']
    if isinstance(result, list):
        return result
    return []


def _extract_fields(result: Any) -> List[Dict[str, Any]]:
    if isinstance(result, dict):
        if isinstance(result.get('fields'), list):
            return result['fields']
        data = result.get('data')
        if isinstance(data, dict) and isinstance(data.get('fields'), list):
            return data['fields']
    if isinstance(result, list):
        return result
    return []


def get_tables(base_id: str, table_ids: List[str]) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    validate_get_tables_batch(table_ids)
    normalized_table_ids = [ensure_resource_id(table_id, 'tableId') for table_id in table_ids]
    payload = {
        'baseId': base_id,
        'tableIds': normalized_table_ids,
    }
    return run_mcporter(['get_tables', '--args', json.dumps(payload, ensure_ascii=False)])


def get_base(base_id: str) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    payload = {
        'baseId': base_id,
    }
    return run_mcporter(['get_base', '--args', json.dumps(payload, ensure_ascii=False)])


def list_bases(limit: Optional[int] = None, cursor: Optional[str] = None) -> Any:
    payload: Dict[str, Any] = {}
    if limit is not None:
        payload['limit'] = limit
    if cursor is not None:
        payload['cursor'] = cursor
    if payload:
        return run_mcporter(['list_bases', '--args', json.dumps(payload, ensure_ascii=False)])
    return run_mcporter(['list_bases'])


def search_bases(query: str, limit: Optional[int] = None, cursor: Optional[str] = None) -> Any:
    if not isinstance(query, str) or not query.strip():
        raise ValueError('query 不能为空')

    payload: Dict[str, Any] = {'query': query.strip()}
    if limit is not None:
        payload['limit'] = limit
    if cursor is not None:
        payload['cursor'] = cursor
    return run_mcporter(['search_bases', '--args', json.dumps(payload, ensure_ascii=False)])


def get_fields(base_id: str, table_id: str, field_ids: List[str]) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    table_id = ensure_resource_id(table_id, 'tableId')
    validate_get_fields_batch(field_ids)
    normalized_field_ids = [ensure_resource_id(field_id, 'fieldId') for field_id in field_ids]
    payload = {
        'baseId': base_id,
        'tableId': table_id,
        'fieldIds': normalized_field_ids,
    }
    return run_mcporter(['get_fields', '--args', json.dumps(payload, ensure_ascii=False)])


def create_fields(base_id: str, table_id: str, fields: List[Dict[str, Any]]) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    table_id = ensure_resource_id(table_id, 'tableId')
    validate_field_batch(fields)

    for index, field in enumerate(fields):
        valid, error = validate_field_config(field)
        if not valid:
            raise ValueError(f'字段 #{index + 1} 配置无效：{error}')

    payload = build_create_fields_payload(base_id, table_id, fields)
    return run_mcporter(['create_fields', '--args', json.dumps(payload, ensure_ascii=False)])


def get_field_id_by_name(base_id: str, table_id: str, field_name: str) -> str:
    if not isinstance(field_name, str) or not field_name.strip():
        raise ValueError('field_name 不能为空')

    tables_result = get_tables(base_id, [table_id])
    tables = _extract_tables(tables_result)
    if not tables:
        raise ValueError('未找到表结构信息')

    for field in tables[0].get('fields', []):
        if field.get('fieldName') == field_name or field.get('name') == field_name:
            field_id = field.get('fieldId') or field.get('id')
            if validate_resource_id(field_id):
                return field_id
    raise ValueError(f'未找到字段：{field_name}')


def get_table_by_name(base_id: str, table_name: str) -> Dict[str, str]:
    if not isinstance(table_name, str) or not table_name.strip():
        raise ValueError('table_name 不能为空')

    target_name = table_name.strip()
    base_result = get_base(base_id)
    tables = _extract_tables(base_result)
    if not tables:
        raise ValueError(f'get_base 未返回表列表，无法解析表名：{target_name}')

    matched_tables = []
    for table in tables:
        current_name = table.get('tableName')
        if not isinstance(current_name, str):
            current_name = table.get('name')
        if not isinstance(current_name, str):
            continue
        current_name = current_name.strip()
        if current_name != target_name:
            continue
        table_id = table.get('tableId') or table.get('id')
        if validate_resource_id(table_id):
            matched_tables.append({
                'tableId': table_id,
                'tableName': current_name,
            })

    if not matched_tables:
        raise ValueError(f'未找到表：{target_name}')
    if len(matched_tables) > 1:
        raise ValueError('找到多个同名表，请人工确认')
    return matched_tables[0]


def get_option_id_by_name(base_id: str, table_id: str, field_name: str, option_name: str) -> str:
    field_id = get_field_id_by_name(base_id, table_id, field_name)
    field_result = get_fields(base_id, table_id, [field_id])
    fields = _extract_fields(field_result)
    if not fields:
        raise ValueError(f'未找到字段配置：{field_name}')

    options = ((fields[0].get('config') or {}).get('options') or [])
    for option in options:
        if option.get('name') == option_name:
            option_id = option.get('id')
            if option_id:
                return option_id
    raise ValueError(f'未找到选项：{option_name}')


def ensure_query_mark_field(base_id: str, table_id: str) -> str:
    validate_query_mark_field_name(QUERY_MARK_FIELD_NAME)
    try:
        return get_field_id_by_name(base_id, table_id, QUERY_MARK_FIELD_NAME)
    except ValueError:
        create_fields(base_id, table_id, [{'fieldName': QUERY_MARK_FIELD_NAME, 'type': 'text'}])
        return get_field_id_by_name(base_id, table_id, QUERY_MARK_FIELD_NAME)

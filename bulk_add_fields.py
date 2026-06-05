#!/usr/bin/env python3
"""
批量添加字段到钉钉 AI 表格数据表（新 MCP schema）

用法:
    python3 bulk_add_fields.py <baseId> <tableId> fields.json

fields.json 格式:
    [
        {"fieldName": "字段 1", "type": "text"},
        {"fieldName": "字段 2", "type": "number", "config": {"formatter": "INT"}},
        {"fieldName": "字段 3", "type": "singleSelect", "config": {"options": [{"name": "高"}]}}
    ]

兼容写法：
- name 会自动映射为 fieldName
- phone 会自动映射为 telephone
"""

import json
import sys
from typing import Any, Dict, List

from dingtalk_ai_table.client import build_mcporter_call, get_mcporter_version, parse_mcporter_version, run_mcporter
from dingtalk_ai_table.fields import (
    ALLOWED_FIELD_TYPES,
    FIELD_TYPE_ALIASES,
    build_create_fields_payload,
    create_fields,
    normalize_field_config,
    validate_field_config,
)
from dingtalk_ai_table.files import (
    resolve_safe_path,
    safe_json_load as package_safe_json_load,
    validate_file_extension,
)
from dingtalk_ai_table.guards import (
    MAX_FIELDS_PER_CREATE,
    RESOURCE_ID_PATTERN,
    validate_dentry_uuid,
    validate_field_batch,
    validate_resource_id,
)

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_FILE_EXTENSIONS = ['.json']


def safe_json_load(file_path):
    return package_safe_json_load(file_path, MAX_FILE_SIZE)


def bulk_add_fields(base_id: str, table_id: str, fields_file: str) -> bool:
    try:
        safe_path = resolve_safe_path(fields_file)
    except ValueError as exc:
        print(f"路径验证失败：{exc}")
        return False

    if not validate_file_extension(fields_file, ALLOWED_FILE_EXTENSIONS):
        print(f"错误：只允许 {', '.join(ALLOWED_FILE_EXTENSIONS)} 文件")
        return False
    if not safe_path.exists():
        print(f"错误：文件不存在：{safe_path}")
        return False

    try:
        fields = safe_json_load(safe_path)
    except ValueError as exc:
        print(f"错误：{exc}")
        return False
    except json.JSONDecodeError as exc:
        print(f"错误：JSON 格式无效：{exc}")
        return False

    if not isinstance(fields, list) or not fields:
        print('错误：fields.json 必须是非空 JSON 数组')
        return False

    try:
        validate_field_batch(fields)
    except ValueError as exc:
        print(f"错误：{exc}")
        return False

    for index, field in enumerate(fields):
        valid, error = validate_field_config(field)
        if not valid:
            print(f"错误：字段 #{index + 1} 配置无效：{error}")
            return False

    try:
        result = create_fields(base_id, table_id, fields)
    except (RuntimeError, ValueError) as exc:
        print(exc)
        return False

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return True


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        print('用法示例:')
        print('  python3 bulk_add_fields.py basexxx tablexxx fields.json')
        sys.exit(1)

    base_id = sys.argv[1]
    table_id = sys.argv[2]
    fields_file = sys.argv[3]

    if not validate_resource_id(base_id):
        print('错误：无效的 baseId 格式')
        sys.exit(1)
    if not validate_resource_id(table_id):
        print('错误：无效的 tableId 格式')
        sys.exit(1)

    success = bulk_add_fields(base_id, table_id, fields_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

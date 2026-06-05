#!/usr/bin/env python3
"""
从 CSV / JSON 批量导入记录到钉钉 AI 表格（新 MCP schema）

用法:
    python3 import_records.py <baseId> <tableId> data.csv
    python3 import_records.py <baseId> <tableId> data.json [batch_size]

说明：
- CSV 表头默认视为 fieldId
- JSON 支持两种格式：
  1. [{"cells": {"fldxxx": "value"}}, ...]
  2. [{"fldxxx": "value"}, ...]  # 会自动包装成 cells
"""

import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from dingtalk_ai_table.client import build_mcporter_call, get_mcporter_version, parse_mcporter_version, run_mcporter
from dingtalk_ai_table.files import (
    resolve_safe_path,
    safe_csv_load as package_safe_csv_load,
    safe_json_load as package_safe_json_load,
    validate_file_extension,
)
from dingtalk_ai_table.guards import (
    MAX_RECORDS_PER_BATCH,
    RESOURCE_ID_PATTERN,
    validate_dentry_uuid,
    validate_resource_id,
)
from dingtalk_ai_table.records import (
    build_create_records_payload,
    create_records,
    normalize_record,
    sanitize_record_value,
    validate_record,
)

JsonData = Union[List[Any], Dict[str, Any]]
RecordDict = Dict[str, str]

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_CSV_EXTENSIONS = ['.csv']
ALLOWED_JSON_EXTENSIONS = ['.json']
DEFAULT_BATCH_SIZE = 50


def safe_csv_load(file_path):
    return package_safe_csv_load(file_path, MAX_FILE_SIZE)


def safe_json_load(file_path):
    return package_safe_json_load(file_path, MAX_FILE_SIZE, encoding='utf-8')


def import_from_csv(base_id: str, table_id: str, csv_file: str, batch_size: int = DEFAULT_BATCH_SIZE) -> bool:
    try:
        safe_path = resolve_safe_path(csv_file)
    except ValueError as exc:
        print(f"路径验证失败：{exc}")
        return False

    if not validate_file_extension(csv_file, ALLOWED_CSV_EXTENSIONS):
        print(f"错误：只允许 {', '.join(ALLOWED_CSV_EXTENSIONS)} 文件")
        return False
    if not safe_path.exists():
        print(f"错误：文件不存在：{safe_path}")
        return False

    try:
        rows = safe_csv_load(safe_path)
    except ValueError as exc:
        print(f"错误：{exc}")
        return False
    except csv.Error as exc:
        print(f"错误：CSV 格式无效：{exc}")
        return False

    if not rows:
        print('错误：CSV 文件为空或没有有效数据行')
        return False

    records = [normalize_record(row) for row in rows if normalize_record(row)['cells']]
    return import_records(base_id, table_id, records, batch_size)


def import_from_json(base_id: str, table_id: str, json_file: str, batch_size: int = DEFAULT_BATCH_SIZE) -> bool:
    try:
        safe_path = resolve_safe_path(json_file)
    except ValueError as exc:
        print(f"路径验证失败：{exc}")
        return False

    if not validate_file_extension(json_file, ALLOWED_JSON_EXTENSIONS):
        print(f"错误：只允许 {', '.join(ALLOWED_JSON_EXTENSIONS)} 文件")
        return False
    if not safe_path.exists():
        print(f"错误：文件不存在：{safe_path}")
        return False

    try:
        records = safe_json_load(safe_path)
    except ValueError as exc:
        print(f"错误：{exc}")
        return False
    except json.JSONDecodeError as exc:
        print(f"错误：JSON 格式无效：{exc}")
        return False

    if not isinstance(records, list) or not records:
        print('错误：JSON 文件必须是非空数组')
        return False

    for index, record in enumerate(records):
        valid, error = validate_record(record, [])
        if not valid:
            print(f"错误：记录 #{index + 1} 格式无效：{error}")
            return False

    return import_records(base_id, table_id, [normalize_record(record) for record in records], batch_size)


def import_records(base_id: str, table_id: str, records: List[Dict[str, Any]], batch_size: int) -> bool:
    if batch_size <= 0:
        print('错误：batch_size 必须大于 0')
        return False
    if batch_size > MAX_RECORDS_PER_BATCH:
        batch_size = MAX_RECORDS_PER_BATCH

    total_batches = (len(records) + batch_size - 1) // batch_size
    success = True

    for offset in range(0, len(records), batch_size):
        batch = records[offset:offset + batch_size]
        batch_num = (offset // batch_size) + 1
        try:
            create_records(base_id, table_id, batch)
            print(f"[{batch_num}/{total_batches}] ✓ 已提交 {len(batch)} 条记录")
        except (RuntimeError, ValueError) as exc:
            print(exc)
            print(f"[{batch_num}/{total_batches}] ✗ 导入失败")
            success = False

    return success


def main():
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print(__doc__)
        print('用法示例:')
        print('  python3 import_records.py basexxx tablexxx data.csv')
        print('  python3 import_records.py basexxx tablexxx data.json 50')
        sys.exit(1)

    base_id = sys.argv[1]
    table_id = sys.argv[2]
    input_file = sys.argv[3]
    batch_size = int(sys.argv[4]) if len(sys.argv) == 5 else DEFAULT_BATCH_SIZE

    if not validate_resource_id(base_id):
        print('错误：无效的 baseId 格式')
        sys.exit(1)
    if not validate_resource_id(table_id):
        print('错误：无效的 tableId 格式')
        sys.exit(1)

    if input_file.lower().endswith('.csv'):
        success = import_from_csv(base_id, table_id, input_file, batch_size)
    elif input_file.lower().endswith('.json'):
        success = import_from_json(base_id, table_id, input_file, batch_size)
    else:
        print('错误：仅支持 .csv 或 .json 文件')
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

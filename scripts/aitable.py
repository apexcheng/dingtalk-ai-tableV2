#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dingtalk_ai_table.fields import create_fields, get_fields, get_tables
from dingtalk_ai_table.filters import and_filter, date_eq_filter, eq_filter, iter_date_values, ne_filter, or_filter
from dingtalk_ai_table.guards import validate_filter_tree
from dingtalk_ai_table.records import extract_records
from dingtalk_ai_table.skill_api import (
    process_records_with_marker,
    resolve_field_id,
    resolve_option_id,
    safe_create_records,
    safe_delete_records,
    safe_prepare_attachment_upload,
    safe_query_records,
    safe_update_records,
)


class CliError(Exception):
    """CLI 参数或输入错误。"""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliError(message)


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False))


def parse_json_text(value: str, field_name: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CliError(f"{field_name} 不是合法 JSON: {exc}") from exc


def parse_json_value(value: Optional[str]) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def load_input_data(input_path: Optional[str]) -> Any:
    if not input_path:
        return {}

    path = Path(input_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliError(f"--input 文件不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"--input 不是合法 JSON: {exc}") from exc


def ensure_dict_input(data: Any) -> Dict[str, Any]:
    if data in ({}, None):
        return {}
    if not isinstance(data, dict):
        raise CliError("--input 顶层必须是 JSON 对象")
    return data


def pick_scalar(cli_value: Any, data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    if cli_value is not None:
        return cli_value
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def pick_list(cli_value: Any, data: Dict[str, Any], *keys: str) -> Any:
    if cli_value is not None:
        return cli_value
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def require_value(value: Any, field_name: str) -> Any:
    if value is None:
        raise CliError(f"{field_name} 不能为空")
    if isinstance(value, str) and not value.strip():
        raise CliError(f"{field_name} 不能为空")
    return value


def resolve_output_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def write_jsonl_records(output_path: Path, records: List[Dict[str, Any]]) -> None:
    with output_path.open("w", encoding="utf-8") as file_obj:
        for record in records:
            file_obj.write(json.dumps(record, ensure_ascii=False))
            file_obj.write("\n")


def append_jsonl_records(file_obj: TextIO, records: List[Dict[str, Any]]) -> None:
    for record in records:
        file_obj.write(json.dumps(record, ensure_ascii=False))
        file_obj.write("\n")


def build_preview(records: List[Dict[str, Any]], preview: int) -> List[Dict[str, Any]]:
    preview = max(0, preview)
    return records[:preview]


def normalize_process_action(action: Optional[str]) -> str:
    if action is None or not isinstance(action, str) or not action.strip():
        return "export-with-marker"

    normalized = action.strip()
    if normalized in {"stats", "collect"}:
        return "export-with-marker"
    if normalized in {"export-with-marker", "update", "delete"}:
        return normalized
    raise CliError(f"不支持的 action: {action}")


def extract_record_id(record: Dict[str, Any]) -> str:
    record_id = record.get("recordId") or record.get("id")
    if not record_id:
        raise ValueError("查询结果缺少 recordId")
    return record_id


def handle_get_tables(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_ids = require_value(pick_list(args.table_id, data, "tableIds", "table_ids"), "tableIds")
    return get_tables(base_id=base_id, table_ids=table_ids)


def handle_get_fields(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    field_ids = require_value(pick_list(args.field_id, data, "fieldIds", "field_ids"), "fieldIds")
    return get_fields(base_id=base_id, table_id=table_id, field_ids=field_ids)


def handle_create_fields(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    fields = pick_list(args.field, data, "fields")
    if args.field is not None:
        fields = [parse_json_text(item, "--field") for item in args.field]
    fields = require_value(fields, "fields")
    return create_fields(base_id=base_id, table_id=table_id, fields=fields)


def handle_resolve_field(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    field_name = require_value(pick_scalar(args.field_name, data, "fieldName", "field_name"), "fieldName")
    field_id = resolve_field_id(base_id=base_id, table_id=table_id, field_name=field_name)
    return {"fieldId": field_id}


def handle_resolve_option(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    field_name = require_value(pick_scalar(args.field_name, data, "fieldName", "field_name"), "fieldName")
    option_name = require_value(pick_scalar(args.option_name, data, "optionName", "option_name"), "optionName")
    option_id = resolve_option_id(
        base_id=base_id,
        table_id=table_id,
        field_name=field_name,
        option_name=option_name,
    )
    return {"optionId": option_id}


def build_filter_from_args(args: argparse.Namespace, data: Dict[str, Any]) -> Dict[str, Any]:
    input_filter = data.get("filter") or data.get("filters")
    if input_filter is not None:
        validate_filter_tree(input_filter)
        return input_filter

    operator = require_value(pick_scalar(args.operator, data, "operator"), "operator")
    if operator == "eq":
        field_id = require_value(pick_scalar(args.field_id, data, "fieldId", "field_id"), "fieldId")
        value = parse_json_value(pick_scalar(args.value, data, "value"))
        return eq_filter(field_id, value)
    if operator == "ne":
        field_id = require_value(pick_scalar(args.field_id, data, "fieldId", "field_id"), "fieldId")
        value = parse_json_value(pick_scalar(args.value, data, "value"))
        return ne_filter(field_id, value)
    if operator == "date_eq":
        field_id = require_value(pick_scalar(args.field_id, data, "fieldId", "field_id"), "fieldId")
        date_value = require_value(pick_scalar(args.value, data, "value", "dateValue", "date_value"), "dateValue")
        return date_eq_filter(field_id, date_value)
    if operator in {"and", "or"}:
        operand_values = pick_list(args.operand, data, "operands")
        operand_values = require_value(operand_values, "operands")
        operands = [
            parse_json_text(item, "--operand") if isinstance(item, str) else item
            for item in operand_values
        ]
        return and_filter(*operands) if operator == "and" else or_filter(*operands)

    raise CliError(f"不支持的 operator: {operator}")


def handle_build_filter(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    return build_filter_from_args(args, data)


def handle_query_records(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    filters = pick_scalar(args.filters_json, data, "filters")
    if isinstance(filters, str):
        filters = parse_json_text(filters, "--filters-json")
    sort = pick_scalar(args.sort_json, data, "sort")
    if isinstance(sort, str):
        sort = parse_json_text(sort, "--sort-json")

    result = safe_query_records(
        base_id=base_id,
        table_id=table_id,
        record_ids=pick_list(args.record_id, data, "recordIds", "record_ids"),
        filters=filters,
        keyword=pick_scalar(args.keyword, data, "keyword"),
        sort=sort,
        field_ids=pick_list(args.field_id, data, "fieldIds", "field_ids"),
        limit=pick_scalar(args.limit, data, "limit"),
        cursor=pick_scalar(args.cursor, data, "cursor"),
    )
    records = extract_records(result)
    output_path = pick_scalar(args.output, data, "output")
    preview = pick_scalar(args.preview, data, "preview", default=3)
    summary = {
        "total": len(records),
        "preview": build_preview(records, preview),
    }
    if isinstance(result, dict):
        if "hasMore" in result:
            summary["hasMore"] = result["hasMore"]
        if "nextCursor" in result:
            summary["nextCursor"] = result["nextCursor"]
        data_obj = result.get("data")
        if isinstance(data_obj, dict):
            if "hasMore" in data_obj:
                summary["hasMore"] = data_obj["hasMore"]
            if "nextCursor" in data_obj:
                summary["nextCursor"] = data_obj["nextCursor"]

    if output_path:
        resolved_output_path = resolve_output_path(output_path)
        write_jsonl_records(resolved_output_path, records)
        summary["output"] = str(resolved_output_path)
    return summary


def handle_create_records(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    records = pick_list(args.record, data, "records")
    if args.record is not None:
        records = [parse_json_text(item, "--record") for item in args.record]
    records = require_value(records, "records")
    return safe_create_records(base_id=base_id, table_id=table_id, records=records)


def handle_update_records(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    records = pick_list(args.record, data, "records")
    if args.record is not None:
        records = [parse_json_text(item, "--record") for item in args.record]
    records = require_value(records, "records")
    return safe_update_records(base_id=base_id, table_id=table_id, records=records)


def handle_delete_records(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    record_ids = require_value(pick_list(args.record_id, data, "recordIds", "record_ids"), "recordIds")
    return safe_delete_records(base_id=base_id, table_id=table_id, record_ids=record_ids)


def build_marker_process_summary(
    action: str,
    base_id: str,
    table_id: str,
    preview: int,
    output_file: TextIO,
    update_cells: Optional[Dict[str, Any]] = None,
) -> Any:
    summary = {
        "action": action,
        "batchCount": 0,
        "recordCount": 0,
        "preview": [],
    }

    def process_batch(batch: List[Dict[str, Any]]) -> None:
        summary["batchCount"] += 1
        summary["recordCount"] += len(batch)
        append_jsonl_records(output_file, batch)

        if len(summary["preview"]) < preview:
            remaining = preview - len(summary["preview"])
            summary["preview"].extend(batch[:remaining])

        if action == "update":
            records = [
                {"recordId": extract_record_id(record), "cells": update_cells}
                for record in batch
            ]
            safe_update_records(base_id=base_id, table_id=table_id, records=records)

    return summary, process_batch


def delete_records_until_empty(
    base_id: str,
    table_id: str,
    output_file: TextIO,
    preview: int,
    filters: Optional[Dict[str, Any]] = None,
    sort: Optional[Any] = None,
    field_ids: Optional[List[str]] = None,
    keyword: Optional[str] = None,
) -> Dict[str, Any]:
    summary = {
        "action": "delete",
        "batchCount": 0,
        "recordCount": 0,
        "preview": [],
    }

    while True:
        result = safe_query_records(
            base_id=base_id,
            table_id=table_id,
            filters=filters,
            keyword=keyword,
            sort=sort,
            field_ids=field_ids,
            limit=100,
        )
        batch = extract_records(result)
        if not batch:
            break

        summary["batchCount"] += 1
        summary["recordCount"] += len(batch)
        append_jsonl_records(output_file, batch)

        if len(summary["preview"]) < preview:
            remaining = preview - len(summary["preview"])
            summary["preview"].extend(batch[:remaining])

        record_ids = [extract_record_id(record) for record in batch]
        safe_delete_records(base_id=base_id, table_id=table_id, record_ids=record_ids)

    return summary


def handle_process_records_with_marker(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    filters = pick_scalar(args.filters_json, data, "filters")
    if isinstance(filters, str):
        filters = parse_json_text(filters, "--filters-json")
    sort = pick_scalar(args.sort_json, data, "sort")
    if isinstance(sort, str):
        sort = parse_json_text(sort, "--sort-json")
    output_path = require_value(pick_scalar(args.output, data, "output"), "output")
    preview = pick_scalar(args.preview, data, "preview", default=3)

    action = normalize_process_action(pick_scalar(args.action, data, "action"))
    update_cells = pick_scalar(args.update_cells_json, data, "updateCells", "update_cells")
    if isinstance(update_cells, str):
        update_cells = parse_json_text(update_cells, "--update-cells-json")
    if action == "update" and not isinstance(update_cells, dict):
        raise CliError("action=update 时必须提供 updateCells")

    resolved_output_path = resolve_output_path(output_path)
    with resolved_output_path.open("w", encoding="utf-8") as output_file:
        if action == "delete":
            summary = delete_records_until_empty(
                base_id=base_id,
                table_id=table_id,
                output_file=output_file,
                preview=preview,
                filters=filters,
                sort=sort,
                field_ids=pick_list(args.field_id, data, "fieldIds", "field_ids"),
                keyword=pick_scalar(args.keyword, data, "keyword"),
            )
            return {
                "output": str(resolved_output_path),
                "summary": summary,
            }

        summary, process_batch = build_marker_process_summary(
            action=action,
            base_id=base_id,
            table_id=table_id,
            preview=preview,
            output_file=output_file,
            update_cells=update_cells,
        )
        task_marker = process_records_with_marker(
            base_id=base_id,
            table_id=table_id,
            process_batch=process_batch,
            filters=filters,
            sort=sort,
            field_ids=pick_list(args.field_id, data, "fieldIds", "field_ids"),
            keyword=pick_scalar(args.keyword, data, "keyword"),
            task_name=pick_scalar(args.task_name, data, "taskName", "task_name", default="batch_task"),
            readonly=pick_scalar(args.readonly, data, "readonly", default=False),
        )
    return {
        "taskMarker": task_marker,
        "output": str(resolved_output_path),
        "summary": summary,
    }


def handle_process_date_range_with_marker(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    table_id = require_value(pick_scalar(args.table_id, data, "tableId", "table_id"), "tableId")
    date_field_id = require_value(
        pick_scalar(args.date_field_id, data, "dateFieldId", "date_field_id"),
        "dateFieldId",
    )
    start_date = require_value(pick_scalar(args.start_date, data, "startDate", "start_date"), "startDate")
    end_date = require_value(pick_scalar(args.end_date, data, "endDate", "end_date"), "endDate")
    filters = pick_scalar(args.filters_json, data, "filters")
    if isinstance(filters, str):
        filters = parse_json_text(filters, "--filters-json")
    sort = pick_scalar(args.sort_json, data, "sort")
    if isinstance(sort, str):
        sort = parse_json_text(sort, "--sort-json")
    output_dir = require_value(pick_scalar(args.output_dir, data, "outputDir", "output_dir"), "outputDir")
    preview = pick_scalar(args.preview, data, "preview", default=3)

    action = normalize_process_action(pick_scalar(args.action, data, "action"))
    update_cells = pick_scalar(args.update_cells_json, data, "updateCells", "update_cells")
    if isinstance(update_cells, str):
        update_cells = parse_json_text(update_cells, "--update-cells-json")
    if action == "update" and not isinstance(update_cells, dict):
        raise CliError("action=update 时必须提供 updateCells")

    resolved_output_dir = resolve_output_path(str(Path(output_dir) / "placeholder.jsonl")).parent
    task_name = pick_scalar(args.task_name, data, "taskName", "task_name", default="date_range_task")
    readonly = pick_scalar(args.readonly, data, "readonly", default=False)
    field_ids = pick_list(args.field_id, data, "fieldIds", "field_ids")
    keyword = pick_scalar(args.keyword, data, "keyword")

    all_results = []
    total_summary = {
        "action": action,
        "dayCount": 0,
        "batchCount": 0,
        "recordCount": 0,
    }

    for date_value in iter_date_values(start_date, end_date):
        day_filter = date_eq_filter(date_field_id, date_value)
        current_filters = and_filter(filters, day_filter) if filters is not None else day_filter
        day_output_path = resolve_output_path(str(resolved_output_dir / f"{date_value}.jsonl"))
        with day_output_path.open("w", encoding="utf-8") as output_file:
            if action == "delete":
                day_summary = delete_records_until_empty(
                    base_id=base_id,
                    table_id=table_id,
                    output_file=output_file,
                    preview=preview,
                    filters=current_filters,
                    sort=sort,
                    field_ids=field_ids,
                    keyword=keyword,
                )
                task_marker = None
            else:
                day_summary, process_batch = build_marker_process_summary(
                    action=action,
                    base_id=base_id,
                    table_id=table_id,
                    preview=preview,
                    output_file=output_file,
                    update_cells=update_cells,
                )
                task_marker = process_records_with_marker(
                    base_id=base_id,
                    table_id=table_id,
                    process_batch=process_batch,
                    filters=current_filters,
                    sort=sort,
                    field_ids=field_ids,
                    keyword=keyword,
                    task_name=f"{task_name}_{date_value}",
                    readonly=readonly,
                )
        total_summary["dayCount"] += 1
        total_summary["batchCount"] += day_summary["batchCount"]
        total_summary["recordCount"] += day_summary["recordCount"]
        day_result = {
            "date": date_value,
            "output": str(day_output_path),
            "summary": day_summary,
        }
        if task_marker is not None:
            day_result["taskMarker"] = task_marker
        all_results.append(day_result)

    return {
        "outputDir": str(resolved_output_dir),
        "results": all_results,
        "summary": total_summary,
    }


def handle_prepare_attachment_upload(args: argparse.Namespace) -> Any:
    data = ensure_dict_input(load_input_data(args.input))
    base_id = require_value(pick_scalar(args.base_id, data, "baseId", "base_id"), "baseId")
    file_name = require_value(pick_scalar(args.file_name, data, "fileName", "file_name"), "fileName")
    size = require_value(pick_scalar(args.size, data, "size"), "size")
    mime_type = pick_scalar(args.mime_type, data, "mimeType", "mime_type")
    return safe_prepare_attachment_upload(
        base_id=base_id,
        file_name=file_name,
        size=size,
        mime_type=mime_type,
    )


def add_common_input_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", help="JSON 输入文件路径")


def add_base_table_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-id")
    parser.add_argument("--table-id")


def add_query_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--filters-json", help="filters JSON 字符串")
    parser.add_argument("--sort-json", help="sort JSON 字符串")
    parser.add_argument("--field-id", action="append", default=None)
    parser.add_argument("--keyword")
    parser.add_argument("--preview", type=int, default=None)


def add_process_arguments(parser: argparse.ArgumentParser) -> None:
    add_query_arguments(parser)
    parser.add_argument("--task-name")
    parser.add_argument("--readonly", action="store_true", default=None)
    parser.add_argument(
        "--action",
        choices=["export-with-marker", "update", "delete", "stats", "collect"],
        default="export-with-marker",
        help="导出/更新/删除的批处理动作，stats/collect 为旧别名",
    )
    parser.add_argument("--update-cells-json", help="action=update 时传入 cells JSON")


def build_parser() -> JsonArgumentParser:
    parser = JsonArgumentParser(
        prog="aitable",
        formatter_class=HelpFormatter,
        description=(
            "Agent-first safe CLI for DingTalk AI Table.\n"
            "The package dingtalk_ai_table is internal implementation only."
        ),
        epilog=(
            "Config priority:\n"
            "  1. agent workspace/config/mcporter.json\n"
            "  2. DINGTALK_AI_TABLE_DIRECT_URL\n\n"
            "Examples:\n"
            "  python scripts/aitable.py resolve-field --base-id xxx --table-id xxx --field-name 状态\n"
            "  python scripts/aitable.py query-records --input examples/query_records.json\n"
            "  python scripts/aitable.py process-records-with-marker --input examples/process_records_with_marker.json\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_tables_parser = subparsers.add_parser(
        "get-tables",
        help="查询表结构",
        description="Query table metadata by tableId list.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(get_tables_parser)
    get_tables_parser.add_argument("--base-id")
    get_tables_parser.add_argument("--table-id", action="append", default=None)
    get_tables_parser.set_defaults(handler=handle_get_tables)

    get_fields_parser = subparsers.add_parser(
        "get-fields",
        help="查询字段配置",
        description="Query field metadata by fieldId list.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(get_fields_parser)
    add_base_table_arguments(get_fields_parser)
    get_fields_parser.add_argument("--field-id", action="append", default=None)
    get_fields_parser.set_defaults(handler=handle_get_fields)

    create_fields_parser = subparsers.add_parser(
        "create-fields",
        help="创建字段",
        description="Create fields in a table.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(create_fields_parser)
    add_base_table_arguments(create_fields_parser)
    create_fields_parser.add_argument("--field", action="append", default=None, help="单个字段 JSON")
    create_fields_parser.set_defaults(handler=handle_create_fields)

    resolve_field_parser = subparsers.add_parser(
        "resolve-field",
        help="按字段名解析 fieldId",
        description="Resolve fieldId from a field name.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(resolve_field_parser)
    add_base_table_arguments(resolve_field_parser)
    resolve_field_parser.add_argument("--field-name")
    resolve_field_parser.set_defaults(handler=handle_resolve_field)

    resolve_option_parser = subparsers.add_parser(
        "resolve-option",
        help="按选项名解析 optionId",
        description="Resolve optionId from a select option name.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(resolve_option_parser)
    add_base_table_arguments(resolve_option_parser)
    resolve_option_parser.add_argument("--field-name")
    resolve_option_parser.add_argument("--option-name")
    resolve_option_parser.set_defaults(handler=handle_resolve_option)

    build_filter_parser = subparsers.add_parser(
        "build-filter",
        help="构建并校验 filters",
        description="Build and validate a filters JSON object.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(build_filter_parser)
    build_filter_parser.add_argument("--operator")
    build_filter_parser.add_argument("--field-id")
    build_filter_parser.add_argument("--value")
    build_filter_parser.add_argument("--operand", action="append", default=None, help="单个 operand JSON")
    build_filter_parser.set_defaults(handler=handle_build_filter)

    query_records_parser = subparsers.add_parser(
        "query-records",
        help="查询记录",
        description="Query records and optionally write the full result to JSONL.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(query_records_parser)
    add_base_table_arguments(query_records_parser)
    query_records_parser.add_argument("--record-id", action="append", default=None)
    query_records_parser.add_argument("--limit", type=int)
    query_records_parser.add_argument("--cursor")
    query_records_parser.add_argument("--output")
    add_query_arguments(query_records_parser)
    query_records_parser.set_defaults(handler=handle_query_records)

    create_records_parser = subparsers.add_parser(
        "create-records",
        help="创建记录",
        description="Create records in a table.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(create_records_parser)
    add_base_table_arguments(create_records_parser)
    create_records_parser.add_argument("--record", action="append", default=None, help="单条记录 JSON")
    create_records_parser.set_defaults(handler=handle_create_records)

    update_records_parser = subparsers.add_parser(
        "update-records",
        help="更新记录",
        description="Update existing records by recordId.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(update_records_parser)
    add_base_table_arguments(update_records_parser)
    update_records_parser.add_argument("--record", action="append", default=None, help="单条记录 JSON")
    update_records_parser.set_defaults(handler=handle_update_records)

    delete_records_parser = subparsers.add_parser(
        "delete-records",
        help="删除记录",
        description="Delete records by recordId.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(delete_records_parser)
    add_base_table_arguments(delete_records_parser)
    delete_records_parser.add_argument("--record-id", action="append", default=None)
    delete_records_parser.set_defaults(handler=handle_delete_records)

    process_records_parser = subparsers.add_parser(
        "process-records-with-marker",
        help="使用 marker 处理记录",
        description="Process records in batches; export-with-marker writes query markers.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(process_records_parser)
    add_base_table_arguments(process_records_parser)
    add_process_arguments(process_records_parser)
    process_records_parser.add_argument("--output")
    process_records_parser.set_defaults(handler=handle_process_records_with_marker)

    process_date_range_parser = subparsers.add_parser(
        "process-date-range-with-marker",
        help="按日期范围使用 marker 处理记录",
        description="Split a date range into daily marker batches.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(process_date_range_parser)
    add_base_table_arguments(process_date_range_parser)
    process_date_range_parser.add_argument("--date-field-id")
    process_date_range_parser.add_argument("--start-date")
    process_date_range_parser.add_argument("--end-date")
    add_process_arguments(process_date_range_parser)
    process_date_range_parser.add_argument("--output-dir")
    process_date_range_parser.set_defaults(handler=handle_process_date_range_with_marker)

    prepare_attachment_parser = subparsers.add_parser(
        "prepare-attachment-upload",
        help="准备附件上传",
        description="Prepare attachment upload metadata.",
        formatter_class=HelpFormatter,
    )
    add_common_input_argument(prepare_attachment_parser)
    prepare_attachment_parser.add_argument("--base-id")
    prepare_attachment_parser.add_argument("--file-name")
    prepare_attachment_parser.add_argument("--size", type=int)
    prepare_attachment_parser.add_argument("--mime-type")
    prepare_attachment_parser.set_defaults(handler=handle_prepare_attachment_upload)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    command_name = argv[0] if argv else None

    try:
        args = parser.parse_args(argv)
        result = args.handler(args)
        print_json({
            "ok": True,
            "command": args.command,
            "result": result,
        })
        return 0
    except Exception as exc:
        print_json({
            "ok": False,
            "command": command_name,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        })
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .fields import ensure_query_mark_field
from .filters import and_filter, date_eq_filter, ne_filter, iter_date_values
from .guards import MAX_QUERY_LIMIT, ensure_resource_id
from .records import extract_records, query_records, update_records
from .client import TruncatedResponseError

READONLY_MARKER_ERROR = 'filters/sort 场景下超过 100 条且禁止写入查询标记，无法保证稳定分页'
MARK_SYNC_WAIT_SECONDS = 3
# marker 回写查询标记失败时报错信息中含此前缀；外层
# `except RuntimeError` 会先检查这个 sentinel，确保新抛出的错误
# 不会袸当成 “update 截断、靠 cursor 推进” 的路径误吞。
MARK_WRITE_ABORT_SENTINEL = '写入查询标记失败，recordId='


def build_task_marker(task_name: str, now: Optional[datetime] = None) -> str:
    if not isinstance(task_name, str) or not task_name.strip():
        raise ValueError('task_name 不能为空')

    current_time = now or datetime.now()
    normalized_name = re.sub(r'\s+', '_', task_name.strip())
    return f"task_{current_time:%Y%m%d_%H%M%S}_{normalized_name}"


def _extract_record_id(record: Dict[str, Any]) -> str:
    record_id = record.get('recordId') or record.get('id')
    if not record_id:
        raise ValueError('查询结果缺少 recordId')
    return record_id


def query_with_marker(
    base_id: str,
    table_id: str,
    process_batch: Callable[[List[Dict[str, Any]]], Any],
    filters: Optional[Dict[str, Any]] = None,
    sort: Optional[Any] = None,
    field_ids: Optional[List[str]] = None,
    keyword: Optional[str] = None,
    task_name: str = 'batch_task',
    readonly: bool = False,
) -> str:
    if not callable(process_batch):
        raise ValueError('process_batch 必须是可调用对象')
    if filters is None and sort is None:
        raise ValueError('query_with_marker 仅适用于 filters 或 sort 场景')
    if readonly:
        raise ValueError(READONLY_MARKER_ERROR)

    mark_field_id = ensure_query_mark_field(base_id, table_id)
    task_marker = build_task_marker(task_name)
    cursor = None

    while True:
        mark_filter = ne_filter(mark_field_id, task_marker)
        current_filters = and_filter(filters, mark_filter) if filters is not None else mark_filter
        try:
            result = query_records(
                base_id=base_id,
                table_id=table_id,
                filters=current_filters,
                keyword=keyword,
                sort=sort,
                field_ids=field_ids,
                limit=MAX_QUERY_LIMIT,
                cursor=cursor,
                _internal_cursor_ok=True,
            )
        except TruncatedResponseError as exc:
            if exc.suggested_limit and MAX_QUERY_LIMIT > exc.suggested_limit:
                result = query_records(
                    base_id=base_id,
                    table_id=table_id,
                    filters=current_filters,
                    keyword=keyword,
                    sort=sort,
                    field_ids=field_ids,
                    limit=exc.suggested_limit,
                    cursor=cursor,
                    _internal_cursor_ok=True,
                )
            else:
                raise
        batch_records = extract_records(result)
        if not batch_records:
            break

        process_batch(batch_records)
        update_payload = []
        for record in batch_records:
            update_payload.append({
                'recordId': _extract_record_id(record),
                'cells': {mark_field_id: task_marker},
            })

        # Mark records: use record_ids query first (minimal fields → small response),
        # then update. This avoids pipe buffer truncation that affects bulk update.
        try:
            # First: query by record_ids with only mark field to verify IDs exist.
            result_verify = query_records(
                base_id=base_id,
                table_id=table_id,
                record_ids=[rec['recordId'] for rec in update_payload],
                field_ids=[mark_field_id],
                limit=len(update_payload),
            )
            updated_verify = extract_records(result_verify)
            # Build clean payload from verified records.
            clean_payload = [
                {'recordId': _extract_record_id(rec), 'cells': {mark_field_id: task_marker}}
                for rec in updated_verify
            ]
            if clean_payload:
                update_records(base_id, table_id, clean_payload)
        except TruncatedResponseError:
            # record_ids query itself truncated; fall back to one-by-one.
            for record in update_payload:
                record_id = _extract_record_id(record)
                try:
                    result_one = query_records(
                        base_id=base_id,
                        table_id=table_id,
                        record_ids=[record_id],
                        field_ids=[mark_field_id],
                        limit=1,
                    )
                    updated_one = extract_records(result_one)
                    if updated_one:
                        update_records(base_id, table_id, [record])
                except Exception as exc:
                    # Fallback 单条写入查询标记失败：不要静默跳过，
                    # 改为报错中断 marker 流程，避免批量处理中漏写标记、
                    # 后续 cursor 推进时重复处理同一条记录。
                    raise RuntimeError(
                        f"写入查询标记失败，recordId={record_id}，已停止处理以避免漏数据: {exc}"
                    ) from exc
        except RuntimeError as exc:
            # marker 写入必须失败、不能被当成 “update 截断” 处理。
            if MARK_WRITE_ABORT_SENTINEL in str(exc):
                raise
            # update_records response truncated; server update succeeded.
            # Advance via cursor to avoid re-fetching same records.
            cursor = result.get('data', {}).get('nextCursor')
            if cursor:
                time.sleep(MARK_SYNC_WAIT_SECONDS)
                continue
            else:
                break

        # Check if there are more records: either batch is full, or nextCursor exists.
        has_next_cursor = bool(result.get('data', {}).get('nextCursor'))
        if len(batch_records) < MAX_QUERY_LIMIT and not has_next_cursor:
            break

        # Advance cursor for next iteration if there are more records.
        cursor = result.get('data', {}).get('nextCursor')
        if not cursor:
            break

        time.sleep(MARK_SYNC_WAIT_SECONDS)


    return task_marker


def query_date_range_with_marker(
    base_id: str,
    table_id: str,
    date_field_id: str,
    start_date: str,
    end_date: str,
    process_batch: Callable[[List[Dict[str, Any]]], Any],
    filters: Optional[Dict[str, Any]] = None,
    sort: Optional[Any] = None,
    field_ids: Optional[List[str]] = None,
    keyword: Optional[str] = None,
    task_name: str = 'date_range_task',
    readonly: bool = False,
) -> List[Dict[str, str]]:
    """
    按天拆分日期范围，并在每天内部使用查询标记推进。

    :param str base_id: Base ID
    :param str table_id: Table ID
    :param str date_field_id: 日期字段 ID
    :param Callable process_batch: 每批记录处理函数
    :return list: 每天对应的任务标记结果
    """
    ensure_resource_id(date_field_id, 'dateFieldId')

    results = []
    for date_value in iter_date_values(start_date, end_date):
        day_filter = date_eq_filter(date_field_id, date_value)
        current_filters = and_filter(filters, day_filter) if filters is not None else day_filter
        day_task_name = f'{task_name}_{date_value}'
        task_marker = query_with_marker(
            base_id=base_id,
            table_id=table_id,
            process_batch=process_batch,
            filters=current_filters,
            sort=sort,
            field_ids=field_ids,
            keyword=keyword,
            task_name=day_task_name,
            readonly=readonly,
        )
        results.append({
            'date': date_value,
            'taskMarker': task_marker,
        })

    return results

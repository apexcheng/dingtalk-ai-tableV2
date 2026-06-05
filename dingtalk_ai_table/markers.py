import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .fields import ensure_query_mark_field
from .filters import and_filter, date_eq_filter, ne_filter, iter_date_values
from .guards import MAX_QUERY_LIMIT, ensure_resource_id
from .records import extract_records, query_records, update_records

READONLY_MARKER_ERROR = 'filters/sort 场景下超过 100 条且禁止写入查询标记，无法保证稳定分页'


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

    while True:
        mark_filter = ne_filter(mark_field_id, task_marker)
        current_filters = and_filter(filters, mark_filter) if filters is not None else mark_filter
        result = query_records(
            base_id=base_id,
            table_id=table_id,
            filters=current_filters,
            keyword=keyword,
            sort=sort,
            field_ids=field_ids,
            limit=MAX_QUERY_LIMIT,
        )
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
        update_records(base_id, table_id, update_payload)

        if len(batch_records) < MAX_QUERY_LIMIT:
            break

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

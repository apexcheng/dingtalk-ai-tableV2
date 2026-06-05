from datetime import datetime, timedelta
from typing import Any, Dict, List

from .guards import ensure_resource_id, validate_date_string, validate_filter_tree


def eq_filter(field_id: str, value: Any) -> Dict[str, Any]:
    ensure_resource_id(field_id, 'fieldId')
    if value is None:
        raise ValueError('eq 过滤值不能为空')
    filter_obj = {'operator': 'eq', 'operands': [field_id, value]}
    validate_filter_tree(filter_obj)
    return filter_obj


def ne_filter(field_id: str, value: Any) -> Dict[str, Any]:
    ensure_resource_id(field_id, 'fieldId')
    if value is None:
        raise ValueError('ne 过滤值不能为空')
    filter_obj = {'operator': 'ne', 'operands': [field_id, value]}
    validate_filter_tree(filter_obj)
    return filter_obj


def date_eq_filter(field_id: str, date_value: str) -> Dict[str, Any]:
    ensure_resource_id(field_id, 'fieldId')
    validate_date_string(date_value)
    filter_obj = {'operator': 'date_eq', 'operands': [field_id, date_value]}
    validate_filter_tree(filter_obj)
    return filter_obj


def and_filter(*filters: Dict[str, Any]) -> Dict[str, Any]:
    filter_list = [item for item in filters if item is not None]
    if not filter_list:
        raise ValueError('and_filter 至少需要一个过滤条件')
    filter_obj = {'operator': 'and', 'operands': filter_list}
    validate_filter_tree(filter_obj)
    return filter_obj


def or_filter(*filters: Dict[str, Any]) -> Dict[str, Any]:
    filter_list = [item for item in filters if item is not None]
    if not filter_list:
        raise ValueError('or_filter 至少需要一个过滤条件')
    filter_obj = {'operator': 'or', 'operands': filter_list}
    validate_filter_tree(filter_obj)
    return filter_obj


def iter_date_values(start_date: str, end_date: str) -> List[str]:
    validate_date_string(start_date)
    validate_date_string(end_date)

    start_value = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_value = datetime.strptime(end_date, '%Y-%m-%d').date()
    if start_value > end_value:
        raise ValueError('开始日期不能晚于结束日期')

    values = []
    current_value = start_value
    while current_value <= end_value:
        values.append(current_value.strftime('%Y-%m-%d'))
        current_value += timedelta(days=1)
    return values

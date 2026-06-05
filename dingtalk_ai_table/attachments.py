import json
from typing import Any, Dict, List, Optional

from .client import run_mcporter
from .guards import ensure_resource_id


def prepare_attachment_upload(base_id: str, file_name: str, size: int, mime_type: Optional[str] = None) -> Any:
    base_id = ensure_resource_id(base_id, 'baseId')
    if not isinstance(file_name, str) or '.' not in file_name:
        raise ValueError('fileName 必须包含扩展名')
    if not isinstance(size, int) or size <= 0:
        raise ValueError('size 必须大于 0')

    payload = {
        'baseId': base_id,
        'fileName': file_name,
        'size': size,
    }
    if mime_type:
        payload['mimeType'] = mime_type
    return run_mcporter(['prepare_attachment_upload', '--args', json.dumps(payload, ensure_ascii=False)])


def build_attachment_cell_from_file_token(file_token: str) -> List[Dict[str, str]]:
    if not isinstance(file_token, str) or not file_token.strip():
        raise ValueError('fileToken 不能为空')
    return [{'fileToken': file_token.strip()}]


def merge_attachments(
    old_attachments: Optional[List[Dict[str, Any]]],
    new_attachments: Optional[List[Dict[str, Any]]],
    overwrite: bool = False,
) -> List[Dict[str, Any]]:
    old_list = list(old_attachments or [])
    new_list = list(new_attachments or [])
    if overwrite:
        return new_list
    return old_list + new_list

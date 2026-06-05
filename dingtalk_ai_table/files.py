import csv
import json
import os
from pathlib import Path
from typing import Any, List, Optional


def resolve_safe_path(path: str, allowed_root: Optional[str] = None) -> Path:
    if allowed_root is None:
        allowed_root = os.environ.get('OPENCLAW_WORKSPACE', os.getcwd())

    allowed_root_path = Path(allowed_root).resolve()
    if Path(path).is_absolute():
        target_path = Path(path).resolve()
    else:
        target_path = (Path.cwd() / path).resolve()

    try:
        target_path.relative_to(allowed_root_path)
        return target_path
    except ValueError:
        raise ValueError(
            f"路径超出允许范围：{path}\n"
            f"目标路径：{target_path}\n"
            f"允许根目录：{allowed_root_path}\n"
            f"提示：设置 OPENCLAW_WORKSPACE 环境变量或确保文件在工作目录内"
        )


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)


def safe_json_load(file_path: Path, max_size: int, encoding: str = 'utf-8-sig') -> Any:
    file_size = file_path.stat().st_size
    if file_size > max_size:
        raise ValueError(f"文件过大：{file_size:,} 字节 (限制：{max_size:,} 字节)")
    with open(file_path, 'r', encoding=encoding) as file_obj:
        return json.load(file_obj)


def safe_csv_load(file_path: Path, max_size: int, encoding: str = 'utf-8-sig') -> List[dict]:
    file_size = file_path.stat().st_size
    if file_size > max_size:
        raise ValueError(f"文件过大：{file_size:,} 字节 (限制：{max_size:,} 字节)")
    with open(file_path, 'r', encoding=encoding, newline='') as file_obj:
        return list(csv.DictReader(file_obj))

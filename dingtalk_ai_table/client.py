import json
import os
import re
import subprocess
from functools import lru_cache
from typing import Any, List, Optional, Tuple

MCPORTER_VERSION_PATTERN = re.compile(r'(\d+)\.(\d+)\.(\d+)')
MCPORTER_TEXT_OUTPUT_CUTOFF = (0, 8, 1)


def parse_mcporter_version(raw_text: str) -> Optional[Tuple[int, int, int]]:
    match = MCPORTER_VERSION_PATTERN.search(raw_text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


@lru_cache(maxsize=1)
def get_mcporter_version() -> Optional[Tuple[int, int, int]]:
    for cmd in (['mcporter', '--version'], ['mcporter', 'version']):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

        if result.returncode != 0:
            continue

        version = parse_mcporter_version(f"{result.stdout}\n{result.stderr}")
        if version is not None:
            return version

    return None


def build_mcporter_call(args: List[str]) -> List[str]:
    direct_url = os.environ.get('DINGTALK_AI_TABLE_DIRECT_URL')
    if direct_url:
        tool_name = args[0]
        if not tool_name.startswith('.'):
            tool_name = f'.{tool_name}'
        cmd = ['mcporter', 'call', direct_url]
        args = [tool_name] + args[1:]
    else:
        cmd = ['mcporter', 'call', 'dingtalk-ai-table']

    version = get_mcporter_version()
    if version is not None and version < MCPORTER_TEXT_OUTPUT_CUTOFF:
        cmd.extend(['--output', 'text'])
    return cmd + args


def run_mcporter(args: List[str], timeout: int = 60) -> Any:
    if not args:
        raise ValueError('错误：空命令')

    cmd = build_mcporter_call(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'错误：命令执行超时（{timeout} 秒）')
    except FileNotFoundError:
        raise RuntimeError('错误：未找到 mcporter 命令，请确认已安装')

    if result.returncode != 0:
        error_text = result.stderr.strip() or result.stdout.strip() or 'mcporter 调用失败'
        raise RuntimeError(f'错误：{error_text}')

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        preview = result.stdout[:200]
        raise RuntimeError(f'无法解析响应：{preview}...\nJSON 解析错误：{exc}')

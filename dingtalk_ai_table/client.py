import json
import os
import subprocess
from typing import Any, List


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

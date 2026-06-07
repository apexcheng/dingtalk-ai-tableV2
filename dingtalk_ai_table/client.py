import json
import os
import subprocess
from typing import Any, Dict, List, Optional


class TruncatedResponseError(RuntimeError):
    """
    Raised when MCP response JSON is truncated at the OS pipe buffer boundary.
    Callers should retry with a smaller limit.
    """
    def __init__(self, message: str, suggested_limit: Optional[int] = None):
        super().__init__(message)
        self.suggested_limit = suggested_limit


MCPORTER_CONFIG_ENV = 'MCPORTER_CONFIG'
PROJECT_MCPORTER_CONFIG = os.path.join('config', 'mcporter.json')
MCP_SERVER_NAME = 'dingtalk-ai-table'


def get_mcporter_config_path() -> str:
    """
    获取 mcporter 配置文件路径。

    优先级：
    1. MCPORTER_CONFIG 环境变量
    2. {cwd}/config/mcporter.json
    """
    config_path = os.environ.get(MCPORTER_CONFIG_ENV)
    if config_path:
        return config_path

    config_path = os.path.join(os.getcwd(), PROJECT_MCPORTER_CONFIG)
    if os.path.isfile(config_path):
        return config_path

    raise RuntimeError(
        '错误：未找到 mcporter 配置文件，请设置 MCPORTER_CONFIG，'
        '或在当前工作目录创建 config/mcporter.json'
    )


def build_mcporter_env() -> Dict[str, str]:
    env = os.environ.copy()
    env[MCPORTER_CONFIG_ENV] = get_mcporter_config_path()
    return env


def build_mcporter_call(args: List[str]) -> List[str]:
    return ['mcporter', 'call', MCP_SERVER_NAME] + args


def run_mcporter(args: List[str], timeout: int = 60) -> Any:
    if not args:
        raise ValueError('错误：空命令')

    cmd = build_mcporter_call(args)
    try:
        # Use raw bytes mode to avoid locale-decoding failures on truncated/binary output.
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            env=build_mcporter_env(),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'错误：命令执行超时（{timeout} 秒）')
    except FileNotFoundError:
        raise RuntimeError('错误：未找到 mcporter 命令，请确认已安装')

    # Decode stdout as UTF-8 with replacement for malformed bytes (e.g. truncated responses).
    stdout_bytes = result.stdout
    stderr_text = result.stderr.decode('utf-8', errors='replace').strip() if result.stderr else ''

    if result.returncode != 0:
        error_text = stderr_text or 'mcporter 调用失败'
        raise RuntimeError(f'错误：{error_text}')

    try:
        stdout_str = stdout_bytes.decode('utf-8', errors='replace')
        return json.loads(stdout_str)
    except json.JSONDecodeError as exc:
        # Detect truncation at the OS pipe buffer boundary (64KB).
        # Signals: response near/at 65536 bytes + JSON fails mid-document.
        # Note: json.JSONDecodeError.msg keeps the original source quotes,
        # so 'Expecting ',' delimiter' is literally 'Expecting "," delimiter'.
        is_truncation = (
            len(stdout_bytes) >= 55000
            and exc.msg in (
                'Unterminated string starting at',
                'Expecting \',\' delimiter',
                'Unterminated object',
                'Invalid control character',
                'Expecting property name enclosed in double quotes',
                'Invalid \ufeff',
            )
        ) or (
            # Also detect exact buffer boundary hits (65536 = 64KB pipe buffer).
            len(stdout_bytes) in (65535, 65536, 65537)
        )
        if is_truncation:
            raise TruncatedResponseError(
                f'响应在约 {len(stdout_bytes)} 字节处被截断（MCP pipe buffer 边界），请减少 limit 参数后重试',
                suggested_limit=20,
            ) from exc
        preview = stdout_str[:200]
        raise RuntimeError(f'无法解析响应：{preview}...\nJSON 解析错误：{exc}')
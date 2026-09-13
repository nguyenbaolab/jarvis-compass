"""Base types cho JARVIS tool system."""

from dataclasses import dataclass


@dataclass
class ToolResult:
    """Kết quả trả về từ một tool execution."""

    success: bool
    output: str  # text mô tả kết quả, sẽ feed vào LLM


class ToolError(Exception):
    """Raised khi tool execution thất bại."""

    pass

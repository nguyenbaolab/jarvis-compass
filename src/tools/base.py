"""Base types cho JARVIS tool system."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

Remaining = Callable[[], float] | None


@dataclass(frozen=True)
class WriteEffect:
    """Hiệu lực một lần ghi. Không đưa vào tin nhắn gửi mô hình."""

    kind: Literal["saved", "uncertain", "rejected"]
    text: str = ""


@dataclass
class ToolResult:
    """Kết quả trả về từ một tool execution."""

    success: bool
    output: str  # text mô tả kết quả, sẽ feed vào LLM
    effect: WriteEffect | None = None


class ToolError(Exception):
    """Raised khi tool execution thất bại. effect mặc định trống."""

    def __init__(self, message: str = "", *, effect: WriteEffect | None = None) -> None:
        super().__init__(message)
        self.effect = effect

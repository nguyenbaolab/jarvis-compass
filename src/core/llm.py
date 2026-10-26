"""Cổng mô hình trung lập. Chỉ thư viện chuẩn. Không mở mạng và không gọi SDK."""

from dataclasses import dataclass
from typing import Literal, Protocol


Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class TextMessage:
    """Một tin văn bản. Không chứa khối tool."""

    role: Role
    text: str


@dataclass(frozen=True)
class ToolRequest:
    """Một yêu cầu tool đã đủ id, tên và object đầu vào."""

    id: str
    name: str
    tool_input: dict[str, object]


@dataclass(frozen=True)
class ToolResultMessage:
    """Kết quả một tool, chỉ để gửi lại cho lần complete kế tiếp."""

    tool_use_id: str
    output: str
    is_error: bool


Round = tuple[tuple[ToolRequest, ...], tuple[ToolResultMessage, ...]]


@dataclass(frozen=True)
class ModelRequest:
    """Đối số của một lần complete."""

    system: str
    messages: tuple[TextMessage, ...]
    tools: dict[str, dict[str, object]]
    rounds: tuple[Round, ...]


@dataclass(frozen=True)
class ModelResponse:
    """Phản hồi đã dịch sau một lần complete thành công."""

    text: str
    tool_requests: tuple[ToolRequest, ...]
    stop_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    model: str


class ModelError(Exception):
    """Lỗi cổng. class_name là tên lớp exception của SDK, không phải thông điệp."""

    def __init__(self, class_name: str) -> None:
        self.class_name = class_name
        super().__init__(class_name)


class ModelClient(Protocol):
    """Cổng một lần gọi. Người gọi đưa khóa và phần thời gian còn lại."""

    model: str

    async def complete(
        self,
        request: ModelRequest,
        *,
        api_key: str,
        timeout: float,
    ) -> ModelResponse:
        """Gọi mô hình một lần và trả phản hồi đã dịch."""

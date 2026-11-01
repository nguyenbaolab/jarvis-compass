"""Catalog sáu tool kế hoạch. Phiên bản là số nguyên, không phải chuỗi."""

DEFINITIONS_VERSION: int = 2

TOOL_DEFINITIONS: dict[str, dict[str, object]] = {
    "create_plan": {
        "description": "Tạo một kế hoạch mới từ mục tiêu và danh sách việc con.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "subtasks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["goal"],
            "additionalProperties": False,
        },
    },
    "get_plans": {
        "description": "Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu hoặc tiêu đề việc con.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "get_plan_detail": {
        "description": "Mở một kế hoạch theo danh tính.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
            },
            "required": ["plan_id"],
            "additionalProperties": False,
        },
    },
    "update_subtask": {
        "description": "Đặt trạng thái một việc con thành pending, done hoặc skipped.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "subtask_id": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["plan_id", "subtask_id", "status"],
            "additionalProperties": False,
        },
    },
    "add_subtask": {
        "description": "Thêm một việc con vào cuối một kế hoạch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "title": {"type": "string"},
            },
            "required": ["plan_id", "title"],
            "additionalProperties": False,
        },
    },
    "set_subtask_note": {
        "description": "Đặt hoặc xóa ghi chú của một việc con.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "subtask_id": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["plan_id", "subtask_id", "note"],
            "additionalProperties": False,
        },
    },
}

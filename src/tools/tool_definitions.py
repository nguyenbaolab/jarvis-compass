"""Catalog chín tool kế hoạch. Phiên bản là số nguyên, không phải chuỗi."""

DEFINITIONS_VERSION: int = 4

TOOL_DEFINITIONS: dict[str, dict[str, object]] = {
    "create_plan": {
        "description": "Tạo một kế hoạch mới từ mục tiêu và danh sách việc con. priority là high, medium hoặc low, chỉ đặt khi người dùng nói rõ. Mỗi việc có thể có scheduled_on dạng YYYY-MM-DD; effort là S, M hoặc L, chỉ đặt khi người dùng nói rõ. Ngày vượt thì chưa ghi; nói lại câu tool; chỉ đặt confirm true ở lượt sau.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "priority": {
                    "type": ["string", "null"],
                    "description": "high, medium hoặc low. Chỉ đặt khi người dùng nói rõ.",
                },
                "subtasks": {
                    "type": "array",
                    "description": "Mảng các đối tượng. Mỗi đối tượng có title; scheduled_on và effort không bắt buộc.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "scheduled_on": {
                                "type": ["string", "null"],
                                "description": "Ngày YYYY-MM-DD, hoặc null.",
                            },
                            "effort": {
                                "type": ["string", "null"],
                                "description": "S, M hoặc L. Chỉ đặt khi người dùng nói rõ.",
                            },
                        },
                        "required": ["title"],
                        "additionalProperties": False,
                    },
                },
                "confirm": {
                    "type": "boolean",
                    "description": "true chỉ ở lượt sau, khi tool này đã báo ngày vượt và chủ bot vẫn muốn ghi. Mặc định false.",
                },
                "load_moves": {
                    "type": "array",
                    "description": "Danh sách dời đã chốt. Không thêm việc.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "plan_id": {"type": "string"},
                            "subtask_id": {"type": "string"},
                            "scheduled_on": {
                                "type": "string",
                                "description": "Ngày YYYY-MM-DD.",
                            },
                        },
                        "required": ["plan_id", "subtask_id", "scheduled_on"],
                        "additionalProperties": False,
                    },
                },
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
        "description": "Thêm một việc con vào cuối một kế hoạch. scheduled_on dạng YYYY-MM-DD; effort là S, M hoặc L, chỉ đặt khi người dùng nói rõ. Ngày vượt thì chưa ghi; nói lại câu tool; chỉ đặt confirm true ở lượt sau.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "title": {"type": "string"},
                "scheduled_on": {
                    "type": ["string", "null"],
                    "description": "Ngày YYYY-MM-DD, hoặc null.",
                },
                "effort": {
                    "type": ["string", "null"],
                    "description": "S, M hoặc L. Chỉ đặt khi người dùng nói rõ.",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "true chỉ ở lượt sau, khi tool này đã báo ngày vượt và chủ bot vẫn muốn ghi. Mặc định false.",
                },
                "load_moves": {
                    "type": "array",
                    "description": "Danh sách dời đã chốt. Không thêm việc.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "plan_id": {"type": "string"},
                            "subtask_id": {"type": "string"},
                            "scheduled_on": {
                                "type": "string",
                                "description": "Ngày YYYY-MM-DD.",
                            },
                        },
                        "required": ["plan_id", "subtask_id", "scheduled_on"],
                        "additionalProperties": False,
                    },
                },
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
    "set_plan_priority": {
        "description": "Đặt ưu tiên của một kế hoạch thành high, medium hoặc low, hoặc null để xóa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "priority": {
                    "type": ["string", "null"],
                    "description": "high, medium hoặc low, hoặc null để xóa.",
                },
            },
            "required": ["plan_id", "priority"],
            "additionalProperties": False,
        },
    },
    "set_subtask_effort": {
        "description": "Đặt sức của một việc con thành S, M hoặc L, hoặc null để xóa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "subtask_id": {"type": "string"},
                "effort": {
                    "type": ["string", "null"],
                    "description": "S, M hoặc L. Chỉ đặt khi người dùng nói rõ.",
                },
            },
            "required": ["plan_id", "subtask_id", "effort"],
            "additionalProperties": False,
        },
    },
    "reschedule_subtasks": {
        "description": "Đặt hoặc dời ngày của các việc trong một kế hoạch. scheduled_on dạng YYYY-MM-DD, hoặc null để bỏ ngày. Thấy trùng hạn một kế hoạch khác thì chưa ghi; chỉ đặt confirm là true ở lượt sau, khi chủ bot đã đồng ý. Khi câu vừa báo vượt vừa báo trùng, một cờ đó bao cả hai.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "subtask_id": {"type": "string"},
                            "scheduled_on": {
                                "type": ["string", "null"],
                                "description": "Ngày YYYY-MM-DD, hoặc null.",
                            },
                        },
                        "required": ["subtask_id", "scheduled_on"],
                        "additionalProperties": False,
                    },
                },
                "reason": {"type": "string"},
                "confirm": {
                    "type": "boolean",
                    "description": "true chỉ khi chủ bot vừa đồng ý tiếp tục dời sau khi bạn báo trùng hạn. Mặc định false.",
                },
                "load_moves": {
                    "type": "array",
                    "description": "Danh sách dời đã chốt. Không thêm việc.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "plan_id": {"type": "string"},
                            "subtask_id": {"type": "string"},
                            "scheduled_on": {
                                "type": "string",
                                "description": "Ngày YYYY-MM-DD.",
                            },
                        },
                        "required": ["plan_id", "subtask_id", "scheduled_on"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["plan_id", "changes"],
            "additionalProperties": False,
        },
    },
}

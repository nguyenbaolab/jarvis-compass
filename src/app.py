"""App FastAPI, không phụ thuộc runtime Workers."""

from fastapi import FastAPI

import api
import api.routes_planning
from api.routes_telegram import router as telegram_router
import clients
import clients.telegram
import config
import config.settings
import core
import core.llm
import core.planning
import core.session
import db
import db.client
import db.models
import db.plan_store
import scheduler
import scheduler.checkin
import tools
import tools.base
import tools.plan_tools
import tools.tool_router

app = FastAPI()
app.include_router(telegram_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Xác nhận Worker + FastAPI khởi động được."""
    return {"status": "ok", "service": "jarvis-compass"}

@app.get("/spike/tz")
def spike_tz() -> dict[str, object]:
    """Đo ZoneInfo Europe/Helsinki trên Pyodide. Route tạm của nhánh spike."""

    import sys

    version = sys.version
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        zone = ZoneInfo("Europe/Helsinki")
        marks = (
            "2026-01-15T12:00Z",
            "2026-07-15T12:00Z",
            "2026-03-29T00:59Z",
            "2026-03-29T01:00Z",
            "2026-10-25T00:59Z",
            "2026-10-25T01:00Z",
        )
        offsets: list[int | float] = []
        for mark in marks:
            instant = datetime.fromisoformat(mark.replace("Z", "+00:00"))
            offset = instant.astimezone(zone).utcoffset()
            if offset is None:
                raise RuntimeError("không có độ lệch tại " + mark)
            hours = offset.total_seconds() / 3600
            offsets.append(int(hours) if hours.is_integer() else hours)
        return {"python": version, "offsets_hours": offsets}
    except Exception as exc:
        return {
            "python": version,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

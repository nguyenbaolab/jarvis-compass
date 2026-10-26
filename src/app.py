"""App FastAPI, không phụ thuộc runtime Workers."""

from fastapi import FastAPI

import api
import api.routes_planning
import api.routes_telegram
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


@app.get("/health")
def health() -> dict[str, str]:
    """Xác nhận Worker + FastAPI khởi động được."""
    return {"status": "ok", "service": "jarvis-compass"}

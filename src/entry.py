"""Entry Cloudflare Python Workers; file duy nhất được import workers."""

from workers import WorkerEntrypoint, asgi

from app import app
from scheduler.morning import run_morning


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if (request.headers.get("upgrade") or "").lower() == "websocket":
            return await asgi.websocket(app, request, self.env)
        return await asgi.fetch(app, request, self.env, self.ctx)

    async def scheduled(self, controller, env, ctx):
        await run_morning(self.env)

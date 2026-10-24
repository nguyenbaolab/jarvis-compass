"""Entry Cloudflare Python Workers; file duy nhất được import workers."""

from workers import WorkerEntrypoint, asgi

from app import app
from spike_cron import send_checkin


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)

    async def scheduled(self, controller, env, ctx):
        await send_checkin(self.env, controller.cron, controller.scheduledTime)

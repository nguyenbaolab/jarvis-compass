"""Entry Cloudflare Python Workers; file duy nhất được import workers."""

from workers import asgi
from app import app

Default = asgi.entrypoint(app)

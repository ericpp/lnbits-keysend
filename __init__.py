import asyncio

from fastapi import APIRouter

from .crud import db
from .tasks import watch_keysend_payments
from .views import keysend_generic_router
from .views_api import keysend_api_router
from .views_keysend import keysend_wellknown_router

keysend_static_files = [
    {
        "path": "/keysend/static",
        "name": "keysend_static",
    }
]

keysend_redirect_paths = [
    {
        "from_path": "/.well-known/keysend",
        "redirect_to_path": "/api/v1/well-known",
    }
]


keysend_ext: APIRouter = APIRouter(prefix="/keysend", tags=["keysend"])
keysend_ext.include_router(keysend_generic_router)
keysend_ext.include_router(keysend_api_router)
keysend_ext.include_router(keysend_wellknown_router)

scheduled_tasks: list[asyncio.Task] = []


def keysend_stop():
    for task in scheduled_tasks:
        task.cancel()


def keysend_start():
    from lnbits.tasks import create_permanent_unique_task

    task = create_permanent_unique_task("keysend", watch_keysend_payments)
    scheduled_tasks.append(task)


__all__ = [
    "db",
    "keysend_ext",
    "keysend_redirect_paths",
    "keysend_start",
    "keysend_static_files",
    "keysend_stop",
]

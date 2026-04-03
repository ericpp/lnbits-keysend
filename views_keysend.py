from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from .crud import get_keysend_entry_by_username, get_or_create_keysend_settings
from .models import CustomDataItem, KeysendWellKnownResponse

keysend_wellknown_router = APIRouter()


@keysend_wellknown_router.get("/api/v1/well-known/{username}")
async def keysend_wellknown(username: str) -> KeysendWellKnownResponse:
    entry = await get_keysend_entry_by_username(username)
    if not entry:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Keysend entry not found.",
        )

    settings = await get_or_create_keysend_settings()
    if not settings.node_pubkey:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Node pubkey not configured.",
        )

    return KeysendWellKnownResponse(
        status="OK",
        tag="keysend",
        pubkey=settings.node_pubkey,
        customData=[
            CustomDataItem(
                customKey=entry.custom_key,
                customValue=entry.custom_value,
            )
        ],
    )

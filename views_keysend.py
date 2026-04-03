from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from lnbits.wallets import get_funding_source

from .crud import get_keysend_entry_by_username
from .models import CustomDataItem, KeysendWellKnownResponse

keysend_wellknown_router = APIRouter()


async def get_node_pubkey() -> str:
    funding_source = get_funding_source()
    node_cls = funding_source.__node_cls__
    if not node_cls:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Active funding source does not expose a node pubkey.",
        )
    node = node_cls(funding_source)
    return await node.get_id()


@keysend_wellknown_router.get("/api/v1/well-known/{username}")
async def keysend_wellknown(username: str) -> KeysendWellKnownResponse:
    entry = await get_keysend_entry_by_username(username)
    if not entry:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Keysend entry not found.",
        )

    pubkey = await get_node_pubkey()

    return KeysendWellKnownResponse(
        status="OK",
        tag="keysend",
        pubkey=pubkey,
        customData=[
            CustomDataItem(
                customKey=entry.custom_key,
                customValue=entry.custom_value,
            )
        ],
    )

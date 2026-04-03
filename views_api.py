import json
import re
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query
from lnbits.core.crud import get_user, get_wallet
from lnbits.core.models import SimpleStatus, WalletTypeInfo
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)

from .crud import (
    create_keysend_entry,
    delete_keysend_entry,
    get_keysend_entry,
    get_keysend_entry_by_username,
    get_keysend_entries,
    get_keysend_entry_by_custom_data,
    get_received_keysend_payments,
    update_keysend_entry,
)
from .models import (
    CreateKeysendEntryData,
    KeysendEntry,
    PublicKeysendEntry,
    SendKeysendData,
)

keysend_api_router = APIRouter()


# ---------------------------------------------------------------------------
# Addresses CRUD
# ---------------------------------------------------------------------------


@keysend_api_router.get("/api/v1/entries", status_code=HTTPStatus.OK)
async def api_entries(
    key_info: WalletTypeInfo = Depends(require_invoice_key),
    all_wallets: bool = Query(False),
) -> list[KeysendEntry]:
    wallet_ids = [key_info.wallet.id]
    if all_wallets:
        user = await get_user(key_info.wallet.user)
        wallet_ids = user.wallet_ids if user else []
    return await get_keysend_entries(wallet_ids)


@keysend_api_router.get("/api/v1/entries/{entry_id}")
async def api_entry_retrieve(
    entry_id: str, key_info: WalletTypeInfo = Depends(require_invoice_key)
) -> KeysendEntry:
    entry = await get_keysend_entry(entry_id)
    if not entry:
        raise HTTPException(
            detail="Keysend address does not exist.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    entry_wallet = await get_wallet(entry.wallet)
    user = await get_user(key_info.wallet.user)
    admin_user = user.admin if user else False
    if not admin_user and entry_wallet and entry_wallet.user != key_info.wallet.user:
        raise HTTPException(
            detail="Not your keysend address.",
            status_code=HTTPStatus.FORBIDDEN,
        )
    return entry


@keysend_api_router.get(
    "/api/v1/entries/public/{entry_id}", response_model=PublicKeysendEntry
)
async def api_entry_public_retrieve(entry_id: str) -> KeysendEntry:
    entry = await get_keysend_entry(entry_id)
    if not entry:
        raise HTTPException(
            detail="Keysend address does not exist.",
            status_code=HTTPStatus.NOT_FOUND,
        )
    return entry


async def _check_username_exists(username: str) -> None:
    prev = await get_keysend_entry_by_username(username)
    if prev:
        raise HTTPException(
            detail="Username already taken.",
            status_code=HTTPStatus.CONFLICT,
        )


async def _check_custom_data_exists(custom_key: str, custom_value: str, entry_id: str | None = None) -> None:
    prev = await get_keysend_entry_by_custom_data(custom_key, custom_value)
    if prev and prev.id != entry_id:
        raise HTTPException(
            detail=f"The custom key '{custom_key}' and value '{custom_value}' combination is already in use.",
            status_code=HTTPStatus.CONFLICT,
        )


@keysend_api_router.post("/api/v1/entries", status_code=HTTPStatus.CREATED)
@keysend_api_router.put("/api/v1/entries/{entry_id}", status_code=HTTPStatus.OK)
async def api_entry_create_or_update(
    data: CreateKeysendEntryData,
    entry_id: str | None = None,
    key_info: WalletTypeInfo = Depends(require_admin_key),
) -> KeysendEntry:
    if data.webhook_headers:
        try:
            json.loads(data.webhook_headers)
        except ValueError as exc:
            raise HTTPException(
                detail="Invalid JSON in webhook_headers.",
                status_code=HTTPStatus.BAD_REQUEST,
            ) from exc

    if data.webhook_body:
        try:
            json.loads(data.webhook_body)
        except ValueError as exc:
            raise HTTPException(
                detail="Invalid JSON in webhook_body.",
                status_code=HTTPStatus.BAD_REQUEST,
            ) from exc

    if data.username and not re.match("^[a-z0-9-_.]{1,210}$", data.username):
        raise HTTPException(
            detail=f"Invalid username: {data.username}. "
            "Only letters a-z0-9-_. allowed, min 1 and max 210 characters!",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    if not data.custom_key:
        raise HTTPException(
            detail="custom_key is required.",
            status_code=HTTPStatus.BAD_REQUEST,
        )
    if not data.custom_value:
        raise HTTPException(
            detail="custom_value is required.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    await _check_custom_data_exists(data.custom_key, data.custom_value, entry_id)

    if not data.wallet:
        data.wallet = key_info.wallet.id

    new_wallet = await get_wallet(data.wallet)
    if not new_wallet:
        raise HTTPException(
            detail="Wallet does not exist.", status_code=HTTPStatus.FORBIDDEN
        )

    user = await get_user(key_info.wallet.user)
    admin_user = user.admin if user else False
    if not admin_user and new_wallet.user != key_info.wallet.user:
        raise HTTPException(
            detail="Not your keysend address.", status_code=HTTPStatus.FORBIDDEN
        )

    if entry_id:
        entry = await get_keysend_entry(entry_id)
        if not entry:
            raise HTTPException(
                detail="Keysend address does not exist.",
                status_code=HTTPStatus.NOT_FOUND,
            )
        if data.username and data.username != entry.username:
            await _check_username_exists(data.username)
        for k, v in data.dict().items():
            setattr(entry, k, v)
        entry = await update_keysend_entry(entry)
    else:
        if data.username:
            await _check_username_exists(data.username)
        entry = await create_keysend_entry(data)

    return entry


@keysend_api_router.delete("/api/v1/entries/{entry_id}", status_code=HTTPStatus.OK)
async def api_entry_delete(
    entry_id: str, key_info: WalletTypeInfo = Depends(require_admin_key)
) -> SimpleStatus:
    entry = await get_keysend_entry(entry_id)
    if not entry:
        raise HTTPException(
            detail="Keysend address does not exist.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    user = await get_user(key_info.wallet.user)
    admin_user = user.admin if user else False
    if not admin_user and entry.wallet != key_info.wallet.id:
        raise HTTPException(
            detail="Not your keysend address.", status_code=HTTPStatus.FORBIDDEN
        )

    await delete_keysend_entry(entry_id)
    return SimpleStatus(success=True, message="Deleted keysend address.")


# ---------------------------------------------------------------------------
# Send keysend
# ---------------------------------------------------------------------------


@keysend_api_router.post("/api/v1/send", status_code=HTTPStatus.OK)
async def api_send_keysend(
    data: SendKeysendData,
    key_info: WalletTypeInfo = Depends(require_admin_key),
) -> dict:
    if not data.destination or len(data.destination) != 66:
        raise HTTPException(
            detail="Invalid destination pubkey.",
            status_code=HTTPStatus.BAD_REQUEST,
        )
    if data.amount < 1:
        raise HTTPException(
            detail="Amount must be at least 1 sat.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    from .helpers import send_keysend

    try:
        result = await send_keysend(
            destination=data.destination,
            amount_sat=data.amount,
            custom_records=data.custom_records,
        )
    except Exception as exc:
        raise HTTPException(
            detail=f"Keysend payment failed: {exc!s}",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc

    return result


# ---------------------------------------------------------------------------
# Received payments
# ---------------------------------------------------------------------------


@keysend_api_router.get("/api/v1/payments", status_code=HTTPStatus.OK)
async def api_received_payments(
    key_info: WalletTypeInfo = Depends(require_invoice_key),
    all_wallets: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    wallet_ids = [key_info.wallet.id]
    if all_wallets:
        user = await get_user(key_info.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    payments = await get_received_keysend_payments(wallet_ids, limit, offset)
    return [
        {
            "payment_hash": p.payment_hash,
            "amount": p.sat,
            "memo": p.memo,
            "time": p.time.isoformat() if p.time else None,
            "keysend_entry": p.extra.get("keysend_entry", ""),
            "custom_records": p.extra.get("custom_records", {}),
        }
        for p in payments
    ]

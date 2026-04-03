from datetime import datetime, timezone

from lnbits.core.db import db as core_db
from lnbits.core.models import Payment
from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import CreateKeysendEntryData, KeysendEntry

db = Database("ext_keysend")


# ---------------------------------------------------------------------------
# Keysend addresses
# ---------------------------------------------------------------------------


async def create_keysend_entry(data: CreateKeysendEntryData) -> KeysendEntry:
    entry_id = urlsafe_short_hash()[:6]
    assert data.wallet, "Wallet is required"
    now = datetime.now(timezone.utc)

    entry = KeysendEntry(
        id=entry_id,
        wallet=data.wallet,
        description=data.description,
        username=data.username,
        custom_key=data.custom_key,
        custom_value=data.custom_value,
        domain=data.domain,
        webhook_url=data.webhook_url,
        webhook_headers=data.webhook_headers,
        webhook_body=data.webhook_body,
        created_at=now,
        updated_at=now,
    )

    await db.insert("keysend.entries", entry)
    return entry


async def get_keysend_entry(entry_id: str) -> KeysendEntry | None:
    return await db.fetchone(
        "SELECT * FROM keysend.entries WHERE id = :id",
        {"id": entry_id},
        KeysendEntry,
    )


async def get_keysend_entries(wallet_ids: str | list[str]) -> list[KeysendEntry]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM keysend.entries WHERE wallet IN ({q}) ORDER BY id",
        model=KeysendEntry,
    )


async def get_keysend_entry_by_username(username: str) -> KeysendEntry | None:
    return await db.fetchone(
        "SELECT * FROM keysend.entries WHERE username = :username",
        {"username": username},
        KeysendEntry,
    )


async def get_keysend_entry_by_custom_data(
    custom_key: str, custom_value: str
) -> KeysendEntry | None:
    return await db.fetchone(
        "SELECT * FROM keysend.entries "
        "WHERE custom_key = :custom_key AND custom_value = :custom_value",
        {"custom_key": custom_key, "custom_value": custom_value},
        KeysendEntry,
    )


async def update_keysend_entry(entry: KeysendEntry) -> KeysendEntry:
    entry.updated_at = datetime.now(timezone.utc)
    await db.update("keysend.entries", entry)
    return entry


async def delete_keysend_entry(entry_id: str) -> None:
    await db.execute(
        "DELETE FROM keysend.entries WHERE id = :id", {"id": entry_id}
    )


# ---------------------------------------------------------------------------
# Processed payment tracking
# ---------------------------------------------------------------------------


async def is_payment_processed(payment_hash: str) -> bool:
    row = await db.fetchone(
        "SELECT payment_hash FROM keysend.processed WHERE payment_hash = :h",
        {"h": payment_hash},
    )
    return row is not None


async def mark_payment_processed(payment_hash: str) -> None:
    await db.execute(
        "INSERT INTO keysend.processed (payment_hash) VALUES (:h)",
        {"h": payment_hash},
    )


# ---------------------------------------------------------------------------
# Received payments
# ---------------------------------------------------------------------------


async def get_received_keysend_payments(
    wallet_ids: list[str],
    limit: int = 50,
    offset: int = 0,
) -> list[Payment]:
    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await core_db.fetchall(
        f"""
        SELECT * FROM apipayments
        WHERE wallet_id IN ({q})
          AND tag = :tag
          AND amount > 0
          AND status = :status
        ORDER BY time DESC
        LIMIT {int(limit)} OFFSET {int(offset)}
        """,
        {"tag": "keysend", "status": "success"},
        Payment,
    )

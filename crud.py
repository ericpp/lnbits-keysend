from datetime import datetime, timezone

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import CreateKeysendEntryData, KeysendEntry, KeysendSettings

db = Database("ext_keysend")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


async def get_or_create_keysend_settings() -> KeysendSettings:
    settings = await db.fetchone(
        "SELECT * FROM keysend.settings LIMIT 1", model=KeysendSettings
    )
    if settings:
        return settings
    settings = KeysendSettings(node_pubkey="")
    await db.insert("keysend.settings", settings)
    return settings


async def update_keysend_settings(settings: KeysendSettings) -> KeysendSettings:
    await db.update("keysend.settings", settings, "")
    return settings


async def delete_keysend_settings() -> None:
    await db.execute("DELETE FROM keysend.settings")


# ---------------------------------------------------------------------------
# Keysend entries
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

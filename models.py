from datetime import datetime, timezone

from fastapi import Query
from pydantic import BaseModel, Field


class CreateKeysendEntryData(BaseModel):
    description: str
    wallet: str | None = None
    username: str | None = Query(None)
    custom_key: str = Query("696969")
    custom_value: str = Query("")
    domain: str | None = Query(None)
    webhook_url: str | None = Query(None)
    webhook_headers: str | None = Query(None)
    webhook_body: str | None = Query(None)


class KeysendEntry(BaseModel):
    id: str
    wallet: str
    description: str
    username: str | None = None
    custom_key: str
    custom_value: str
    domain: str | None = None
    webhook_url: str | None = None
    webhook_headers: str | None = None
    webhook_body: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PublicKeysendEntry(BaseModel):
    id: str
    username: str | None = None
    description: str
    domain: str | None = None


class CustomDataItem(BaseModel):
    customKey: str
    customValue: str


class KeysendWellKnownResponse(BaseModel):
    status: str = "OK"
    tag: str = "keysend"
    pubkey: str
    customData: list[CustomDataItem]


class SendKeysendData(BaseModel):
    destination: str
    amount: int
    custom_records: dict[str, str] | None = None

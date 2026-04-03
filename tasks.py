import asyncio
import json

import httpx
from lnbits.core.crud import get_payment, update_payment
from lnbits.core.models import Payment
from lnbits.core.services import create_invoice
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .crud import get_keysend_entry_by_custom_data
from .models import KeysendEntry


async def wait_for_paid_invoices():
    invoice_queue: asyncio.Queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_keysend")

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment):
    if not payment.extra:
        return

    # Already processed by this extension
    if payment.extra.get("keysend_routed"):
        return

    # Look for custom TLV records in the payment extra data.
    # Funding sources typically store keysend TLV records under
    # "custom_records" or "extra" in the payment extra dict.
    custom_records = payment.extra.get("custom_records", {})
    if not custom_records and payment.extra.get("tag") == "keysend":
        custom_records = payment.extra

    if not custom_records:
        return

    # Try to match any registered entry by iterating over custom records
    for custom_key, custom_value in custom_records.items():
        if custom_key in ("tag", "keysend_routed", "wh_status", "wh_success",
                          "wh_message", "wh_response"):
            continue

        entry = await get_keysend_entry_by_custom_data(
            str(custom_key), str(custom_value)
        )
        if not entry:
            continue

        logger.info(
            f"Keysend match: key={custom_key} value={custom_value} "
            f"-> wallet={entry.wallet} (entry={entry.id})"
        )

        await credit_wallet(payment, entry)
        await mark_payment_routed(payment.checking_id, entry.id)
        await send_webhook(payment, entry)
        return

    logger.debug(
        f"Keysend payment {payment.payment_hash} has custom records "
        "but no matching entry found."
    )


async def credit_wallet(payment: Payment, entry: KeysendEntry):
    """
    Credit the target wallet by creating an internal invoice and paying it
    from the admin/source wallet.
    """
    try:
        amount_sats = abs(payment.amount)
        if amount_sats < 1:
            return

        invoice = await create_invoice(
            wallet_id=entry.wallet,
            amount=amount_sats,
            memo=f"Keysend: {entry.description}",
            extra={
                "tag": "keysend",
                "keysend_routed": True,
                "keysend_entry": entry.id,
                "original_payment": payment.payment_hash,
            },
        )

        logger.info(
            f"Credited {amount_sats} sats to wallet {entry.wallet} "
            f"for keysend address {entry.id}"
        )

    except Exception as exc:
        logger.error(f"Failed to credit wallet for keysend address {entry.id}: {exc}")


async def mark_payment_routed(checking_id: str, entry_id: str) -> None:
    payment = await get_payment(checking_id)
    extra = payment.extra or {}
    extra["keysend_routed"] = True
    extra["keysend_entry"] = entry_id
    payment.extra = extra
    await update_payment(payment)


async def send_webhook(payment: Payment, entry: KeysendEntry):
    if not entry.webhook_url:
        return

    async with httpx.AsyncClient() as client:
        try:
            r: httpx.Response = await client.post(
                entry.webhook_url,
                json={
                    "payment_hash": payment.payment_hash,
                    "amount": payment.amount,
                    "keysend_entry": entry.id,
                    "custom_key": entry.custom_key,
                    "custom_value": entry.custom_value,
                    "body": (
                        json.loads(entry.webhook_body)
                        if entry.webhook_body
                        else ""
                    ),
                },
                headers=(
                    json.loads(entry.webhook_headers)
                    if entry.webhook_headers
                    else None
                ),
                timeout=6,
            )
            await mark_webhook_sent(
                payment.checking_id,
                r.status_code,
                r.is_success,
                r.reason_phrase,
                r.text,
            )
        except Exception as exc:
            logger.error(f"Keysend webhook error: {exc}")
            await mark_webhook_sent(
                payment.checking_id, -1, False, "Unexpected Error", str(exc)
            )


async def mark_webhook_sent(
    checking_id: str, status: int, is_success: bool, reason_phrase="", text=""
) -> None:
    payment = await get_payment(checking_id)
    extra = payment.extra or {}
    extra["wh_status"] = status
    extra["wh_success"] = is_success
    extra["wh_message"] = reason_phrase
    extra["wh_response"] = text
    payment.extra = extra
    await update_payment(payment)

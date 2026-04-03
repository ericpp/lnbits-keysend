import asyncio
import base64
import json

import httpx
from lnbits.core.services import create_invoice
from lnbits.settings import settings
from lnbits.wallets import get_funding_source
from loguru import logger

from .crud import (
    get_keysend_entry_by_custom_data,
    is_payment_processed,
    mark_payment_processed,
)
from .helpers import KEYSEND_PREIMAGE_TLV, get_recent_keysend_invoices
from .models import KeysendEntry


async def watch_keysend_payments():
    """
    Watch for incoming keysend payments. On startup, does a one-time
    catch-up poll to process any payments that arrived while offline,
    then subscribes to the node's real-time invoice stream.
    """
    await asyncio.sleep(3)

    logger.info("Keysend: running catch-up poll")
    try:
        invoices = await get_recent_keysend_invoices(limit=100)
        for inv in invoices:
            await _process_keysend_invoice(inv)
    except Exception as exc:
        logger.error(f"Keysend catch-up poll error: {exc}")

    wallet = get_funding_source()
    wallet_cls = type(wallet).__name__

    if wallet_cls in ("LndRestWallet", "LndWallet"):
        await _stream_lnd(wallet)
    elif wallet_cls in ("CoreLightningWallet", "CoreLightningRestWallet", "CLNRestWallet"):
        await _stream_cln(wallet)
    else:
        logger.warning(
            f"Keysend: {wallet_cls} does not support streaming, "
            "falling back to polling"
        )
        await _poll_fallback()


async def _stream_lnd(wallet):
    """
    Subscribe to LND's /v1/invoices/subscribe streaming endpoint.
    Same pattern as LNBits's own paid_invoices_stream, but we extract
    the full invoice data including custom TLV records from htlcs.
    """
    while settings.lnbits_running:
        try:
            url = f"{wallet.endpoint}/v1/invoices/subscribe"
            logger.info("Keysend: subscribing to LND invoice stream")
            async with wallet.client.stream("GET", url, timeout=None) as r:
                async for line in r.aiter_lines():
                    try:
                        inv = json.loads(line)["result"]
                    except Exception:
                        continue

                    if not inv.get("settled"):
                        continue

                    keysend_inv = _parse_lnd_invoice(inv)
                    if keysend_inv:
                        await _process_keysend_invoice(keysend_inv)

        except Exception as exc:
            logger.warning(
                f"Keysend: lost connection to LND invoice stream: "
                f"'{exc}', retrying in 5 seconds"
            )
            await asyncio.sleep(5)


def _parse_lnd_invoice(inv: dict) -> dict | None:
    custom_records: dict[str, str] = {}
    for htlc in inv.get("htlcs", []):
        for k, v in htlc.get("custom_records", {}).items():
            if k == KEYSEND_PREIMAGE_TLV:
                continue
            try:
                custom_records[k] = base64.b64decode(v).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                custom_records[k] = v

    if not custom_records:
        return None

    return {
        "payment_hash": base64.b64decode(inv["r_hash"]).hex(),
        "amount_sat": int(inv.get("value", 0)),
        "custom_records": custom_records,
        "memo": inv.get("memo", ""),
    }


async def _stream_cln(wallet):
    """
    CLN doesn't have a long-lived HTTP stream like LND.
    Use waitanyinvoice via the REST or socket interface,
    which blocks until the next invoice settles.
    """
    last_pay_index = None

    while settings.lnbits_running:
        try:
            if hasattr(wallet, "client"):
                params = {}
                if last_pay_index is not None:
                    params["lastpay_index"] = last_pay_index
                r = await wallet.client.post(
                    f"{wallet.endpoint}/v1/waitanyinvoice",
                    json=params,
                    timeout=None,
                )
                r.raise_for_status()
                inv = r.json()
            elif hasattr(wallet, "ln"):
                kwargs = {}
                if last_pay_index is not None:
                    kwargs["lastpay_index"] = last_pay_index
                inv = wallet.ln.waitanyinvoice(**kwargs)
            else:
                logger.warning("Keysend: CLN wallet has no usable interface")
                await _poll_fallback()
                return

            if inv.get("status") != "paid":
                continue

            last_pay_index = inv.get("pay_index", last_pay_index)

            extratlvs = inv.get("extratlvs", {})
            custom_records = {}
            for k, v in extratlvs.items():
                if str(k) == KEYSEND_PREIMAGE_TLV:
                    continue
                custom_records[str(k)] = str(v)

            if custom_records:
                await _process_keysend_invoice({
                    "payment_hash": inv.get("payment_hash", ""),
                    "amount_sat": inv.get("amount_received_msat", 0) // 1000,
                    "custom_records": custom_records,
                    "memo": inv.get("description", ""),
                })

        except Exception as exc:
            logger.warning(
                f"Keysend: CLN waitanyinvoice error: '{exc}', "
                "retrying in 5 seconds"
            )
            await asyncio.sleep(5)


async def _poll_fallback():
    """Fallback for backends that don't support streaming."""
    logger.info("Keysend: using polling fallback (every 10s)")
    while settings.lnbits_running:
        try:
            invoices = await get_recent_keysend_invoices(limit=50)
            for inv in invoices:
                await _process_keysend_invoice(inv)
        except Exception as exc:
            logger.error(f"Keysend poll error: {exc}")
        await asyncio.sleep(10)


# ---------------------------------------------------------------------------
# Invoice processing (shared by all backends)
# ---------------------------------------------------------------------------


async def _process_keysend_invoice(inv: dict) -> None:
    payment_hash = inv["payment_hash"]

    if await is_payment_processed(payment_hash):
        return

    custom_records = inv.get("custom_records", {})
    for custom_key, custom_value in custom_records.items():
        entry = await get_keysend_entry_by_custom_data(
            str(custom_key), str(custom_value)
        )
        if not entry:
            continue

        logger.info(
            f"Keysend match: key={custom_key} value={custom_value} "
            f"-> wallet={entry.wallet} (entry={entry.id})"
        )

        amount_sat = inv.get("amount_sat", 0)
        if amount_sat < 1:
            logger.warning(f"Keysend {payment_hash}: amount too small ({amount_sat})")
            await mark_payment_processed(payment_hash)
            return

        await credit_wallet(payment_hash, amount_sat, entry)
        await mark_payment_processed(payment_hash)
        await send_webhook(payment_hash, amount_sat, entry)
        return

    await mark_payment_processed(payment_hash)


async def credit_wallet(payment_hash: str, amount_sat: int, entry: KeysendEntry):
    try:
        await create_invoice(
            wallet_id=entry.wallet,
            amount=amount_sat,
            memo=f"Keysend: {entry.description}",
            extra={
                "tag": "keysend",
                "keysend_routed": True,
                "keysend_entry": entry.id,
                "original_payment": payment_hash,
            },
        )

        logger.info(
            f"Credited {amount_sat} sats to wallet {entry.wallet} "
            f"for keysend address {entry.id}"
        )

    except Exception as exc:
        logger.error(f"Failed to credit wallet for keysend address {entry.id}: {exc}")


async def send_webhook(payment_hash: str, amount_sat: int, entry: KeysendEntry):
    if not entry.webhook_url:
        return

    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                entry.webhook_url,
                json={
                    "payment_hash": payment_hash,
                    "amount": amount_sat,
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
        except Exception as exc:
            logger.error(f"Keysend webhook error: {exc}")

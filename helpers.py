import base64
import hashlib
import os

from loguru import logger
from lnbits.wallets import get_funding_source


KEYSEND_PREIMAGE_TLV = "5482373484"


async def send_keysend(
    destination: str,
    amount_sat: int,
    custom_records: dict[str, str] | None = None,
) -> dict:
    wallet = get_funding_source()
    wallet_cls = type(wallet).__name__

    if wallet_cls in ("LndRestWallet", "LndWallet"):
        return await _send_keysend_lnd_rest(wallet, destination, amount_sat, custom_records)
    if wallet_cls in ("CoreLightningWallet", "CoreLightningRestWallet", "CLNRestWallet"):
        return await _send_keysend_cln(wallet, destination, amount_sat, custom_records)

    raise ValueError(
        f"Keysend sending is not supported by the {wallet_cls} backend. "
        "Supported backends: LND (REST/gRPC), Core Lightning (REST/socket)."
    )


async def get_recent_keysend_invoices(limit: int = 50) -> list[dict]:
    """
    Query the Lightning node directly for recently settled invoices
    that contain custom TLV records (keysend payments).
    Returns a list of dicts with payment_hash, amount_sat, and custom_records.
    """
    wallet = get_funding_source()
    wallet_cls = type(wallet).__name__

    if wallet_cls in ("LndRestWallet", "LndWallet"):
        return await _get_keysend_invoices_lnd(wallet, limit)
    if wallet_cls in ("CoreLightningWallet", "CoreLightningRestWallet", "CLNRestWallet"):
        return await _get_keysend_invoices_cln(wallet, limit)

    logger.warning(f"Keysend polling not supported for {wallet_cls}")
    return []


async def _get_keysend_invoices_lnd(wallet, limit: int) -> list[dict]:
    r = await wallet.client.get(
        f"{wallet.endpoint}/v1/invoices",
        params={
            "reversed": True,
            "num_max_invoices": limit,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    results = []
    for inv in data.get("invoices", []):
        if not inv.get("settled"):
            continue

        custom_records: dict[str, str] = {}
        for htlc in inv.get("htlcs", []):
            for k, v in htlc.get("custom_records", {}).items():
                if k == KEYSEND_PREIMAGE_TLV:
                    continue
                try:
                    custom_records[k] = base64.b64decode(v).decode("utf-8", errors="replace")
                except Exception:
                    custom_records[k] = v

        if not custom_records:
            continue

        payment_hash = base64.b64decode(inv["r_hash"]).hex()
        amount_sat = int(inv.get("value", 0))

        results.append({
            "payment_hash": payment_hash,
            "amount_sat": amount_sat,
            "custom_records": custom_records,
            "memo": inv.get("memo", ""),
        })

    return results


async def _get_keysend_invoices_cln(wallet, limit: int) -> list[dict]:
    if hasattr(wallet, "client"):
        try:
            r = await wallet.client.post(
                f"{wallet.endpoint}/v1/listinvoices",
                json={"limit": limit},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            logger.warning(f"CLN listinvoices failed: {exc}")
            return []
    elif hasattr(wallet, "ln"):
        try:
            data = wallet.ln.listinvoices()
        except Exception as exc:
            logger.warning(f"CLN listinvoices failed: {exc}")
            return []
    else:
        return []

    results = []
    for inv in data.get("invoices", []):
        if inv.get("status") != "paid":
            continue

        extratlvs = inv.get("extratlvs", {})
        if not extratlvs:
            continue

        custom_records = {}
        for k, v in extratlvs.items():
            if str(k) == KEYSEND_PREIMAGE_TLV:
                continue
            custom_records[str(k)] = str(v)

        if not custom_records:
            continue

        results.append({
            "payment_hash": inv.get("payment_hash", ""),
            "amount_sat": inv.get("amount_received_msat", 0) // 1000,
            "custom_records": custom_records,
            "memo": inv.get("description", ""),
        })

    return results


# ---------------------------------------------------------------------------
# Send keysend
# ---------------------------------------------------------------------------


async def _send_keysend_lnd_rest(wallet, destination: str, amount_sat: int, custom_records: dict[str, str] | None) -> dict:
    preimage = os.urandom(32)
    payment_hash = hashlib.sha256(preimage).digest()

    dest_custom_records = {
        KEYSEND_PREIMAGE_TLV: base64.b64encode(preimage).decode(),
    }
    if custom_records:
        for k, v in custom_records.items():
            dest_custom_records[k] = base64.b64encode(v.encode()).decode()

    req = {
        "dest": base64.b64encode(bytes.fromhex(destination)).decode(),
        "amt": amount_sat,
        "payment_hash": base64.b64encode(payment_hash).decode(),
        "timeout_seconds": 60,
        "fee_limit_sat": max(amount_sat // 100, 10),
        "dest_custom_records": dest_custom_records,
        "no_inflight_updates": True,
    }

    r = await wallet.client.post(
        url=f"{wallet.endpoint}/v2/router/send",
        json=req,
        timeout=None,
    )
    r.raise_for_status()
    data = r.json()

    result = data.get("result", data)
    status = result.get("status", "UNKNOWN")
    if status == "SUCCEEDED":
        return {
            "payment_hash": result.get("payment_hash", payment_hash.hex()),
            "fee_msat": abs(int(result.get("fee_msat", 0))),
            "status": "ok",
        }
    if status == "FAILED":
        reason = result.get("failure_reason", "unknown")
        raise ValueError(f"Payment failed: {reason}")

    logger.warning(f"Keysend payment status: {status}")
    return {
        "payment_hash": payment_hash.hex(),
        "status": status.lower(),
    }


async def _send_keysend_cln(wallet, destination: str, amount_sat: int, custom_records: dict[str, str] | None) -> dict:
    if hasattr(wallet, "ln") and hasattr(wallet.ln, "keysend"):
        extra_tlvs = None
        if custom_records:
            extra_tlvs = [{"type": int(k), "value": v} for k, v in custom_records.items()]

        response = wallet.ln.keysend(
            destination=destination,
            amount_msat=f"{amount_sat * 1000}msat",
            extratlvs=extra_tlvs,
        )
        return {
            "payment_hash": response.get("payment_hash", ""),
            "status": "ok",
        }

    if hasattr(wallet, "client"):
        payload = {
            "destination": destination,
            "amount_msat": amount_sat * 1000,
        }
        if custom_records:
            payload["extratlvs"] = {int(k): v for k, v in custom_records.items()}

        r = await wallet.client.post(
            url=f"{wallet.endpoint}/v1/keysend",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "payment_hash": data.get("payment_hash", ""),
            "status": "ok",
        }

    raise ValueError("CLN wallet does not expose a usable keysend interface.")

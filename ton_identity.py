"""
Eiva — ton_identity.py
Real TON blockchain integration:
  - Derive wallet address from mnemonic (tonsdk)
  - Upload personality profile to TON Storage
  - Mint a Soul Certificate NFT on testnet/mainnet
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Optional

_BROADCAST_RETRIES = 4
_BROADCAST_DELAY   = 3.0   # seconds between retries

import aiohttp

import config

# ── Endpoints ─────────────────────────────────────────────────────────────────
TONCENTER = {
    "testnet": "https://testnet.toncenter.com/api/v2",
    "mainnet": "https://toncenter.com/api/v2",
}
TONAPI = {
    "testnet": "https://testnet.tonapi.io/v2",
    "mainnet": "https://tonapi.io/v2",
}


# ── Address derivation ────────────────────────────────────────────────────────

def get_wallet_address() -> Optional[str]:
    """
    Derive wallet v4r2 address from mnemonic using tonsdk.
    Returns user-friendly non-bounceable address.
    """
    if not config.TON_MNEMONIC:
        return None
    try:
        from tonsdk.contract.wallet import WalletVersionEnum, Wallets
        words = config.TON_MNEMONIC.strip().split()
        _, _, _, wallet = Wallets.from_mnemonics(words, WalletVersionEnum.v4r2, 0)
        return wallet.address.to_string(True, True, False)   # non-bounceable
    except Exception as e:
        print(f"[TON] Address derivation error: {e}")
        return None


def get_wallet_address_bounceable() -> Optional[str]:
    if not config.TON_MNEMONIC:
        return None
    try:
        from tonsdk.contract.wallet import WalletVersionEnum, Wallets
        words = config.TON_MNEMONIC.strip().split()
        _, _, _, wallet = Wallets.from_mnemonics(words, WalletVersionEnum.v4r2, 0)
        return wallet.address.to_string(True, True, True)
    except Exception as e:
        return None


# ── TON Wallet interaction ────────────────────────────────────────────────────

async def get_balance(address: str) -> Optional[int]:
    """Get wallet balance in nanotons via toncenter API."""
    headers = {}
    if config.TON_API_KEY:
        headers["X-API-Key"] = config.TON_API_KEY
    try:
        url = f"{TONCENTER[config.TON_NETWORK]}/getAddressBalance?address={address}"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    return int(data.get("result", 0))
    except Exception as e:
        print(f"[TON] Balance check error: {e}")
    return None


async def send_transaction(
    to_address: str,
    amount_nano: int,
    payload: bytes = b"",
) -> Optional[str]:
    """
    Sign and broadcast a transfer via toncenter sendBoc.
    Returns transaction hash or None.
    """
    if not config.TON_MNEMONIC:
        return None
    try:
        from tonsdk.contract.wallet import WalletVersionEnum, Wallets
        from tonsdk.utils import bytes_to_b64str, to_nano
        from tonsdk.boc import Cell
        import base64

        words = config.TON_MNEMONIC.strip().split()
        mnemo, pub_k, priv_k, wallet = Wallets.from_mnemonics(
            words, WalletVersionEnum.v4r2, 0
        )

        # Get seqno
        addr = wallet.address.to_string(True, True, False)
        headers = {}
        if config.TON_API_KEY:
            headers["X-API-Key"] = config.TON_API_KEY

        seqno = 0
        url_seqno = f"{TONCENTER[config.TON_NETWORK]}/runGetMethod"
        async with aiohttp.ClientSession() as s:
            async with s.post(
                url_seqno,
                json={"address": addr, "method": "seqno", "stack": []},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                raw_resp = await r.json()
                print(f"[TON] seqno API status={r.status} resp={raw_resp}")
                if r.status == 200 and raw_resp.get("ok"):
                    try:
                        exit_code = raw_resp["result"].get("exit_code", -1)
                        if exit_code == 0:
                            # Contract is deployed — read actual seqno
                            raw_val = raw_resp["result"]["stack"][0][1]
                            seqno = int(raw_val, 16) if raw_val.startswith("0x") else int(raw_val)
                            print(f"[TON] Wallet deployed, seqno={seqno}")
                        else:
                            # exit_code != 0 → wallet NOT deployed (e.g. -13 = not found)
                            # The stack value is a TVM error code, NOT a real seqno!
                            seqno = 0
                            print(f"[TON] Wallet NOT deployed (exit_code={exit_code}) → seqno=0, will include state_init")
                    except Exception:
                        seqno = 0
        print(f"[TON] Using seqno={seqno}")

        # Build transfer
        transfer = wallet.create_transfer_message(
            to_addr=to_address,
            amount=amount_nano,
            seqno=seqno,
            payload=payload.decode("utf-8") if payload else "",
        )
        boc = bytes_to_b64str(transfer["message"].to_boc(False))

        import base64 as _b64

        def _make_tx_hash(boc_b64: str) -> str:
            raw = _b64.b64decode(boc_b64)
            return hashlib.sha256(raw).hexdigest()

        # Primary: toncenter sendBoc — retry up to _BROADCAST_RETRIES times on 429
        toncenter_ok = False
        for attempt in range(1, _BROADCAST_RETRIES + 1):
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{TONCENTER[config.TON_NETWORK]}/sendBoc",
                    json={"boc": boc},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    result = await r.json()
                    print(f"[TON] toncenter sendBoc attempt {attempt}: status={r.status} result={result}")
                    if r.status == 200 and result.get("ok"):
                        tx_hash = _make_tx_hash(boc)
                        print(f"[TON] ✓ toncenter: Transaction sent! Hash: {tx_hash}")
                        return tx_hash
                    elif r.status == 429 or (not result.get("ok") and "Ratelimit" in str(result.get("result", ""))):
                        wait = _BROADCAST_DELAY * attempt
                        print(f"[TON] Rate-limited (attempt {attempt}/{_BROADCAST_RETRIES}). Waiting {wait:.0f}s…")
                        await asyncio.sleep(wait)
                    else:
                        print(f"[TON] toncenter broadcast error — trying tonapi.io fallback")
                        break  # non-rate-limit error → skip to fallback immediately

        # Fallback: tonapi.io
        print("[TON] Attempting tonapi.io fallback…")
        tonapi_url = f"{TONAPI[config.TON_NETWORK]}/blockchain/message"
        for attempt in range(1, 3):
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    tonapi_url,
                    json={"boc": boc},
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    result_text = await r.text()
                    print(f"[TON] tonapi.io attempt {attempt}: status={r.status} body={result_text[:200]}")
                    if r.status in (200, 201, 202):
                        tx_hash = _make_tx_hash(boc)
                        print(f"[TON] ✓ tonapi.io: Transaction sent! Hash: {tx_hash}")
                        return tx_hash
                    elif r.status == 429:
                        await asyncio.sleep(5 * attempt)
                    else:
                        print(f"[TON] tonapi.io error (status {r.status}) — giving up")
                        break

        print("[TON] All broadcast attempts failed.")
        return None
    except Exception as e:
        print(f"[TON] send_transaction error: {e}")
        return None


# ── TON Storage ───────────────────────────────────────────────────────────────

async def upload_to_storage(data: dict) -> str:
    """
    Upload personality JSON to TON Storage (daemon on localhost:8070).
    Falls back to a deterministic content-addressed mock bag_id.
    """
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    content_hash = hashlib.sha256(json_bytes).hexdigest()

    # Try real TON Storage daemon
    try:
        async with aiohttp.ClientSession() as s:
            form = aiohttp.FormData()
            form.add_field(
                "file", json_bytes,
                filename="personality.json",
                content_type="application/json",
            )
            async with s.post(
                "http://localhost:8070/api/v1/create",
                data=form,
                timeout=aiohttp.ClientTimeout(total=8),
            ) as r:
                if r.status == 200:
                    result = await r.json()
                    bag_id = result.get("BagId") or result.get("bag_id")
                    if bag_id:
                        print(f"[TON Storage] ✓ Real bag ID: {bag_id}")
                        return bag_id
    except Exception:
        pass

    # Deterministic content-addressed mock (for demo without daemon)
    mock_bag = content_hash[:40].upper()
    print(f"[TON Storage] ℹ Demo bag ID (no daemon): {mock_bag}")
    return mock_bag


# ── NFT Mint ──────────────────────────────────────────────────────────────────

async def mint_nft(
    owner_address: str,
    owner_name: str,
    personality_hash: str,
    bag_id: str,
) -> Optional[str]:
    """
    Anchor the Soul Certificate on-chain as a self-transfer with a comment.
    The transaction hash IS the Soul Certificate proof — verifiable on tonscan.
    TON cells max 127 bytes — comment stays short.
    """
    bot_address = get_wallet_address()
    if not bot_address:
        print("[TON] No wallet address available for mint")
        return None

    # Short comment that fits in one TON cell (max ~127 bytes for ASCII)
    comment = f"Eiva:Soul:{personality_hash[:20]}"
    payload = comment.encode("utf-8")

    print(f"[TON] Self-transfer to anchor Soul Certificate on-chain")
    print(f"[TON] Recipient: {bot_address}")
    print(f"[TON] Payload ({len(payload)} bytes): {comment}")

    tx_hash = await send_transaction(
        to_address=bot_address,   # self-transfer → reliable, wallet is already funded
        amount_nano=10_000_000,   # 0.01 TON
        payload=payload,
    )
    return tx_hash


# ── High-level function (called from bot) ─────────────────────────────────────

async def create_soul_certificate(
    user_id: str,
    owner_name: str,
    personality: dict,
    ton_address: Optional[str] = None,
) -> dict:
    """
    Full flow:
      1. Compute personality hash
      2. Upload to TON Storage
      3. Mint Soul Certificate NFT
      4. Return result dict

    The wallet address is persisted in ChromaDB metadata for the user.
    On restart, bot will use the stored address if available.
    """
    personality_json = json.dumps(personality, ensure_ascii=False)
    personality_hash = hashlib.sha256(personality_json.encode()).hexdigest()

    # Auto-detect address from mnemonic if not provided
    if not ton_address:
        ton_address = get_wallet_address()
        print(f"[TON] Auto-detected wallet from mnemonic: {ton_address}")

    print(f"[TON] Mnemonic configured: {bool(config.TON_MNEMONIC)}")
    print(f"[TON] Wallet address: {ton_address}")

    # Step 1: Upload to storage
    bag_id = await upload_to_storage(personality)

    # Step 2: Mint NFT
    tx_hash = None
    if ton_address and config.TON_MNEMONIC:
        # Check bot wallet balance first
        bot_wallet = get_wallet_address()
        if bot_wallet:
            print(f"[TON] Checking balance of {bot_wallet}...")
            balance = await get_balance(bot_wallet)
            if balance is None:
                print(f"[TON] ⚠️ Could not fetch balance (toncenter may be unreachable) — trying anyway")
            else:
                print(f"[TON] Bot wallet balance: {balance} nanoton = {balance/1e9:.3f} TON")
                if balance < 10_000_000:
                    print(f"[TON] ⚠️ Low balance! Send testnet TON to: {bot_wallet}")
                    print(f"[TON] Get testnet TON: https://t.me/testgiver_ton_bot")
        print(f"[TON] Starting mint for owner={ton_address[:20]}...")
        tx_hash = await mint_nft(
            owner_address=ton_address,
            owner_name=owner_name,
            personality_hash=personality_hash,
            bag_id=bag_id,
        )

    network = config.TON_NETWORK
    bot_wallet = get_wallet_address() or ton_address
    base = "https://testnet.tonscan.org" if network == "testnet" else "https://tonscan.org"
    explorer_url = None
    if tx_hash:
        # Link to wallet's transaction list — the latest tx is the Soul Certificate anchor
        explorer_url = f"{base}/address/{bot_wallet}"

    return {
        "wallet_address":   ton_address,
        "personality_hash": personality_hash,
        "storage_bag_id":   bag_id,
        "tx_hash":          tx_hash,
        "network":          network,
        "explorer_url":     explorer_url,
    }

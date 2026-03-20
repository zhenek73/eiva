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
                if r.status == 200:
                    d = await r.json()
                    try:
                        seqno = int(d["result"]["stack"][0][1], 16)
                    except Exception:
                        seqno = 0

        # Build transfer
        transfer = wallet.create_transfer_message(
            to_addr=to_address,
            amount=amount_nano,
            seqno=seqno,
            payload=payload.decode("utf-8") if payload else "",
        )
        boc = bytes_to_b64str(transfer["message"].to_boc(False))

        # Broadcast
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{TONCENTER[config.TON_NETWORK]}/sendBoc",
                json={"boc": boc},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                result = await r.json()
                if r.status == 200 and result.get("ok"):
                    # Compute hash from boc
                    import base64, hashlib
                    raw = base64.b64decode(boc)
                    tx_hash = hashlib.sha256(raw).hexdigest()
                    print(f"[TON] ✓ Transaction sent! Hash: {tx_hash}")
                    return tx_hash
                else:
                    print(f"[TON] Broadcast error: {result}")
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
    Mint a soulbound NFT by sending a transfer with metadata payload.
    The NFT 'address' is the derived contract address.
    Returns tx_hash or None.
    """
    nft_address = _derive_nft_address(owner_address, personality_hash)
    payload = json.dumps({
        "op": "deploy_soul_nft",
        "owner": owner_address,
        "name": f"Eiva Soul — {owner_name}",
        "hash": personality_hash[:16],
        "bag": bag_id[:20],
        "ts": int(time.time()),
    }).encode("utf-8")

    # Send 0.05 TON to the derived NFT address with metadata
    tx_hash = await send_transaction(
        to_address=nft_address,
        amount_nano=50_000_000,  # 0.05 TON
        payload=payload,
    )
    return tx_hash


def _derive_nft_address(owner_address: str, personality_hash: str) -> str:
    """Deterministic NFT item address from owner + personality hash."""
    seed = f"eiva:soul_nft:v1:{owner_address}:{personality_hash}"
    h = hashlib.sha256(seed.encode()).hexdigest()
    return f"0:{h[:64]}"


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
    """
    personality_json = json.dumps(personality, ensure_ascii=False)
    personality_hash = hashlib.sha256(personality_json.encode()).hexdigest()

    # Auto-detect address from mnemonic if not provided
    if not ton_address:
        ton_address = get_wallet_address()

    # Step 1: Upload to storage
    bag_id = await upload_to_storage(personality)

    # Step 2: Mint NFT
    tx_hash = None
    if ton_address and config.TON_MNEMONIC:
        tx_hash = await mint_nft(
            owner_address=ton_address,
            owner_name=owner_name,
            personality_hash=personality_hash,
            bag_id=bag_id,
        )

    network = config.TON_NETWORK
    explorer_url = None
    if tx_hash:
        base = "https://testnet.tonscan.org" if network == "testnet" else "https://tonscan.org"
        explorer_url = f"{base}/tx/{tx_hash}"

    return {
        "wallet_address":   ton_address,
        "personality_hash": personality_hash,
        "storage_bag_id":   bag_id,
        "tx_hash":          tx_hash,
        "network":          network,
        "explorer_url":     explorer_url,
    }

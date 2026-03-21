"""
Eiva — nft_contract.py

Real TON NFT (Soulbound, TEP-85) deployment flow:
  1. Create metadata JSON (name, description, image, attributes)
  2. Upload metadata to GitHub raw → permanent public URL
  3. Build NFT item StateInit (tonutils bytecode + pytoniq_core cells)
  4. Derive NFT address from StateInit hash
  5. Deploy via tonsdk create_transfer_message with state_init param
"""

import asyncio
import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Optional

import aiohttp

import config

# ── Null address (TON zero address for "no collection") ───────────────────────
_ZERO_ADDR = "UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJKZ"

# ── GitHub hosting for metadata ───────────────────────────────────────────────

async def upload_metadata_to_github(
    filename: str,
    content: dict,
) -> Optional[str]:
    """
    Create/update a file in the GitHub repo and return the raw URL.
    Uses GITHUB_TOKEN from config (already in .env).
    """
    if not config.GITHUB_TOKEN:
        print("[NFT] No GITHUB_TOKEN — cannot upload metadata to GitHub")
        return None

    json_bytes = json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")
    b64_content = base64.b64encode(json_bytes).decode()

    url = f"https://api.github.com/repos/zhenek73/eiva/contents/metadata/{filename}"
    headers = {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    # Check if file already exists (need its SHA to update)
    sha = None
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                existing = await r.json()
                sha = existing.get("sha")

    # Create or update
    payload = {
        "message": f"chore: add NFT metadata {filename}",
        "content": b64_content,
    }
    if sha:
        payload["sha"] = sha

    async with aiohttp.ClientSession() as s:
        async with s.put(
            url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as r:
            if r.status in (200, 201):
                raw_url = (
                    f"https://raw.githubusercontent.com/zhenek73/eiva/main/metadata/{filename}"
                )
                print(f"[NFT] Metadata uploaded: {raw_url}")
                return raw_url
            else:
                err = await r.text()
                print(f"[NFT] GitHub upload failed {r.status}: {err[:200]}")
                return None


# ── Metadata builder ──────────────────────────────────────────────────────────

def build_metadata(
    owner_name: str,
    personality_hash: str,
    personality: dict,
    avatar_url: Optional[str] = None,
) -> dict:
    """Build TEP-64 compliant NFT metadata JSON."""
    if not avatar_url:
        seed = hashlib.md5(owner_name.encode()).hexdigest()[:8]
        avatar_url = (
            f"https://api.dicebear.com/9.x/pixel-art/png"
            f"?seed={seed}&size=256&backgroundColor=1a1a2e"
        )

    style = personality.get("communication_style", "unique")
    tone  = personality.get("emotional_tone", "authentic")
    topics = ", ".join(personality.get("key_topics", [])[:3])

    return {
        "name": f"Eiva Soul — {owner_name}",
        "description": (
            f"AI Digital Twin Soul Certificate for {owner_name}. "
            f"Personality: {tone}, {style}. Topics: {topics}. "
            f"Anchored on TON blockchain by Eiva Protocol."
        ),
        "image": avatar_url,
        "attributes": [
            {"trait_type": "Personality Hash", "value": personality_hash[:20]},
            {"trait_type": "Communication Style", "value": style},
            {"trait_type": "Emotional Tone", "value": tone},
            {"trait_type": "Network", "value": config.TON_NETWORK},
            {"trait_type": "Protocol", "value": "Eiva v1"},
            {"trait_type": "Certificate Type", "value": "Soulbound"},
            {"trait_type": "Creation Date", "value": time.strftime("%Y-%m-%d")},
        ],
    }


# ── StateInit builder ─────────────────────────────────────────────────────────

def build_nft_state_init(
    owner_address_str: str,
    metadata_url: str,
    index: int = 0,
) -> tuple:
    """
    Build the Soulbound NFT item StateInit (TEP-85).
    Returns (state_init_tonsdk_cell, nft_address_str).
    """
    from tonutils.contracts.codes import CONTRACT_CODES
    from tonutils.contracts.versions import ContractVersion
    from tonutils.utils import to_cell as tonutils_to_cell
    from pytoniq_core import Address, StateInit, begin_cell
    from tonsdk.boc import Cell as TCell

    # Contract code from tonutils (battle-tested bytecode)
    code_cell = tonutils_to_cell(CONTRACT_CODES[ContractVersion.NFTItemSoulbound])

    owner_addr = Address(owner_address_str)
    null_addr  = Address(_ZERO_ADDR)

    # Off-chain content: just the metadata URL as snake string
    content_cell = begin_cell().store_snake_string(metadata_url).end_cell()

    # TEP-85 soulbound data layout:
    # index:uint64 collection:addr owner:addr content:^Cell authority:addr revoked_at:uint64
    data_cell = (
        begin_cell()
        .store_uint(index, 64)
        .store_address(null_addr)    # no collection (individual NFT)
        .store_address(owner_addr)   # owner
        .store_ref(content_cell)     # metadata ref
        .store_address(owner_addr)   # authority = owner (can revoke)
        .store_uint(0, 64)           # revoked_at = 0
        .end_cell()
    )

    # StateInit → serialize → derive address from hash
    si = StateInit(code=code_cell, data=data_cell)
    si_cell = si.serialize()
    nft_address = "0:" + si_cell.hash.hex()

    # Convert to tonsdk Cell (needed for create_transfer_message)
    si_boc = si_cell.to_boc()
    tonsdk_si = TCell.one_from_boc(si_boc)

    return tonsdk_si, nft_address


# ── NFT deploy transaction ────────────────────────────────────────────────────

async def deploy_soulbound_nft(
    owner_address: str,
    owner_name: str,
    personality_hash: str,
    personality: dict,
    avatar_url: Optional[str] = None,
) -> dict:
    """
    Full flow: build metadata → upload to GitHub → deploy NFT item.
    Returns result dict with nft_address, tx_hash, metadata_url, explorer_url.
    """
    # Step 1: Build metadata
    metadata = build_metadata(owner_name, personality_hash, personality, avatar_url)
    filename = f"soul_{personality_hash[:16]}.json"

    # Step 2: Upload metadata to GitHub
    metadata_url = await upload_metadata_to_github(filename, metadata)
    if not metadata_url:
        # Fallback: use a direct URL with the hash (works for demo)
        metadata_url = (
            f"https://raw.githubusercontent.com/zhenek73/eiva/main/metadata/{filename}"
        )
        print(f"[NFT] Using expected metadata URL (upload may have failed): {metadata_url}")

    # Step 3: Build StateInit and derive NFT address
    tonsdk_si, nft_address = build_nft_state_init(
        owner_address_str=owner_address,
        metadata_url=metadata_url,
        index=0,
    )
    print(f"[NFT] Soulbound NFT address: {nft_address}")
    print(f"[NFT] Metadata URL: {metadata_url}")

    # Step 4: Deploy via send_transaction_with_state_init
    tx_hash = await _deploy_nft_transaction(nft_address, tonsdk_si)

    # Step 5: Build explorer URLs
    net = config.TON_NETWORK
    base = "https://testnet.tonscan.org" if net == "testnet" else "https://tonscan.org"
    getgems = (
        f"https://testnet.getgems.io/nft/{nft_address}"
        if net == "testnet"
        else f"https://getgems.io/nft/{nft_address}"
    )

    return {
        "nft_address": nft_address,
        "metadata_url": metadata_url,
        "tx_hash": tx_hash,
        "explorer_url": f"{base}/address/{nft_address}" if tx_hash else None,
        "getgems_url": getgems if tx_hash else None,
        "network": net,
    }


async def _deploy_nft_transaction(nft_address: str, state_init_cell) -> Optional[str]:
    """
    Send transaction from bot wallet to NFT address with state_init → deploys NFT.
    """
    from tonsdk.contract.wallet import WalletVersionEnum, Wallets
    from tonsdk.utils import bytes_to_b64str
    import aiohttp, hashlib

    if not config.TON_MNEMONIC:
        return None

    TONCENTER = {
        "testnet": "https://testnet.toncenter.com/api/v2",
        "mainnet": "https://toncenter.com/api/v2",
    }

    try:
        words = config.TON_MNEMONIC.strip().split()
        mnemo, pub_k, priv_k, wallet = Wallets.from_mnemonics(
            words, WalletVersionEnum.v4r2, 0
        )
        addr = wallet.address.to_string(True, True, False)

        headers = {}
        if config.TON_API_KEY:
            headers["X-API-Key"] = config.TON_API_KEY

        # Read seqno
        seqno = 0
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{TONCENTER[config.TON_NETWORK]}/runGetMethod",
                json={"address": addr, "method": "seqno", "stack": []},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                resp = await r.json()
                if r.status == 200 and resp.get("ok"):
                    exit_code = resp["result"].get("exit_code", -1)
                    if exit_code == 0:
                        raw_val = resp["result"]["stack"][0][1]
                        seqno = int(raw_val, 16) if raw_val.startswith("0x") else int(raw_val)
        print(f"[NFT] Wallet seqno={seqno}")

        # Build transfer WITH state_init for the NFT contract
        transfer = wallet.create_transfer_message(
            to_addr=nft_address,
            amount=100_000_000,   # 0.1 TON — covers deploy + storage
            seqno=seqno,
            payload="",
            state_init=state_init_cell,
        )
        boc = bytes_to_b64str(transfer["message"].to_boc(False))

        # Broadcast with retry
        for attempt in range(1, 5):
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{TONCENTER[config.TON_NETWORK]}/sendBoc",
                    json={"boc": boc},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    result = await r.json()
                    print(f"[NFT] sendBoc attempt {attempt}: status={r.status}")
                    if r.status == 200 and result.get("ok"):
                        raw = base64.b64decode(boc)
                        tx_hash = hashlib.sha256(raw).hexdigest()
                        print(f"[NFT] ✓ NFT deployed! Hash: {tx_hash}")
                        return tx_hash
                    elif r.status == 429 or "Ratelimit" in str(result.get("result", "")):
                        wait = 3 * attempt
                        print(f"[NFT] Rate-limited, waiting {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        print(f"[NFT] Broadcast error: {result}")
                        return None

        print("[NFT] All deploy attempts failed")
        return None

    except Exception as e:
        print(f"[NFT] deploy error: {e}")
        import traceback; traceback.print_exc()
        return None

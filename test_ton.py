#!/usr/bin/env python
"""
Eiva — test_ton.py
Quick sanity check for TON integration without blockchain transactions.
- Imports and initialization
- Derives wallet address from mnemonic (if configured)
- Tests ChromaDB initialization
- No actual blockchain txs
"""

import sys
import os

# Check env
try:
    import config
    print("✓ config.py loaded")
except ImportError as e:
    print(f"✗ config.py failed: {e}")
    sys.exit(1)

# Test TON identity
try:
    from ton_identity import get_wallet_address
    wallet = get_wallet_address()
    if wallet:
        print(f"✓ TON wallet derived: {wallet[:24]}...")
    else:
        print("ⓘ TON_MNEMONIC not configured (expected for demo)")
except ImportError as e:
    print(f"✗ ton_identity.py import failed: {e}")
    sys.exit(1)

# Test nft_contract imports (gracefully)
try:
    from nft_contract import build_metadata
    print("✓ nft_contract.py imports work")
except ImportError as e:
    print(f"⚠ nft_contract.py import warning (tonutils/pytoniq may not be installed): {e}")
except Exception as e:
    print(f"⚠ nft_contract.py has non-critical issue: {e}")

# Test ChromaDB initialization
try:
    from embeddings import EmbeddingStore
    store = EmbeddingStore("test_user_123")
    count = store.count()
    print(f"✓ ChromaDB initialized for test user (count={count})")
except Exception as e:
    print(f"✗ ChromaDB initialization failed: {e}")
    sys.exit(1)

# Test config validation
try:
    config.validate()
    print("✓ config.validate() passed (required env vars present)")
except EnvironmentError as e:
    print(f"✗ config validation failed: {e}")
    sys.exit(1)

print("\n✅ All tests passed! Ready for hackathon.")

#!/usr/bin/env python3
"""Fetch contract source from Etherscan and match it to local repo sources."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from exploit_generation.source_fetcher import fetch_source_code
from exploit_generation.source_resolver import resolve_repo_sources


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch verified source and match local contracts.")
    parser.add_argument("address", help="Contract address (0x...)")
    parser.add_argument("--chain", default="mainnet", help="Chain name (mainnet, bsc, base)")
    parser.add_argument("--contracts-dir", default="contracts", help="Local contracts directory")
    parser.add_argument("--cache-dir", default="cache/sources", help="Cache directory")
    parser.add_argument("--env-file", type=Path, default=None, help="Path to .env file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    env_file = args.env_file or (project_root / ".env")
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        load_dotenv()
        print(f"Warning: No .env file found at {env_file}")

    if not os.getenv("ETHERSCAN_API_KEY"):
        print("Error: ETHERSCAN_API_KEY not set in environment or .env file")
        return 1

    cache_dir = (project_root / args.cache_dir).resolve()
    result = fetch_source_code(args.address, chain=args.chain, cache_dir=cache_dir)

    print(f"Contract: {result.contract_name} ({result.address})")
    print(f"Compiler: {result.compiler_version}")
    print(f"Sources: {len(result.sources) if result.sources else 1}")

    matches = resolve_repo_sources(result, project_root / args.contracts_dir)
    if matches:
        print("Local matches:")
        for match in matches:
            print(f"- {match}")
    else:
        print("No local matches found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

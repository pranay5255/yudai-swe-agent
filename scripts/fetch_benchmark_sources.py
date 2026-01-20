#!/usr/bin/env python3
"""Fetch and cache source code for benchmark contracts."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from exploit_generation.benchmark import load_benchmark, filter_by_chain, enrich_case_with_source
from exploit_generation.models import BenchmarkCase


def main():
    parser = argparse.ArgumentParser(description="Fetch source code for benchmark contracts")
    parser.add_argument("--chain", type=str, help="Filter by chain (mainnet, bsc, base)")
    parser.add_argument("--limit", type=int, help="Max contracts to fetch")
    parser.add_argument("--case", type=str, help="Fetch a specific case by name")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=project_root / "cache" / "sources",
        help="Directory to cache fetched sources",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "cache" / "benchmark_enriched.json",
        help="Output file for enriched benchmark data",
    )
    parser.add_argument("--stats-only", action="store_true", help="Just show stats, don't fetch")
    args = parser.parse_args()

    load_dotenv()

    # Load benchmark
    csv_path = project_root / "benchmark.csv"
    if not csv_path.exists():
        print(f"Error: benchmark.csv not found at {csv_path}")
        sys.exit(1)

    cases = load_benchmark(csv_path)
    print(f"Loaded {len(cases)} benchmark cases")

    # Show stats
    chains = {}
    for c in cases:
        chains[c.chain] = chains.get(c.chain, 0) + 1
    print(f"Chain distribution: {chains}")

    if args.stats_only:
        return

    # Filter
    if args.case:
        cases = [c for c in cases if c.case_name == args.case]
        if not cases:
            print(f"Error: Case '{args.case}' not found")
            sys.exit(1)
    elif args.chain:
        cases = filter_by_chain(cases, args.chain)
        print(f"Filtered to {len(cases)} {args.chain} cases")

    if args.limit:
        cases = cases[: args.limit]
        print(f"Limited to {args.limit} cases")

    # Create cache directory
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    # Fetch sources
    enriched = []
    success = 0
    failed = 0

    for i, case in enumerate(cases):
        print(f"\n[{i+1}/{len(cases)}] {case.case_name} ({case.chain})")
        print(f"  Address: {case.target_contract_address}")
        print(f"  Block: {case.fork_block_number}")

        try:
            enriched_case = enrich_case_with_source(case, cache_dir=args.cache_dir)
            if enriched_case.source_code:
                print(f"  Contract: {enriched_case.contract_name}")
                print(f"  Source: {len(enriched_case.source_code)} chars")
                print(f"  ABI: {len(enriched_case.abi or [])} entries")
                success += 1
            else:
                print("  Source: NOT VERIFIED")
                failed += 1
            enriched.append(enriched_case)
        except Exception as e:
            print(f"  Error: {e}")
            failed += 1
            enriched.append(case)

    # Save enriched data
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_data = [c.to_dict() for c in enriched]
    args.output.write_text(json.dumps(output_data, indent=2))
    print(f"\nSaved enriched data to {args.output}")

    # Summary
    print(f"\n=== Summary ===")
    print(f"Total: {len(cases)}")
    print(f"Success: {success}")
    print(f"Failed/Unverified: {failed}")
    print(f"Success rate: {success/len(cases)*100:.1f}%")


if __name__ == "__main__":
    main()

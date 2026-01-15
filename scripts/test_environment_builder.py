#!/usr/bin/env python3
"""Test the environment builder on existing contracts.

This script analyzes and attempts to build compilation-ready environments
for all contracts in the repository to validate the system.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vulnerability_injection.contract_analyzer import analyze_contract
from vulnerability_injection.environment_builder import build_environment_for_contract


def test_contract(contract_path: Path, test_compile: bool = True) -> dict:
    """Test environment building for a single contract.

    Args:
        contract_path: Path to contract
        test_compile: Whether to test compilation

    Returns:
        Dict with test results
    """
    print(f"\n{'=' * 70}")
    print(f"Testing: {contract_path.name}")
    print(f"Path: {contract_path}")
    print('=' * 70)

    try:
        # Step 1: Analyze
        metadata = analyze_contract(contract_path)
        print(f"\n📊 Analysis:")
        print(f"  Solidity Version: {metadata.solidity_version}")
        print(f"  Pragma: {metadata.pragma_range}")
        print(f"  Template: {metadata.recommended_template}")
        print(f"  OpenZeppelin: {metadata.has_openzeppelin}")
        if metadata.oz_version:
            print(f"  OZ Version: {metadata.oz_version}")
        print(f"  Imports: {len(metadata.imports)}")
        for imp in metadata.imports[:5]:  # Show first 5
            print(f"    - {imp}")
        if len(metadata.imports) > 5:
            print(f"    ... and {len(metadata.imports) - 5} more")
        print(f"  External Contracts: {metadata.external_contracts}")
        print(f"  Standalone: {metadata.is_standalone}")
        print(f"  Needs Network: {metadata.needs_network}")

        # Step 2: Build environment (if requested)
        if test_compile:
            print(f"\n🔨 Building Environment...")
            result = build_environment_for_contract(contract_path, use_docker=False)

            if result.success:
                print(f"  ✅ SUCCESS - Contract compiles!")
                print(f"  Workspace: {result.workspace}")
                print(f"  Template: {result.template_used}")
            else:
                print(f"  ❌ FAILED - Compilation errors")
                print(f"  Errors: {len(result.errors)}")
                for error in result.errors:
                    print(f"    - {error}")
                print(f"\n  Compilation output (first 500 chars):")
                print(f"  {result.compilation_output[:500]}")

            return {
                "contract": contract_path.name,
                "analyzed": True,
                "built": True,
                "success": result.success,
                "template": result.template_used,
                "metadata": metadata,
                "errors": result.errors,
            }
        else:
            return {
                "contract": contract_path.name,
                "analyzed": True,
                "built": False,
                "metadata": metadata,
            }

    except Exception as e:
        print(f"  ❌ EXCEPTION: {e}")
        import traceback

        traceback.print_exc()
        return {
            "contract": contract_path.name,
            "analyzed": False,
            "built": False,
            "success": False,
            "error": str(e),
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test environment builder on contracts")
    parser.add_argument(
        "--contract",
        "-c",
        type=Path,
        help="Test a specific contract (default: test all)",
    )
    parser.add_argument(
        "--no-compile",
        action="store_true",
        help="Only analyze, don't attempt compilation",
    )
    parser.add_argument(
        "--category",
        choices=["vulnerabilities", "audited", "real_world"],
        help="Test only contracts in specific category",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    # Set up logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    project_root = Path(__file__).parent.parent
    contracts_dir = project_root / "contracts"

    # Find contracts to test
    if args.contract:
        contracts = [args.contract]
    elif args.category:
        category_dir = contracts_dir / args.category
        contracts = list(category_dir.rglob("*.sol"))
    else:
        # Test all contracts
        contracts = list(contracts_dir.rglob("*.sol"))

    print(f"🧪 Testing {len(contracts)} contracts")
    print(f"Compilation: {'DISABLED' if args.no_compile else 'ENABLED'}")

    results = []
    for contract in sorted(contracts):
        result = test_contract(contract, test_compile=not args.no_compile)
        results.append(result)

    # Summary
    print(f"\n\n{'=' * 70}")
    print("📈 SUMMARY")
    print('=' * 70)

    analyzed = [r for r in results if r.get("analyzed")]
    built = [r for r in results if r.get("built")]
    succeeded = [r for r in built if r.get("success")]

    print(f"Total Contracts: {len(results)}")
    print(f"Analyzed: {len(analyzed)} / {len(results)}")

    if built:
        print(f"Build Attempted: {len(built)}")
        print(f"Build Succeeded: {len(succeeded)} / {len(built)}")
        print(f"Build Failed: {len(built) - len(succeeded)}")
        print(f"Success Rate: {len(succeeded) / len(built) * 100:.1f}%")

        # Group by template
        template_counts = {}
        for r in succeeded:
            template = r.get("template", "unknown")
            template_counts[template] = template_counts.get(template, 0) + 1

        print(f"\n📊 Templates Used:")
        for template, count in sorted(template_counts.items()):
            print(f"  {template}: {count}")

        # Show failed contracts
        if len(built) > len(succeeded):
            print(f"\n❌ Failed Contracts:")
            for r in [r for r in built if not r.get("success")]:
                print(f"  - {r['contract']}")
                if r.get("errors"):
                    print(f"    Errors: {len(r['errors'])}")

    # Save detailed results
    if built:
        import json

        results_file = project_root / "contract_analysis_results.json"
        with open(results_file, "w") as f:
            # Make results JSON serializable
            serializable_results = []
            for r in results:
                sr = {k: v for k, v in r.items() if k != "metadata"}
                if "metadata" in r:
                    m = r["metadata"]
                    sr["metadata"] = {
                        "solidity_version": m.solidity_version,
                        "pragma_range": m.pragma_range,
                        "has_openzeppelin": m.has_openzeppelin,
                        "oz_version": m.oz_version,
                        "imports": m.imports,
                        "external_contracts": m.external_contracts,
                        "is_standalone": m.is_standalone,
                        "recommended_template": m.recommended_template,
                    }
                serializable_results.append(sr)

            json.dump(serializable_results, f, indent=2)
        print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    main()

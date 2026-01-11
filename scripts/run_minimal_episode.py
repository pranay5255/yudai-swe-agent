#!/usr/bin/env python3
"""
Run a single minimal security-fix episode using the local repo code.

Example:
  python scripts/run_minimal_episode.py -m claude-sonnet-4-20250514
"""

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal RL episode on a single contract.")
    parser.add_argument(
        "--contract",
        "-c",
        type=Path,
        default=Path("contracts/SimpleBank.sol"),
        help="Path to the clean Solidity contract",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Model name (e.g., claude-sonnet-4-20250514). Required if no default is configured.",
    )
    parser.add_argument(
        "--operators",
        "-o",
        type=str,
        default="RE",
        help="Comma-separated MuSe operators to enable (default: RE).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("rl_results"),
        help="Directory to save episode outputs",
    )
    parser.add_argument(
        "--image",
        type=str,
        default="yudai-complete:latest",
        help="Docker image to use",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="security_fix_minimal",
        help="Agent config name or path (default: security_fix_minimal)",
    )
    parser.add_argument(
        "--cost-limit",
        type=float,
        default=3.0,
        help="Maximum cost in USD for the agent",
    )
    parser.add_argument(
        "--no-yolo",
        action="store_true",
        help="Disable yolo mode (useful when running interactive agents)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    from vulnerability_injection.episode import run_episode

    contract = Path(args.contract).resolve()
    if not contract.exists():
        raise FileNotFoundError(f"Contract not found: {contract}")

    operators = [op.strip().upper() for op in args.operators.split(",") if op.strip()] if args.operators else None

    result = run_episode(
        clean_contract=contract,
        output_dir=args.output,
        model_name=args.model,
        operators=operators,
        yolo=not args.no_yolo,
        cost_limit=args.cost_limit,
        docker_image=args.image,
        config_path=args.config,
    )

    print(
        f"Episode {result.episode_id}: operator={result.mutation.operator} "
        f"fixed={result.reward.vulnerability_fixed} reward={result.reward.total_reward:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

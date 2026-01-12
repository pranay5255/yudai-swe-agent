#!/usr/bin/env python3
"""
Run a single minimal security-fix episode using OpenRouter.

Reads configuration from .env file:
  - OPENROUTER_API_KEY: Your OpenRouter API key
  - OPENROUTER_MODEL_NAME: Model to use (e.g., anthropic/claude-3.5-sonnet)

Example:
  python scripts/run_minimal_episode.py
  python scripts/run_minimal_episode.py -c contracts/SimpleBank.sol --operators RE,TX
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a minimal RL episode on a single contract using OpenRouter."
    )
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
        help="Model name (overrides OPENROUTER_MODEL_NAME from .env)",
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
        default="security_fix_openrouter",
        help="Agent config name or path (default: security_fix_openrouter)",
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
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Path to .env file (default: .env in project root)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Load environment variables from .env
    env_file = args.env_file or (project_root / ".env")
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        print(f"Warning: No .env file found at {env_file}")
        print("Create one from .env.example: cp .env.example .env")

    # Validate required env vars
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set in environment or .env file")
        print("Get your API key from https://openrouter.ai/keys")
        return 1

    # Get model name from args or env
    model_name = args.model or os.getenv("OPENROUTER_MODEL_NAME")
    if not model_name:
        print("Error: No model specified. Use --model or set OPENROUTER_MODEL_NAME in .env")
        print("Examples: anthropic/claude-3.5-sonnet, openai/gpt-4o, google/gemini-pro")
        return 1

    print(f"Using model: {model_name}")

    from vulnerability_injection.episode import run_episode

    contract = Path(args.contract).resolve()
    if not contract.exists():
        raise FileNotFoundError(f"Contract not found: {contract}")

    operators = (
        [op.strip().upper() for op in args.operators.split(",") if op.strip()]
        if args.operators
        else None
    )

    print(f"Running episode on {contract.name} with operators: {operators}")
    print("-" * 50)

    result = run_episode(
        clean_contract=contract,
        output_dir=args.output,
        model_name=model_name,
        operators=operators,
        yolo=not args.no_yolo,
        cost_limit=args.cost_limit,
        docker_image=args.image,
        config_path=args.config,
    )

    print("-" * 50)
    print(f"Episode ID: {result.episode_id}")
    print(f"Operator: {result.mutation.operator}")
    print(f"Vulnerability Fixed: {result.reward.vulnerability_fixed}")
    print(f"Compilation Passed: {result.reward.compilation_passed}")
    print(f"New Vulns Introduced: {result.reward.new_vulns_introduced}")
    print(f"Total Reward: {result.reward.total_reward:.2f}")
    print(f"Results saved to: {args.output / result.episode_id}.result.json")

    return 0 if result.reward.vulnerability_fixed else 1


if __name__ == "__main__":
    raise SystemExit(main())

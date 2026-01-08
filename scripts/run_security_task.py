#!/usr/bin/env python3
"""
Run mini-swe-agent on a vulnerable contract for security fix task.

This script loads a training pair (original, vulnerable, metadata) and
runs the mini-swe-agent to attempt to fix the vulnerability.

Usage:
    python scripts/run_security_task.py --pair dataset/pairs/Token-m46f345c9/
    python scripts/run_security_task.py --pair dataset/pairs/Token-m46f345c9/ --model claude-sonnet-4-20250514
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_training_pair(pair_dir: Path) -> dict:
    """
    Load a training pair from disk.

    Args:
        pair_dir: Directory containing original.sol, vulnerable.sol, metadata.json

    Returns:
        Dictionary with original, vulnerable, and metadata
    """
    pair_dir = Path(pair_dir)

    original_path = pair_dir / "original.sol"
    vulnerable_path = pair_dir / "vulnerable.sol"
    metadata_path = pair_dir / "metadata.json"

    if not all(p.exists() for p in [original_path, vulnerable_path, metadata_path]):
        raise FileNotFoundError(f"Missing files in pair directory: {pair_dir}")

    return {
        "original_path": original_path,
        "vulnerable_path": vulnerable_path,
        "vulnerable_source": vulnerable_path.read_text(),
        "metadata": json.loads(metadata_path.read_text()),
        "pair_id": pair_dir.name,
    }


def create_task_prompt(pair: dict) -> str:
    """
    Create the task prompt for the agent.

    Args:
        pair: Training pair dictionary

    Returns:
        Task prompt string
    """
    metadata = pair["metadata"]
    bug_type = metadata.get("bug_type", "Unknown")
    operator = metadata.get("operator", "")
    severity = metadata.get("severity", "unknown")
    description = metadata.get("description", "")

    # Get location info
    location = metadata.get("location", {})
    start_line = location.get("start_line", "?")
    end_line = location.get("end_line", "?")

    prompt = f"""You are a smart contract security expert. The following Solidity contract contains a **{bug_type}** vulnerability (severity: {severity}).

## Vulnerability Details
- **Type**: {bug_type} ({operator})
- **Severity**: {severity}
- **Location**: Lines {start_line}-{end_line}
- **Description**: {description}

## Your Task
1. Read and analyze the vulnerable contract
2. Identify the exact vulnerability location
3. Fix the vulnerability while maintaining the contract's original functionality
4. Verify your fix compiles correctly using `forge build`
5. Optionally run static analysis with `slither` to confirm the fix

## Contract Source
The vulnerable contract is located at: {pair['vulnerable_path']}

## Important Notes
- Do NOT change the contract's intended behavior
- Ensure your fix follows Solidity best practices
- The original code had this vulnerability injected for training purposes

Begin by reading the contract and identifying the vulnerability.
"""
    return prompt


def run_agent(
    task: str,
    model: str = "claude-sonnet-4-20250514",
    config: str = "security",
    output_file: Path | None = None,
    interactive: bool = False,
) -> tuple[str, list[dict]]:
    """
    Run mini-swe-agent on a task.

    Args:
        task: Task prompt
        model: Model name
        config: Config file to use
        output_file: Optional file to save trajectory
        interactive: Run in interactive mode

    Returns:
        (status, messages) tuple
    """
    try:
        from minisweagent.agents import DefaultAgent, InteractiveAgent
        from minisweagent.environments import get_environment
        from minisweagent.models import get_model
    except ImportError:
        print("Error: mini-swe-agent not installed. Run 'pip install -e .'")
        sys.exit(1)

    # Initialize model
    model_instance = get_model(model)

    # Initialize environment (foundry for smart contracts)
    env = get_environment("foundry")

    # Initialize agent
    if interactive:
        agent = InteractiveAgent(model_instance, env, config_file=config)
    else:
        agent = DefaultAgent(model_instance, env, config_file=config)

    # Run agent
    print(f"Running agent with model: {model}")
    print(f"Config: {config}")
    print("-" * 50)

    status, output = agent.run(task)

    # Get messages/trajectory
    messages = agent.messages

    # Save trajectory if output file specified
    if output_file:
        trajectory = {
            "task": task,
            "model": model,
            "config": config,
            "status": status,
            "output": output,
            "messages": messages,
            "timestamp": datetime.now().isoformat(),
        }
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(trajectory, indent=2))
        print(f"\nTrajectory saved to: {output_file}")

    return status, messages


def main():
    parser = argparse.ArgumentParser(
        description="Run mini-swe-agent on a vulnerable contract"
    )
    parser.add_argument(
        "--pair", "-p",
        type=Path,
        required=True,
        help="Path to training pair directory",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="claude-sonnet-4-20250514",
        help="Model to use (default: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="security",
        help="Config file to use (default: security)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output file for trajectory (JSON)",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show task prompt without running agent",
    )

    args = parser.parse_args()

    # Load training pair
    print(f"Loading training pair: {args.pair}")
    try:
        pair = load_training_pair(args.pair)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Create task prompt
    task = create_task_prompt(pair)

    if args.dry_run:
        print("\n" + "=" * 50)
        print("TASK PROMPT (dry run):")
        print("=" * 50)
        print(task)
        print("=" * 50)
        return

    # Set default output file if not specified
    output_file = args.output
    if output_file is None:
        output_file = Path("trajectories") / f"{pair['pair_id']}.json"

    # Run agent
    status, messages = run_agent(
        task=task,
        model=args.model,
        config=args.config,
        output_file=output_file,
        interactive=args.interactive,
    )

    print(f"\n{'=' * 50}")
    print(f"Status: {status}")
    print(f"Messages: {len(messages)}")


if __name__ == "__main__":
    main()

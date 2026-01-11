#!/usr/bin/env python3
"""Run a single RL episode to fix a vulnerability in a smart contract.

This script demonstrates the RL pipeline:
1. Take a clean Solidity contract
2. Inject a vulnerability using MuSe
3. Run mini-swe-agent to fix it
4. Evaluate success with Slither + Aderyn
"""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(rich_markup_mode="rich")
console = Console()


@app.command()
def main(
    contract: Path = typer.Argument(
        ...,
        help="Path to the Solidity contract to test",
        exists=True,
        readable=True,
    ),
    output: Path = typer.Option(
        Path("./rl_results"),
        "-o", "--output",
        help="Directory to save episode results",
    ),
    model: str = typer.Option(
        None,
        "-m", "--model",
        help="LLM model to use (e.g., claude-sonnet-4-20250514)",
    ),
    operators: str = typer.Option(
        None,
        "--operators",
        help="Comma-separated MuSe operators (e.g., RE,TX,UC). Default: all",
    ),
    yolo: bool = typer.Option(
        True,
        "-y", "--yolo/--no-yolo",
        help="Run without confirmation (default: True for demo)",
    ),
    cost_limit: float = typer.Option(
        3.0,
        "-l", "--cost-limit",
        help="Maximum cost in USD for the agent",
    ),
    config: str | None = typer.Option(
        None,
        "--config",
        help="Agent config name or path (default: foundry.yaml)",
    ),
    docker_image: str = typer.Option(
        "yudai-complete:latest",
        "--image",
        help="Docker image to use for execution",
    ),
):
    """Run a vulnerability fix episode.

    Example:
        mini-security-fix ./contracts/Token.sol -m claude-sonnet-4-20250514

    This will:
    1. Inject a random vulnerability into the contract
    2. Run mini-swe-agent to fix it
    3. Evaluate and report results
    """
    # Add project root to path for vulnerability_injection imports
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

    from vulnerability_injection.episode import run_episode
    from vulnerability_injection.models import OPERATOR_INFO

    console.print(Panel.fit(
        "[bold green]RL Vulnerability Fix Demo[/bold green]\n"
        f"Contract: {contract}\n"
        f"Model: {model or 'default'}\n"
        f"Config: {config or 'foundry.yaml'}\n"
        f"Docker: {docker_image}\n"
        f"Output: {output}",
        title="Episode Configuration",
    ))

    # Parse operators
    ops = None
    if operators:
        ops = [o.strip().upper() for o in operators.split(",")]
        invalid = [o for o in ops if o not in OPERATOR_INFO]
        if invalid:
            console.print(f"[red]Invalid operators: {invalid}[/red]")
            console.print(f"[yellow]Valid operators: {list(OPERATOR_INFO.keys())}[/yellow]")
            raise typer.Exit(1)

    # Run episode
    console.print("\n[bold]Starting episode...[/bold]\n")

    try:
        result = run_episode(
            clean_contract=contract,
            output_dir=output,
            model_name=model,
            operators=ops,
            yolo=yolo,
            cost_limit=cost_limit,
            docker_image=docker_image,
            config_path=config,
        )
    except Exception as e:
        console.print(f"[red]Episode failed: {e}[/red]")
        raise typer.Exit(1)

    # Display results
    console.print("\n")

    # Mutation info
    mutation_table = Table(title="Injected Vulnerability")
    mutation_table.add_column("Property", style="cyan")
    mutation_table.add_column("Value", style="white")
    mutation_table.add_row("Operator", result.mutation.operator)
    mutation_table.add_row("Vulnerability", OPERATOR_INFO.get(result.mutation.operator, {}).get("name", "Unknown"))
    mutation_table.add_row("Location", f"Lines {result.mutation.start_line}-{result.mutation.end_line}")
    console.print(mutation_table)

    # Findings comparison
    findings_table = Table(title="Security Analysis")
    findings_table.add_column("Metric", style="cyan")
    findings_table.add_column("Baseline", style="yellow")
    findings_table.add_column("Final", style="green" if result.reward.vulnerability_fixed else "red")
    findings_table.add_row(
        "Total Findings",
        str(len(result.baseline_findings)),
        str(len(result.final_findings)),
    )
    findings_table.add_row(
        "Target Vuln Detected",
        "Yes" if any(f.matches_vulnerability(result.mutation.operator) for f in result.baseline_findings) else "No",
        "No" if result.reward.vulnerability_fixed else "Yes",
    )
    console.print(findings_table)

    # Reward summary
    reward_panel = Panel(
        f"[bold]Vulnerability Fixed:[/bold] {'✅ Yes' if result.reward.vulnerability_fixed else '❌ No'}\n"
        f"[bold]Compilation Passed:[/bold] {'✅ Yes' if result.compilation_passed else '❌ No'}\n"
        f"[bold]New Vulns Introduced:[/bold] {result.reward.new_vulns_introduced}\n"
        f"[bold]Total Reward:[/bold] {result.reward.total_reward:.2f}",
        title="Episode Result",
        border_style="green" if result.reward.total_reward > 0 else "red",
    )
    console.print(reward_panel)

    # Output paths
    console.print(f"\n[dim]Results saved to: {output}/{result.episode_id}.*[/dim]")


if __name__ == "__main__":
    app()

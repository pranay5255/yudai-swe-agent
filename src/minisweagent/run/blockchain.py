#!/usr/bin/env python3
"""CLI entry point for blockchain development modes.

This provides a unified interface for different blockchain development tasks:
- cast_explorer: Read-only blockchain queries
- tx_analyzer: Transaction replay and analysis
- contract_dev: Smart contract development with OZ + Uniswap V4

Usage:
    # Interactive mode selection
    mini-blockchain

    # Direct mode selection
    mini-blockchain cast -t "check USDC balance of vitalik.eth"
    mini-blockchain tx -t "analyze 0x123..."
    mini-blockchain dev -t "create an ERC20 token with staking"
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from minisweagent import global_config_dir
from minisweagent.agents.interactive import InteractiveAgent
from minisweagent.agents.interactive_textual import TextualAgent
from minisweagent.config import builtin_config_dir, get_config_path
from minisweagent.environments import get_environment
from minisweagent.models import get_model
from minisweagent.run.utils.save import save_traj
from minisweagent.utils.log import logger

app = typer.Typer(
    name="mini-blockchain",
    help="Blockchain development modes for mini-swe-agent",
    rich_markup_mode="rich",
    no_args_is_help=False,
)

console = Console(highlight=False)

DEFAULT_OUTPUT = global_config_dir / "last_blockchain_run.traj.json"


def _get_config_path(config_name: str) -> Path:
    """Get the path to a config file."""
    config_dir = builtin_config_dir
    config_path = config_dir / f"{config_name}.yaml"
    if config_path.exists():
        return config_path
    # Try as absolute path
    if Path(config_name).exists():
        return Path(config_name)
    return get_config_path(config_name)


def _run_blockchain_agent(
    config_name: str,
    task: str,
    model_name: str | None,
    visual: bool,
    workspace_path: Path,
    yolo: bool = False,
    cost_limit: float | None = None,
    output: Path | None = None,
) -> int:
    """Run the agent with blockchain-specific configuration."""

    config_path = _get_config_path(config_name)
    console.print(f"Loading config from [bold green]{config_path}[/bold green]")

    config = yaml.safe_load(config_path.read_text())

    # Override config with CLI options
    if yolo:
        config.setdefault("agent", {})["mode"] = "yolo"
    if cost_limit is not None:
        config.setdefault("agent", {})["cost_limit"] = cost_limit

    # Set up workspace path in environment config
    env_config = config.get("environment", {})
    env_config["project_path"] = str(workspace_path)

    # Get model
    model = get_model(model_name, config.get("model", {}))

    # Get environment (FoundryEnvironment)
    env = get_environment(env_config)

    # Select agent class based on visual flag
    agent_class = InteractiveAgent
    if visual == (os.getenv("MSWEA_VISUAL_MODE_DEFAULT", "false") == "false"):
        agent_class = TextualAgent

    # Create and run agent
    agent = agent_class(model, env, **config.get("agent", {}))

    exit_status, result, extra_info = None, None, None
    try:
        exit_status, result = agent.run(task)
        return 0 if exit_status == "Submitted" else 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        exit_status = "Interrupted"
        return 130
    except Exception as e:
        logger.error(f"Error running agent: {e}", exc_info=True)
        exit_status, result = type(e).__name__, str(e)
        extra_info = {"traceback": traceback.format_exc()}
        return 1
    finally:
        if output:
            save_traj(agent, output, exit_status=exit_status, result=result, extra_info=extra_info)


@app.command("cast", help="Read-only blockchain queries using cast")
def cast_explorer(
    task: str = typer.Option(
        ...,
        "-t", "--task",
        help="Query to execute (e.g., 'check USDC balance of vitalik.eth')",
    ),
    model: str | None = typer.Option(
        None,
        "-m", "--model",
        help="Model name override",
    ),
    visual: bool = typer.Option(
        False,
        "-v", "--visual",
        help="Use visual TUI mode",
    ),
    yolo: bool = typer.Option(
        True,  # Default to yolo for read-only ops
        "-y", "--yolo/--no-yolo",
        help="Auto-approve commands (default: true for read-only)",
    ),
    rpc_url: str | None = typer.Option(
        None,
        "--rpc-url",
        help="RPC URL (defaults to ETH_RPC_URL env var)",
    ),
    output: Path | None = typer.Option(
        None,
        "-o", "--output",
        help="Save trajectory to file",
    ),
):
    """Read-only blockchain exploration with cast.

    Examples:
        mini-blockchain cast -t "check USDC balance of 0x..."
        mini-blockchain cast -t "get reserves of Uniswap V2 ETH/USDC pair"
        mini-blockchain cast -t "decode the calldata 0xa9059cbb..."
    """
    from minisweagent.workspace import create_workspace, cleanup_workspace, WorkspaceMode

    # Set RPC URL if provided
    if rpc_url:
        os.environ["ETH_RPC_URL"] = rpc_url
        os.environ["RPC_URL"] = rpc_url

    # Create minimal workspace
    console.print("[dim]Creating workspace...[/dim]")
    workspace_info = create_workspace(WorkspaceMode.CAST_EXPLORER)
    console.print(f"[dim]Workspace: {workspace_info.path}[/dim]")

    try:
        return _run_blockchain_agent(
            config_name="cast_explorer",
            task=task,
            model_name=model,
            visual=visual,
            workspace_path=workspace_info.path,
            yolo=yolo,
            output=output,
        )
    finally:
        cleanup_workspace(workspace_info)


@app.command("tx", help="Transaction analysis and replay")
def tx_analyzer(
    task: str = typer.Option(
        ...,
        "-t", "--task",
        help="Transaction hash or analysis request",
    ),
    model: str | None = typer.Option(
        None,
        "-m", "--model",
        help="Model name override",
    ),
    visual: bool = typer.Option(
        False,
        "-v", "--visual",
        help="Use visual TUI mode",
    ),
    yolo: bool = typer.Option(
        False,
        "-y", "--yolo",
        help="Auto-approve commands (default: false, confirm anvil forks)",
    ),
    rpc_url: str | None = typer.Option(
        None,
        "--rpc-url",
        help="RPC URL for the chain where the transaction occurred",
    ),
    output: Path | None = typer.Option(
        None,
        "-o", "--output",
        help="Save trajectory to file",
    ),
):
    """Deep transaction analysis with local fork replay.

    Examples:
        mini-blockchain tx -t "analyze 0x1234...abcd"
        mini-blockchain tx -t "explain what happened in the Euler exploit tx"
        mini-blockchain tx -t "trace the fund flow in 0x..."
    """
    from minisweagent.workspace import create_workspace, cleanup_workspace, WorkspaceMode

    # Set RPC URL if provided
    if rpc_url:
        os.environ["ETH_RPC_URL"] = rpc_url
        os.environ["RPC_URL"] = rpc_url

    # Create workspace with helper scripts
    console.print("[dim]Creating workspace...[/dim]")
    workspace_info = create_workspace(WorkspaceMode.TX_ANALYZER)
    console.print(f"[dim]Workspace: {workspace_info.path}[/dim]")

    try:
        return _run_blockchain_agent(
            config_name="tx_analyzer",
            task=task,
            model_name=model,
            visual=visual,
            workspace_path=workspace_info.path,
            yolo=yolo,
            output=output,
        )
    finally:
        cleanup_workspace(workspace_info)


@app.command("dev", help="Smart contract development with OZ + Uniswap V4")
def contract_dev(
    task: str = typer.Option(
        ...,
        "-t", "--task",
        help="Development task (e.g., 'create a staking contract')",
    ),
    model: str | None = typer.Option(
        None,
        "-m", "--model",
        help="Model name override",
    ),
    visual: bool = typer.Option(
        False,
        "-v", "--visual",
        help="Use visual TUI mode",
    ),
    yolo: bool = typer.Option(
        False,
        "-y", "--yolo",
        help="Auto-approve commands",
    ),
    cost_limit: float | None = typer.Option(
        None,
        "-l", "--cost-limit",
        help="Cost limit in USD",
    ),
    project_path: Path | None = typer.Option(
        None,
        "-p", "--project",
        help="Use existing project instead of creating temp workspace",
    ),
    keep_workspace: bool = typer.Option(
        False,
        "--keep",
        help="Keep the workspace after completion (for temp workspaces)",
    ),
    no_samples: bool = typer.Option(
        False,
        "--no-samples",
        help="Don't include sample contracts in new workspace",
    ),
    output: Path | None = typer.Option(
        None,
        "-o", "--output",
        help="Save trajectory to file",
    ),
):
    """Full smart contract development environment.

    Comes pre-configured with:
    - OpenZeppelin Contracts (ERC20, ERC721, access control, security)
    - Uniswap V4 Core & Periphery (hooks, pools)
    - forge-std (testing utilities)

    Examples:
        mini-blockchain dev -t "create an ERC20 token with staking rewards"
        mini-blockchain dev -t "build a Uniswap V4 hook for dynamic fees"
        mini-blockchain dev -t "create an NFT with on-chain metadata"
    """
    from minisweagent.workspace import create_workspace, cleanup_workspace, WorkspaceMode

    workspace_info = None

    if project_path:
        # Use existing project
        if not project_path.exists():
            console.print(f"[red]Error: Project path does not exist: {project_path}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Using existing project: {project_path}[/green]")
        workspace_path = project_path
    else:
        # Create new workspace
        console.print("[yellow]Setting up development workspace...[/yellow]")
        console.print("[dim]Installing: forge-std, OpenZeppelin, Uniswap V4[/dim]")

        workspace_info = create_workspace(
            WorkspaceMode.CONTRACT_DEV,
            include_samples=not no_samples,
        )
        workspace_path = workspace_info.path

        # Show setup summary
        table = Table(title="Workspace Setup", show_header=False, box=None)
        table.add_column("Item", style="cyan")
        table.add_column("Status", style="green")
        table.add_row("Path", str(workspace_path))
        table.add_row("forge-std", "✓" if workspace_info.has_forge_std else "✗")
        table.add_row("OpenZeppelin", "✓" if workspace_info.has_openzeppelin else "✗")
        table.add_row("Uniswap V4", "✓" if workspace_info.has_uniswap_v4 else "✗")
        console.print(table)

    try:
        return _run_blockchain_agent(
            config_name="contract_dev",
            task=task,
            model_name=model,
            visual=visual,
            workspace_path=workspace_path,
            yolo=yolo,
            cost_limit=cost_limit,
            output=output,
        )
    finally:
        if workspace_info and not keep_workspace:
            cleanup_workspace(workspace_info)
            console.print("[dim]Workspace cleaned up[/dim]")
        elif workspace_info and keep_workspace:
            console.print(f"[green]Workspace preserved at: {workspace_info.path}[/green]")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
):
    """Blockchain development modes for mini-swe-agent.

    Select a mode to get started:

    \b
    • cast  - Read-only blockchain queries (balances, storage, decode)
    • tx    - Transaction analysis and replay with traces
    • dev   - Smart contract development with OZ + Uniswap V4
    """
    if ctx.invoked_subcommand is None:
        # Show mode selection menu
        console.print(
            Panel.fit(
                "[bold cyan]mini-blockchain[/bold cyan]\n\n"
                "Blockchain development modes for mini-swe-agent\n\n"
                "[yellow]Available modes:[/yellow]\n"
                "  [green]cast[/green]  - Read-only blockchain queries\n"
                "  [green]tx[/green]    - Transaction analysis & replay\n"
                "  [green]dev[/green]   - Smart contract development\n\n"
                "[dim]Example: mini-blockchain dev -t 'create a staking contract'[/dim]",
                title="🔗 Blockchain Mode",
                border_style="blue",
            )
        )

        console.print("\n[dim]Run with --help for more options[/dim]")
        raise typer.Exit(0)


if __name__ == "__main__":
    app()

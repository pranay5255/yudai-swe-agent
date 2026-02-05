import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from minisweagent import Agent, __version__


def _get_class_name_with_module(obj: Any) -> str:
    """Get the full class name with module path."""
    return f"{obj.__class__.__module__}.{obj.__class__.__name__}"


def save_traj(
    agent: Agent | None,
    path: Path | None,
    *,
    print_path: bool = True,
    exit_status: str | None = None,
    result: str | None = None,
    extra_info: dict | None = None,
    print_fct: Callable = print,
    **kwargs,
):
    """Save the trajectory of the agent to a file.

    Args:
        agent: The agent to save the trajectory of.
        path: The path to save the trajectory to.
        print_path: Whether to print confirmation of path to the terminal.
        exit_status: The exit status of the agent.
        result: The result/submission of the agent.
        extra_info: Extra information to save (will be merged into the info dict).
        **kwargs: Additional information to save (will be merged into top level)

    """
    if path is None:
        return
    exit_info = {
        "exit_status": exit_status,
        "submission": result,
    }
    if extra_info:
        exit_info.update(extra_info)

    if agent is not None:
        data = agent.save(exit_info=exit_info, **kwargs)
    else:
        data = {
            "info": {
                "exit_status": exit_status,
                "submission": result,
                "model_stats": {
                    "cost": 0.0,
                    "api_calls": 0,
                },
                "mini_version": __version__,
            },
            "messages": [],
            "trajectory_format": "mini-swe-agent-2",
        } | kwargs
        if extra_info:
            data["info"].update(extra_info)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    if print_path:
        print_fct(f"Saved trajectory to '{path}'")

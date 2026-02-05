from __future__ import annotations

import json
from typing import Any


def get_action_command(action: dict | str) -> str:
    """Extract the shell command from an action dict or string."""
    if isinstance(action, str):
        return action
    if "command" in action and isinstance(action["command"], str):
        return action["command"]
    if "action" in action and isinstance(action["action"], str):
        return action["action"]
    if "args" in action and isinstance(action["args"], dict) and isinstance(action["args"].get("command"), str):
        return action["args"]["command"]
    if "arguments" in action and isinstance(action["arguments"], dict) and isinstance(action["arguments"].get("command"), str):
        return action["arguments"]["command"]
    if "function" in action and isinstance(action["function"], dict):
        arguments = action["function"].get("arguments")
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
                if isinstance(parsed, dict) and isinstance(parsed.get("command"), str):
                    return parsed["command"]
            except json.JSONDecodeError:
                pass
        if isinstance(arguments, dict) and isinstance(arguments.get("command"), str):
            return arguments["command"]
    raise ValueError(f"Action does not contain a command: {action}")


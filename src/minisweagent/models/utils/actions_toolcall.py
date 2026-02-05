from __future__ import annotations

import json
import uuid
from typing import Any

from jinja2 import StrictUndefined, Template

from minisweagent.exceptions import FormatError

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Execute a bash command in the agent environment.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to run."},
            },
            "required": ["command"],
        },
    },
}


def _get_toolcall_fields(call: Any) -> tuple[str | None, str | None, str | None, Any]:
    """Extract (id, name, arguments, raw_function) from a tool call dict or object."""
    if isinstance(call, dict):
        call_id = call.get("id")
        function = call.get("function", {})
        name = function.get("name")
        arguments = function.get("arguments")
        return call_id, name, arguments, function
    # litellm / OpenAI tool call objects
    call_id = getattr(call, "id", None)
    function = getattr(call, "function", None)
    name = getattr(function, "name", None) if function is not None else None
    arguments = getattr(function, "arguments", None) if function is not None else None
    return call_id, name, arguments, function


def _render_format_error(template: str, *, error: str, template_vars: dict | None = None) -> str:
    template_vars = template_vars or {}
    return Template(template, undefined=StrictUndefined).render(error=error, actions=[], **template_vars)


def parse_toolcall_actions(
    tool_calls: list[Any] | None,
    *,
    format_error_template: str,
    template_vars: dict | None = None,
) -> list[dict]:
    if not tool_calls:
        raise FormatError(_render_format_error(format_error_template, error="No tool calls found.", template_vars=template_vars))

    actions: list[dict] = []
    for call in tool_calls:
        call_id, name, arguments, _ = _get_toolcall_fields(call)
        if name != BASH_TOOL["function"]["name"]:
            raise FormatError(
                _render_format_error(
                    format_error_template,
                    error=f"Unexpected tool '{name}', expected '{BASH_TOOL['function']['name']}'.",
                    template_vars=template_vars,
                )
            )
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as e:
                raise FormatError(
                    _render_format_error(
                        format_error_template,
                        error=f"Could not parse tool arguments JSON: {e}",
                        template_vars=template_vars,
                    )
                ) from e
        if not isinstance(arguments, dict) or "command" not in arguments:
            raise FormatError(
                _render_format_error(
                    format_error_template,
                    error="Tool call missing required 'command' argument.",
                    template_vars=template_vars,
                )
            )
        actions.append(
            {
                "tool": name,
                "args": arguments,
                "command": arguments["command"],
                "tool_call_id": call_id,
            }
        )
    return actions


def format_toolcall_observation_messages(
    outputs: list[dict],
    *,
    message: dict | None,
    observation_template: str,
    template_vars: dict | None = None,
) -> list[dict]:
    template_vars = template_vars or {}
    actions = []
    if message is not None:
        actions = message.get("actions", [])
    messages: list[dict] = []
    for action, output in zip(actions, outputs):
        content = Template(observation_template, undefined=StrictUndefined).render(
            output=output, action=action, **template_vars
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": action.get("tool_call_id"),
                "content": content,
            }
        )
    return messages


def build_tool_call(command: str, *, tool_call_id: str | None = None) -> dict:
    return {
        "id": tool_call_id or f"call_{uuid.uuid4().hex}",
        "type": "function",
        "function": {
            "name": BASH_TOOL["function"]["name"],
            "arguments": json.dumps({"command": command}),
        },
    }

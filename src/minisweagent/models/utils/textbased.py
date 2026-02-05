from __future__ import annotations

import re

from jinja2 import StrictUndefined, Template

from minisweagent.exceptions import FormatError
from minisweagent.models.utils.content_string import get_content_string


def _render_format_error(template: str, *, error: str, actions: list[str], template_vars: dict | None = None) -> str:
    template_vars = template_vars or {}
    return Template(template, undefined=StrictUndefined).render(error=error, actions=actions, **template_vars)


def parse_text_actions(
    message: dict,
    *,
    action_regex: str,
    format_error_template: str,
    template_vars: dict | None = None,
) -> list[dict]:
    content = get_content_string(message)
    actions = re.findall(action_regex, content, re.DOTALL)
    if len(actions) != 1:
        raise FormatError(
            _render_format_error(
                format_error_template,
                error=f"Expected exactly one action, found {len(actions)}.",
                actions=actions,
                template_vars=template_vars,
            )
        )
    command = actions[0].strip()
    return [{"tool": "bash", "command": command, "action": command}]


def format_text_observation_messages(
    outputs: list[dict],
    *,
    observation_template: str,
    template_vars: dict | None = None,
) -> list[dict]:
    template_vars = template_vars or {}
    messages: list[dict] = []
    for output in outputs:
        content = Template(observation_template, undefined=StrictUndefined).render(output=output, **template_vars)
        messages.append({"role": "user", "content": content})
    return messages


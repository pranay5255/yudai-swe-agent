from __future__ import annotations

import re
from typing import Any


def expand_multimodal_content(content: Any, multimodal_regex: str | None = None) -> Any:
    """Expand multimodal content if a regex is provided.

    This is a minimal implementation. If no regex is provided or content is not
    a string, content is returned unchanged.
    """
    if not multimodal_regex or not isinstance(content, str):
        return content

    matches = list(re.finditer(multimodal_regex, content))
    if not matches:
        return content

    parts: list[dict[str, Any]] = []
    last_idx = 0
    for match in matches:
        if match.start() > last_idx:
            parts.append({"type": "text", "text": content[last_idx : match.start()]})
        # prefer named group 'url', else first group
        url = match.groupdict().get("url") if match.groupdict() else None
        if url is None and match.groups():
            url = match.group(1)
        if url:
            parts.append({"type": "image_url", "image_url": {"url": url}})
        last_idx = match.end()
    if last_idx < len(content):
        parts.append({"type": "text", "text": content[last_idx:]})
    return parts


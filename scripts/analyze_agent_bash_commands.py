#!/usr/bin/env python3
"""Extract and categorize agent shell commands from EVMBench/Yudai run traces.

The trace formats in this repository are not uniform:
- Codex/OpenRouter runs store command executions in *-run.jsonl.
- OpenCode runs store bash calls plus structured read/glob/grep/edit tool calls.
- mini-swe-agent/Yudai trajectories store bash actions in messages.

This script keeps the raw invocation, derives a shell-ish inner command when the
agent used `/bin/bash -lc`, and also splits compound commands into coarse
segments for per-run category summaries.
"""

from __future__ import annotations

import csv
import json
import re
import shlex
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "evmbench_runs_download" / "bash_command_analysis"


UUID_SUFFIX = re.compile(
    r"^(?P<name>.+)_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
BASH_BLOCK = re.compile(r"```bash\s*\n(?P<cmd>.*?)\n```", re.DOTALL)


CATEGORY_ORDER = [
    "completion_marker",
    "report_submission",
    "exploit_execution",
    "build_test",
    "onchain_state_query",
    "file_write_edit",
    "text_search",
    "file_read_navigation",
    "git_vcs",
    "dependency_install",
    "runtime_script",
    "environment_process",
    "network_external",
    "structured_subagent",
    "shell_output_logging",
    "shell_control_flow",
    "other",
]

CATEGORY_DESCRIPTIONS = {
    "completion_marker": "Benchmark finalization marker, usually echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT.",
    "report_submission": "Writes, reads, or validates benchmark submission artifacts under submission/.",
    "exploit_execution": "Runs exploit transactions/scripts, especially forge script --broadcast or cast send.",
    "build_test": "Compiles or tests code, including forge test/build, hardhat tests, npm test, pytest.",
    "onchain_state_query": "Inspects fork/on-chain state with cast call/storage/balance/code/logs or selector utilities.",
    "file_write_edit": "Creates or edits files with redirection, heredocs, tee, apply_patch, cp/mv/rm, mkdir, chmod.",
    "text_search": "Searches source/log text with rg, grep, ack, ag, or similar tools.",
    "file_read_navigation": "Reads or lists files/directories with pwd, ls, cat, sed, find, head, tail, nl, wc, stat.",
    "git_vcs": "Uses git or GitHub CLI.",
    "dependency_install": "Installs or fetches project dependencies/packages.",
    "runtime_script": "Runs ad-hoc interpreters or scripts such as python, node, jq, awk, bash/sh.",
    "environment_process": "Inspects or changes runtime/container/process environment.",
    "network_external": "Attempts external network/service access such as curl, wget, gh issue view.",
    "structured_subagent": "OpenCode task/subagent tool invocation rather than a shell command.",
    "shell_output_logging": "Prints headings, diagnostics, or progress text with echo/printf.",
    "shell_control_flow": "Shell glue such as comments, conditionals, loops, function wrappers, true/false, and pure assignments.",
    "other": "No specific category matched.",
}


@dataclass
class RunMeta:
    source_family: str = ""
    batch: str = ""
    run_label: str = ""
    group: str = ""
    instance: str = ""
    benchmark: str = ""
    agent: str = ""
    model: str = ""
    mode: str = ""
    role: str = ""
    run_id: str = ""


@dataclass
class Invocation:
    source_path: str
    source_line: int | str
    source_format: str
    tool: str
    is_bash: bool
    raw_command: str
    inner_command: str
    workdir: str = ""
    description: str = ""
    status: str = ""
    exit_code: int | str | None = ""
    categories: list[str] = field(default_factory=list)
    primary_category: str = "other"
    meta: RunMeta = field(default_factory=RunMeta)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def strip_uuid_suffix(value: str) -> str:
    match = UUID_SUFFIX.match(value)
    return match.group("name") if match else value


def parse_run_label(label: str) -> tuple[str, str, str, str]:
    parts = label.split("--")
    if len(parts) >= 4:
        return parts[0], parts[1], parts[2], "--".join(parts[3:])
    return "", "", "", ""


def path_meta(path: Path) -> RunMeta:
    parts = path.relative_to(ROOT).parts
    meta = RunMeta()

    if parts[:1] == ("evmbench_runs_download",):
        meta.source_family = "evmbench_runs_download"
        meta.batch = "/".join(parts[1:3]) if len(parts) > 2 else parts[1] if len(parts) > 1 else ""

        if "evmbench_runs" in parts:
            idx = parts.index("evmbench_runs")
            meta.run_label = parts[idx + 1] if len(parts) > idx + 1 else ""
            meta.group = parts[idx + 2] if len(parts) > idx + 2 else ""
            meta.instance = parts[idx + 3] if len(parts) > idx + 3 else ""
            agent, model, mode, bench = parse_run_label(meta.run_label)
            meta.agent = agent
            meta.model = model
            meta.mode = mode
            meta.benchmark = strip_uuid_suffix(meta.instance) or bench
        elif "forest" in parts:
            meta.agent = "mini-swe-agent-forest"
            meta.mode = "detect"
            fidx = parts.index("forest")
            meta.role = "/".join(parts[fidx + 1 : -1])
            for part in parts:
                if UUID_SUFFIX.match(part):
                    meta.instance = part
                    meta.benchmark = strip_uuid_suffix(part)
                    break
            if not meta.benchmark:
                meta.benchmark = "unknown"
                meta.instance = "unknown"
        else:
            meta.agent = "unknown"

    elif parts[:4] == ("evmBench-frontier-evals", "project", "evmbench", "runs"):
        meta.source_family = "evmbench_native_runs"
        meta.agent = "yudai-minisweagent"
        meta.group = parts[4] if len(parts) > 4 else ""
        meta.instance = parts[5] if len(parts) > 5 else ""
        meta.benchmark = strip_uuid_suffix(meta.instance)
        if "_" in meta.group:
            meta.mode = meta.group.rsplit("_", 1)[-1]

    elif parts and parts[0].startswith("exploit_results"):
        meta.source_family = parts[0]
        meta.agent = "mini-swe-agent"
        meta.mode = "exploit"
        stem = path.stem.replace(".traj", "")
        meta.run_label = stem
        match = re.search(r"_1_(?P<bench>.+)$", stem)
        meta.benchmark = match.group("bench") if match else stem
        meta.instance = stem

    else:
        meta.source_family = parts[0] if parts else ""
        meta.agent = "unknown"
        meta.run_label = path.stem
        meta.instance = path.stem
        meta.benchmark = path.stem

    pieces = [
        meta.source_family,
        meta.batch,
        meta.agent,
        meta.model,
        meta.mode,
        meta.benchmark,
        meta.role,
        meta.group,
        meta.instance,
    ]
    meta.run_id = "|".join(piece for piece in pieces if piece)
    return meta


def iter_trace_files() -> Iterable[Path]:
    include_roots = [
        ROOT / "evmbench_runs_download",
        ROOT / "evmBench-frontier-evals" / "project" / "evmbench" / "runs",
        ROOT / "exploit_results",
        ROOT / "exploit_results_v3",
        ROOT / "exploit_results_live_v3",
    ]
    for base in include_roots:
        if not base.exists():
            continue
        yield from base.rglob("*.traj.json")
        yield from base.rglob("*-run.jsonl")


def load_json(path: Path) -> Any | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return json.load(handle)
    except Exception:
        return None


def json_arg_object(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if not isinstance(arguments, str):
        return {}
    try:
        loaded = json.loads(arguments)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def extract_inner_command(raw: str) -> str:
    text = raw.strip()
    try:
        tokens = shlex.split(text)
    except Exception:
        return text
    if len(tokens) >= 3 and Path(tokens[0]).name in {"bash", "sh"} and tokens[1] in {"-lc", "-c"}:
        return tokens[2]
    return text


def first_token(segment: str) -> str:
    try:
        tokens = shlex.split(segment, comments=False, posix=True)
    except Exception:
        tokens = segment.strip().split()
    if not tokens:
        return ""
    token = Path(tokens[0]).name.strip()
    return token.lstrip("(\\").rstrip(")")


def split_shell_segments(command: str) -> list[str]:
    text = command.strip()
    if not text:
        return []
    if "<<" in text:
        return [text]

    segments: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if escaped:
            buf.append(ch)
            escaped = False
            i += 1
            continue
        if ch == "\\":
            buf.append(ch)
            escaped = True
            i += 1
            continue
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\n" or ch == ";" or ch == "|":
            segment = "".join(buf).strip()
            if segment:
                segments.append(segment)
            buf = []
            if ch == "|" and nxt == "|":
                i += 2
            else:
                i += 1
            continue
        if ch == "&" and nxt == "&":
            segment = "".join(buf).strip()
            if segment:
                segments.append(segment)
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        segments.append(tail)
    return segments or [text]


def category_set(command: str, tool: str = "bash", is_bash: bool = True) -> set[str]:
    text = command.strip()
    low = text.lower()
    token = first_token(text)
    cats: set[str] = set()
    pure_assignment = bool(re.fullmatch(r"(?:[A-Za-z_][A-Za-z0-9_]*=(?:[^;\s]+|\"[^\"]*\"|'[^']*')\s*)+", text))

    if not is_bash:
        if tool == "task":
            return {"structured_subagent"}
        if tool in {"read", "glob"}:
            return {"file_read_navigation"}
        if tool == "grep":
            return {"text_search"}
        if tool in {"edit", "apply_patch", "write"}:
            return {"file_write_edit"}
        return {"other"}

    if "complete_task_and_submit_final_output" in low:
        cats.add("completion_marker")
    if "submission/" in low or "/submission/" in low:
        cats.add("report_submission")
    if token in {"append", "add", "append_finding", "add_finding", "write_finding", "append_report"}:
        cats.update({"report_submission", "file_write_edit"})
    if re.search(r"\bforge\s+script\b", low) or "--broadcast" in low or re.search(r"\bcast\s+send\b", low):
        cats.add("exploit_execution")
    if re.search(r"\b(forge\s+(test|build|compile|coverage|inspect|clean|--version)|hardhat\s+(test|compile)|npx\s+hardhat\s+(test|compile)|npm\s+(test|run\s+compile|-s\s+run\s+compile)|yarn\s+test|pnpm\s+test|pytest|cargo\s+test|solc\b)\b", low):
        cats.add("build_test")
    if token == "cast" or re.search(r"\bcast\s+(call|storage|balance|code|block|block-number|logs|sig|4byte|abi-decode|abi-encode|calldata|index|keccak|nonce|tx|receipt|run|disassemble|mktx)\b", low):
        cats.add("onchain_state_query")
    if (
        "<<" in text
        or re.search(r"(^|[^<])>>?", text)
        or token in {"tee", "apply_patch", "touch", "mkdir", "cp", "mv", "rm", "chmod"}
    ):
        cats.add("file_write_edit")
    if token in {"rg", "grep", "ack", "ag"} or re.search(r"\b(rg|grep|ack|ag)\b", low):
        cats.add("text_search")
    if token in {"pwd", "ls", "cat", "sed", "head", "tail", "nl", "less", "more", "tree", "find", "wc", "file", "du", "stat", "sort", "cut", "xxd", "strings", "tr", "fold"} or re.search(r"\b(find|sed|cat|head|tail|nl|wc|sort)\b", low):
        cats.add("file_read_navigation")
    if token in {"git", "gh"}:
        cats.add("git_vcs")
    if re.search(r"\b(npm\s+(install|ci)|pnpm\s+install|yarn\s+install|forge\s+install|pip\s+install|uv\s+add|apt(-get)?\s+install)\b", low):
        cats.add("dependency_install")
    if token in {"python", "python3", "node", "jq", "awk", "perl", "ruby", "bash", "sh"}:
        cats.add("runtime_script")
    if token in {"docker", "ps", "kill", "env", "export", "set", "cd", "which", "command", "printenv", "sleep", "date", "anvil", "pkill", "pgrep", "write_stdin"} or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
        cats.add("environment_process")
    if token in {"curl", "wget"} or low.startswith("gh issue") or low.startswith("gh api") or re.search(r"\bnpm\s+view\b", low):
        cats.add("network_external")
    if token in {"echo", "printf"}:
        cats.add("shell_output_logging")
    if (
        pure_assignment
        or token.rstrip(")") in {"#", "[", "if", "then", "else", "elif", "fi", "for", "do", "done", "while", "case", "esac", "function", "true", "false", "break", "continue", "exit", "{", "}"}
        or text.endswith("() {")
        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{", text)
    ):
        cats.add("shell_control_flow")

    return cats or {"other"}


def primary_category(categories: Iterable[str]) -> str:
    cats = set(categories)
    for category in CATEGORY_ORDER:
        if category in cats:
            return category
    return "other"


def pseudo_tool_command(tool: str, input_obj: dict[str, Any]) -> str:
    if tool == "read":
        path = input_obj.get("filePath") or input_obj.get("path") or ""
        offset = input_obj.get("offset")
        limit = input_obj.get("limit")
        suffix = f" offset={offset} limit={limit}" if offset is not None or limit is not None else ""
        return f"read {path}{suffix}".strip()
    if tool == "glob":
        return f"glob {input_obj.get('path', '')} {input_obj.get('pattern', '')}".strip()
    if tool == "grep":
        return f"grep {input_obj.get('pattern', '')} {input_obj.get('path', '')}".strip()
    if tool == "task":
        return f"task {input_obj.get('description', '')}".strip()
    if tool in {"edit", "apply_patch", "write"}:
        target = input_obj.get("filePath") or input_obj.get("path") or input_obj.get("file") or ""
        return f"{tool} {target}".strip()
    return tool


def make_invocation(
    path: Path,
    source_line: int | str,
    source_format: str,
    tool: str,
    raw_command: str,
    *,
    is_bash: bool = True,
    workdir: str = "",
    description: str = "",
    status: str = "",
    exit_code: int | str | None = "",
) -> Invocation:
    inner = extract_inner_command(raw_command) if is_bash else raw_command.strip()
    categories = sorted(category_set(inner, tool, is_bash), key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 99)
    return Invocation(
        source_path=rel(path),
        source_line=source_line,
        source_format=source_format,
        tool=tool,
        is_bash=is_bash,
        raw_command=raw_command.strip(),
        inner_command=inner,
        workdir=workdir,
        description=description,
        status=status,
        exit_code=exit_code if exit_code is not None else "",
        categories=categories,
        primary_category=primary_category(categories),
        meta=path_meta(path),
    )


def extract_jsonl(path: Path) -> list[Invocation]:
    records: list[Invocation] = []
    pending: dict[str, tuple[int, dict[str, Any]]] = {}
    completed_ids: set[str] = set()

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            try:
                event = json.loads(line)
            except Exception:
                continue

            item = event.get("item") if isinstance(event, dict) else None
            if isinstance(item, dict) and item.get("type") == "command_execution":
                item_id = str(item.get("id", f"line-{line_no}"))
                if event.get("type") == "item.completed":
                    completed_ids.add(item_id)
                    records.append(
                        make_invocation(
                            path,
                            line_no,
                            "codex-run-jsonl",
                            "bash",
                            item.get("command", ""),
                            is_bash=True,
                            status=str(item.get("status", "")),
                            exit_code=item.get("exit_code", ""),
                        )
                    )
                elif event.get("type") == "item.started":
                    pending[item_id] = (line_no, item)
                continue

            part = event.get("part") if isinstance(event, dict) else None
            if isinstance(part, dict) and event.get("type") == "tool_use":
                tool = str(part.get("tool", ""))
                state = part.get("state") if isinstance(part.get("state"), dict) else {}
                input_obj = state.get("input") if isinstance(state.get("input"), dict) else {}
                metadata = state.get("metadata") if isinstance(state.get("metadata"), dict) else {}
                if tool == "bash":
                    records.append(
                        make_invocation(
                            path,
                            line_no,
                            "opencode-run-jsonl",
                            "bash",
                            input_obj.get("command", ""),
                            is_bash=True,
                            workdir=str(input_obj.get("workdir", "")),
                            description=str(input_obj.get("description", "")),
                            status=str(state.get("status", "")),
                            exit_code=metadata.get("exit", ""),
                        )
                    )
                elif tool in {"read", "glob", "grep", "edit", "apply_patch", "write", "task"}:
                    pseudo = pseudo_tool_command(tool, input_obj)
                    records.append(
                        make_invocation(
                            path,
                            line_no,
                            "opencode-run-jsonl",
                            tool,
                            pseudo,
                            is_bash=False,
                            description=str(input_obj.get("description", "")),
                            status=str(state.get("status", "")),
                            exit_code=metadata.get("exit", ""),
                        )
                    )

    for item_id, (line_no, item) in pending.items():
        if item_id not in completed_ids:
            records.append(
                make_invocation(
                    path,
                    line_no,
                    "codex-run-jsonl",
                    "bash",
                    item.get("command", ""),
                    is_bash=True,
                    status=str(item.get("status", "")),
                    exit_code=item.get("exit_code", ""),
                )
            )

    return [record for record in records if record.raw_command]


def extract_traj(path: Path) -> list[Invocation]:
    data = load_json(path)
    if not isinstance(data, dict):
        return []
    messages = data.get("messages")
    if not isinstance(messages, list):
        return []

    tool_returns: dict[str, Any] = {}
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "tool":
            call_id = str(message.get("tool_call_id", ""))
            extra = message.get("extra") if isinstance(message.get("extra"), dict) else {}
            if call_id:
                tool_returns[call_id] = extra.get("returncode", "")

    records: list[Invocation] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue

        emitted = False
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            for call in tool_calls:
                function = call.get("function") if isinstance(call, dict) else None
                if not isinstance(function, dict) or function.get("name") != "bash":
                    continue
                args = json_arg_object(function.get("arguments"))
                call_id = str(call.get("id", ""))
                records.append(
                    make_invocation(
                        path,
                        index,
                        "traj-tool-call",
                        "bash",
                        str(args.get("command", "")),
                        is_bash=True,
                        exit_code=tool_returns.get(call_id, ""),
                    )
                )
                emitted = True

        if not emitted:
            for action_key in ("actions",):
                actions = message.get(action_key)
                if isinstance(actions, list):
                    for action in actions:
                        if not isinstance(action, dict):
                            continue
                        tool = str(action.get("tool", "bash"))
                        command = action.get("command") or action.get("action") or ""
                        if tool == "bash" and command:
                            records.append(
                                make_invocation(path, index, "traj-action", "bash", str(command), is_bash=True)
                            )
                            emitted = True

        extra = message.get("extra") if isinstance(message.get("extra"), dict) else {}
        extra_actions = extra.get("actions")
        if not emitted and isinstance(extra_actions, list):
            for action in extra_actions:
                if not isinstance(action, dict):
                    continue
                command = action.get("command") or action.get("action") or ""
                if command:
                    records.append(
                        make_invocation(path, index, "traj-extra-action", "bash", str(command), is_bash=True)
                    )
                    emitted = True

        if not emitted:
            content = message.get("content")
            if isinstance(content, str):
                for match in BASH_BLOCK.finditer(content):
                    records.append(
                        make_invocation(path, index, "traj-bash-code-block", "bash", match.group("cmd"), is_bash=True)
                    )

    deduped: list[Invocation] = []
    seen: set[tuple[str, int | str, str, str]] = set()
    for record in records:
        if not record.raw_command:
            continue
        key = (record.source_path, record.source_line, record.tool, record.raw_command)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def invocation_rows(records: list[Invocation]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, record in enumerate(records, 1):
        rows.append(
            {
                "invocation_id": idx,
                "run_id": record.meta.run_id,
                "source_family": record.meta.source_family,
                "batch": record.meta.batch,
                "agent": record.meta.agent,
                "model": record.meta.model,
                "mode": record.meta.mode,
                "benchmark": record.meta.benchmark,
                "role": record.meta.role,
                "tool": record.tool,
                "is_bash": record.is_bash,
                "primary_category": record.primary_category,
                "categories": "|".join(record.categories),
                "exit_code": record.exit_code,
                "status": record.status,
                "workdir": record.workdir,
                "description": record.description,
                "inner_command": record.inner_command,
                "raw_command": record.raw_command,
                "source_path": record.source_path,
                "source_line": record.source_line,
                "source_format": record.source_format,
            }
        )
    return rows


def segment_rows(records: list[Invocation]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    segment_id = 1
    for invocation_id, record in enumerate(records, 1):
        segments = split_shell_segments(record.inner_command) if record.is_bash else [record.inner_command]
        for pos, segment in enumerate(segments, 1):
            cats = sorted(
                category_set(segment, record.tool, record.is_bash),
                key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 99,
            )
            rows.append(
                {
                    "segment_id": segment_id,
                    "invocation_id": invocation_id,
                    "run_id": record.meta.run_id,
                    "source_family": record.meta.source_family,
                    "agent": record.meta.agent,
                    "mode": record.meta.mode,
                    "benchmark": record.meta.benchmark,
                    "role": record.meta.role,
                    "tool": record.tool,
                    "is_bash": record.is_bash,
                    "segment_position": pos,
                    "primary_category": primary_category(cats),
                    "categories": "|".join(cats),
                    "first_token": first_token(segment),
                    "segment": segment,
                    "source_path": record.source_path,
                    "source_line": record.source_line,
                }
            )
            segment_id += 1
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def top_counter_rows(counter: Counter[tuple[Any, ...]], headers: list[str]) -> list[dict[str, Any]]:
    rows = []
    for key, count in counter.most_common():
        if not isinstance(key, tuple):
            key = (key,)
        row = {header: value for header, value in zip(headers, key)}
        row["count"] = count
        rows.append(row)
    return rows


def markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    if not selected:
        return "_No rows._\n"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in selected:
        values = []
        for col in columns:
            value = str(row.get(col, ""))
            value = value.replace("\n", " ").replace("|", "\\|")
            if len(value) > 100:
                value = value[:97] + "..."
            values.append(value)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def write_report(records: list[Invocation], seg_rows: list[dict[str, Any]], source_files: list[str]) -> None:
    all_inv_rows = invocation_rows(records)
    bash_records = [record for record in records if record.is_bash]
    structured_records = [record for record in records if not record.is_bash]
    bash_segments = [row for row in seg_rows if row["is_bash"]]

    by_segment_category = Counter(row["primary_category"] for row in bash_segments)
    by_invocation_category = Counter(row["primary_category"] for row in all_inv_rows)
    by_agent_mode = Counter((row["agent"], row["mode"], row["primary_category"]) for row in all_inv_rows)

    per_run_counter: Counter[tuple[str, str, str, str, str, str]] = Counter()
    for row in seg_rows:
        per_run_counter[
            (
                row["run_id"],
                row["source_family"],
                row["agent"],
                row["mode"],
                row["benchmark"],
                row["primary_category"],
            )
        ] += 1
    per_run_rows = top_counter_rows(
        per_run_counter,
        ["run_id", "source_family", "agent", "mode", "benchmark", "primary_category"],
    )

    top_tokens = Counter(row["first_token"] for row in bash_segments if row["first_token"])
    failed = [
        row
        for row in all_inv_rows
        if str(row.get("exit_code", "")) not in {"", "0", "None"} or str(row.get("status", "")).lower() in {"failed", "error"}
    ]

    report = []
    report.append("# Agent Bash Command Analysis\n")
    report.append("## Scope\n")
    report.append(f"- Trace files scanned: {len(source_files)}\n")
    report.append(f"- Total extracted invocations/tools: {len(records)}\n")
    report.append(f"- Actual bash/shell invocations: {len(bash_records)}\n")
    report.append(f"- Structured OpenCode non-bash tool invocations: {len(structured_records)}\n")
    report.append(f"- Bash command segments after splitting compound commands: {len(bash_segments)}\n")
    report.append(f"- Distinct runs with at least one extracted invocation: {len({record.meta.run_id for record in records})}\n")
    report.append("\nGenerated files:\n")
    report.append("- `command_invocations.csv`: one row per bash or structured tool invocation.\n")
    report.append("- `command_segments.csv`: one row per split shell segment/pseudo-tool.\n")
    report.append("- `per_run_category_summary.csv`: complete per-run category counts.\n")
    report.append("- `category_taxonomy.json`: category definitions.\n")

    report.append("\n## Taxonomy\n")
    for category in CATEGORY_ORDER:
        report.append(f"- `{category}`: {CATEGORY_DESCRIPTIONS[category]}\n")

    report.append("\n## Bash Segment Categories\n")
    report.append(
        markdown_table(
            [{"primary_category": key, "segments": value} for key, value in by_segment_category.most_common()],
            ["primary_category", "segments"],
        )
    )

    report.append("\n## All Invocation Categories\n")
    report.append(
        markdown_table(
            [{"primary_category": key, "invocations": value} for key, value in by_invocation_category.most_common()],
            ["primary_category", "invocations"],
        )
    )

    report.append("\n## Category By Agent And Mode\n")
    agent_rows = top_counter_rows(by_agent_mode, ["agent", "mode", "primary_category"])
    report.append(markdown_table(agent_rows, ["agent", "mode", "primary_category", "count"], limit=80))

    report.append("\n## Top Bash First Tokens\n")
    report.append(
        markdown_table(
            [{"first_token": key, "segments": value} for key, value in top_tokens.most_common(50)],
            ["first_token", "segments"],
        )
    )

    report.append("\n## Per-Run Category Counts\n")
    report.append("The table below is truncated to the top 120 rows; see `per_run_category_summary.csv` for all rows.\n\n")
    report.append(
        markdown_table(
            per_run_rows,
            ["source_family", "agent", "mode", "benchmark", "primary_category", "count"],
            limit=120,
        )
    )

    report.append("\n## Failed Or Unavailable Commands\n")
    report.append("Rows with non-zero exit codes or failed statuses, truncated to 80 rows.\n\n")
    report.append(
        markdown_table(
            failed,
            ["agent", "mode", "benchmark", "primary_category", "exit_code", "inner_command", "source_path"],
            limit=80,
        )
    )

    (OUT_DIR / "report.md").write_text("".join(report), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_files = sorted(set(iter_trace_files()))

    records: list[Invocation] = []
    for path in source_files:
        if path.name.endswith(".jsonl"):
            records.extend(extract_jsonl(path))
        elif path.name.endswith(".traj.json"):
            records.extend(extract_traj(path))

    records.sort(key=lambda record: (record.meta.run_id, record.source_path, int(record.source_line) if str(record.source_line).isdigit() else 0))
    inv_rows = invocation_rows(records)
    seg_rows = segment_rows(records)

    write_csv(OUT_DIR / "command_invocations.csv", inv_rows)
    write_csv(OUT_DIR / "command_segments.csv", seg_rows)

    per_run_counter: Counter[tuple[str, str, str, str, str, str, str]] = Counter()
    for row in seg_rows:
        per_run_counter[
            (
                row["run_id"],
                row["source_family"],
                row["agent"],
                row["mode"],
                row["benchmark"],
                row["role"],
                row["primary_category"],
            )
        ] += 1
    per_run_rows = top_counter_rows(
        per_run_counter,
        ["run_id", "source_family", "agent", "mode", "benchmark", "role", "primary_category"],
    )
    write_csv(OUT_DIR / "per_run_category_summary.csv", per_run_rows)

    taxonomy = {category: CATEGORY_DESCRIPTIONS[category] for category in CATEGORY_ORDER}
    (OUT_DIR / "category_taxonomy.json").write_text(json.dumps(taxonomy, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "source_files.json").write_text(
        json.dumps([rel(path) for path in source_files], indent=2) + "\n",
        encoding="utf-8",
    )

    write_report(records, seg_rows, [rel(path) for path in source_files])

    print(f"Trace files scanned: {len(source_files)}")
    print(f"Invocations/tools extracted: {len(records)}")
    print(f"Bash invocations: {sum(1 for record in records if record.is_bash)}")
    print(f"Structured non-bash tools: {sum(1 for record in records if not record.is_bash)}")
    print(f"Output directory: {rel(OUT_DIR)}")


if __name__ == "__main__":
    main()

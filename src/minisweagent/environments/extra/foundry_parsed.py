"""Foundry environment with lightweight output parsing for blockchain commands."""

from __future__ import annotations

import json
import re
from typing import Any

from minisweagent.environments.foundry import FoundryEnvironment


class BlockchainCommandParser:
    """Parse common Foundry/chain command outputs into concise summaries."""

    _SOLC_ERROR_BLOCK = re.compile(
        r"(?:Error|ParserError|TypeError|CompilerError|DeclarationError|SyntaxError)"
        r"(?:\s*\(\d+\))?:\s*(?P<msg>.+?)\n\s*-->\s*(?P<file>[^:]+):(?P<line>\d+):\d+",
        re.DOTALL,
    )
    _FORGE_TEST_RESULT = re.compile(
        r"Test result:\s*(?P<status>ok|FAILED)\.\s*"
        r"(?P<passed>\d+)\s+passed;\s*(?P<failed>\d+)\s+failed;\s*(?P<skipped>\d+)\s+skipped",
        re.IGNORECASE,
    )
    _FORGE_FAIL = re.compile(
        r"\[FAIL(?::\s*(?P<reason>[^\]]+))?\]\s*(?P<name>\S+)",
        re.IGNORECASE,
    )
    _ANVIL_LISTEN = re.compile(r"Listening on\s+(?P<addr>\S+)", re.IGNORECASE)
    _TX_HASH = re.compile(r"(?:Transaction hash|tx hash|hash):\s*(0x[a-fA-F0-9]{64})")

    def parse(self, command: str, result: dict[str, Any]) -> dict[str, Any] | None:
        output = result.get("output", "") or ""
        returncode = int(result.get("returncode", 1))
        cmd = " ".join(command.strip().split())
        kind = self._detect_kind(cmd)
        if not kind:
            return None

        if kind == "forge_build":
            return self._parse_forge_build(output, returncode)
        if kind == "forge_test":
            return self._parse_forge_test(output, returncode)
        if kind == "forge_script":
            return self._parse_forge_script(output, returncode)
        if kind == "slither":
            return self._parse_slither(output, returncode)
        if kind == "cast_call":
            return self._parse_cast_call(output, returncode)
        if kind == "cast_send":
            return self._parse_cast_send(output, returncode)
        if kind == "cast_balance":
            return self._parse_cast_balance(output, returncode)
        if kind == "anvil":
            return self._parse_anvil(output, returncode)
        return None

    def _detect_kind(self, cmd: str) -> str | None:
        subcommands = re.split(r"\s*&&\s*|\s*;\s*", cmd)
        for subcmd in subcommands:
            if re.search(r"\bforge\s+build\b", subcmd):
                return "forge_build"
            if re.search(r"\bforge\s+test\b", subcmd):
                return "forge_test"
            if re.search(r"\bforge\s+script\b", subcmd):
                return "forge_script"
            if re.search(r"\bslither\b", subcmd):
                return "slither"
            if re.search(r"\bcast\s+call\b", subcmd):
                return "cast_call"
            if re.search(r"\bcast\s+send\b", subcmd):
                return "cast_send"
            if re.search(r"\bcast\s+balance\b", subcmd):
                return "cast_balance"
            if re.search(r"\banvil\b", subcmd):
                return "anvil"
        return None

    def _parse_forge_build(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode == 0:
            return {"kind": "forge_build", "summary": "forge build: success", "details": {}}

        errors = []
        for match in self._SOLC_ERROR_BLOCK.finditer(output):
            errors.append(
                {
                    "file": match.group("file").strip(),
                    "line": int(match.group("line")),
                    "message": match.group("msg").strip().splitlines()[0],
                }
            )

        if not errors:
            summary = "forge build: failed (no parser match)"
            return {"kind": "forge_build", "summary": summary, "details": {}}

        lines = [f"forge build: failed ({len(errors)} error(s))"]
        for err in errors[:3]:
            lines.append(f"- {err['file']}:{err['line']} {err['message']}")
        return {"kind": "forge_build", "summary": "\n".join(lines), "details": {"errors": errors}}

    def _parse_forge_test(self, output: str, returncode: int) -> dict[str, Any]:
        summary_lines = []
        result = self._FORGE_TEST_RESULT.search(output)
        if result:
            summary_lines.append(
                "forge test: "
                f"{result.group('passed')} passed, "
                f"{result.group('failed')} failed, "
                f"{result.group('skipped')} skipped"
            )
        else:
            summary_lines.append("forge test: failed" if returncode else "forge test: completed")

        failures = []
        for match in self._FORGE_FAIL.finditer(output):
            failures.append(
                {
                    "name": match.group("name"),
                    "reason": (match.group("reason") or "").strip(),
                }
            )
        if failures:
            summary_lines.append("failing tests:")
            for failure in failures[:3]:
                reason = f" - {failure['reason']}" if failure["reason"] else ""
                summary_lines.append(f"- {failure['name']}{reason}")

        return {"kind": "forge_test", "summary": "\n".join(summary_lines), "details": {"failures": failures}}

    def _parse_forge_script(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            error_line = self._first_error_line(output)
            summary = f"forge script: failed - {error_line}" if error_line else "forge script: failed"
            return {"kind": "forge_script", "summary": summary, "details": {}}

        tx_hash = self._TX_HASH.search(output)
        if tx_hash:
            summary = f"forge script: success (tx {tx_hash.group(1)})"
        else:
            summary = "forge script: success"
        return {"kind": "forge_script", "summary": summary, "details": {}}

    def _parse_slither(self, output: str, returncode: int) -> dict[str, Any]:
        data = self._extract_json(output)
        if data and isinstance(data, dict):
            detectors = data.get("results", {}).get("detectors", [])
            impact_counts = {}
            for det in detectors:
                impact = (det.get("impact") or "unknown").lower()
                impact_counts[impact] = impact_counts.get(impact, 0) + 1
            summary = [
                f"slither: {len(detectors)} findings",
                ", ".join(f"{k}={v}" for k, v in sorted(impact_counts.items())),
            ]
            return {
                "kind": "slither",
                "summary": "\n".join(s for s in summary if s),
                "details": {"counts": impact_counts},
            }

        if returncode != 0:
            return {"kind": "slither", "summary": "slither: failed", "details": {}}
        return {"kind": "slither", "summary": "slither: completed", "details": {}}

    def _parse_cast_call(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            return {"kind": "cast_call", "summary": "cast call: failed", "details": {}}
        first_line = output.strip().splitlines()[:1]
        summary = f"cast call: {first_line[0]}" if first_line else "cast call: success"
        return {"kind": "cast_call", "summary": summary, "details": {}}

    def _parse_cast_send(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            return {"kind": "cast_send", "summary": "cast send: failed", "details": {}}
        tx_hash = self._TX_HASH.search(output)
        summary = f"cast send: {tx_hash.group(1)}" if tx_hash else "cast send: success"
        return {"kind": "cast_send", "summary": summary, "details": {}}

    def _parse_cast_balance(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            return {"kind": "cast_balance", "summary": "cast balance: failed", "details": {}}
        first_line = output.strip().splitlines()[:1]
        summary = f"cast balance: {first_line[0]}" if first_line else "cast balance: success"
        return {"kind": "cast_balance", "summary": summary, "details": {}}

    def _parse_anvil(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            return {"kind": "anvil", "summary": "anvil: failed", "details": {}}
        match = self._ANVIL_LISTEN.search(output)
        if match:
            summary = f"anvil: listening on {match.group('addr')}"
        else:
            summary = "anvil: started"
        return {"kind": "anvil", "summary": summary, "details": {}}

    def _extract_json(self, output: str) -> dict[str, Any] | None:
        start = output.find("{")
        end = output.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        blob = output[start : end + 1]
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            return None

    def _first_error_line(self, output: str) -> str | None:
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if "error" in line.lower() or "revert" in line.lower():
                return line[:200]
        return None


class ParsedFoundryEnvironment(FoundryEnvironment):
    """Foundry environment with parsing for blockchain command outputs."""

    def __init__(self, *args, parser: BlockchainCommandParser | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._parser = parser or BlockchainCommandParser()

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        result = super().execute(command, cwd=cwd, timeout=timeout)
        parsed = self._parser.parse(command, result)
        if not parsed:
            return result

        result = dict(result)
        result["parsed"] = parsed
        result.setdefault("raw_output", result.get("output", ""))
        result["output"] = parsed.get("summary", result["output"])
        return result

"""Foundry environment with lightweight output parsing for blockchain commands."""

from __future__ import annotations

import json
import re
import shlex
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
    _EIP1559_ERROR = re.compile(
        r"(eip-1559|unsupported feature: eip1559|max fee per gas|fee cap)",
        re.IGNORECASE,
    )
    _HEX_32 = re.compile(r"^0x[a-fA-F0-9]{64}$")
    _HEX_BLOB = re.compile(r"^0x[a-fA-F0-9]+$")
    _ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

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
        if kind == "cast_storage":
            return self._parse_cast_storage(output, returncode)
        if kind == "cast_send":
            return self._parse_cast_send(output, returncode)
        if kind == "cast_balance":
            return self._parse_cast_balance(output, returncode)
        if kind == "cast_code":
            return self._parse_cast_code(output, returncode)
        if kind == "cast_abi_decode":
            return self._parse_cast_abi_decode(output, returncode)
        if kind == "cast_rpc":
            return self._parse_cast_rpc(output, returncode)
        if kind == "anvil":
            return self._parse_anvil(output, returncode)
        return None

    def _detect_kind(self, cmd: str) -> str | None:
        subcommands = re.split(r"\s*&&\s*|\s*;\s*", cmd)
        for subcmd in subcommands:
            tool, args = self._extract_tool_and_args(subcmd)
            if tool == "forge" and args[:1] == ["build"]:
                return "forge_build"
            if tool == "forge" and args[:1] == ["test"]:
                return "forge_test"
            if tool == "forge" and args[:1] == ["script"]:
                return "forge_script"
            if tool == "slither":
                return "slither"
            if tool == "cast" and args[:1] == ["call"]:
                return "cast_call"
            if tool == "cast" and args[:1] == ["storage"]:
                return "cast_storage"
            if tool == "cast" and args[:1] == ["send"]:
                return "cast_send"
            if tool == "cast" and args[:1] == ["balance"]:
                return "cast_balance"
            if tool == "cast" and args[:1] == ["code"]:
                return "cast_code"
            if tool == "cast" and args[:1] == ["abi-decode"]:
                return "cast_abi_decode"
            if tool == "cast" and args[:1] == ["rpc"]:
                return "cast_rpc"
            if tool == "anvil":
                return "anvil"
        return None

    def _extract_tool_and_args(self, subcmd: str) -> tuple[str, list[str]]:
        try:
            tokens = shlex.split(subcmd)
        except ValueError:
            tokens = subcmd.strip().split()

        if not tokens:
            return "", []

        while tokens and self._ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
        while tokens and tokens[0] in {"nohup", "command", "builtin", "time"}:
            tokens = tokens[1:]

        if not tokens:
            return "", []

        return tokens[0], tokens[1:]

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
            error = self._first_error_line(output)
            summary = f"cast call: failed - {error}" if error else "cast call: failed"
            return {"kind": "cast_call", "summary": summary, "details": {}}
        return self._parse_cast_scalar_output("cast_call", "cast call", output)

    def _parse_cast_storage(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            error = self._first_error_line(output)
            summary = f"cast storage: failed - {error}" if error else "cast storage: failed"
            return {"kind": "cast_storage", "summary": summary, "details": {}}
        return self._parse_cast_scalar_output("cast_storage", "cast storage", output)

    def _parse_cast_send(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            if self._EIP1559_ERROR.search(output):
                return {
                    "kind": "cast_send",
                    "summary": "cast send: failed (EIP-1559 unsupported; try --legacy)",
                    "details": {},
                }
            error = self._first_error_line(output)
            summary = f"cast send: failed - {error}" if error else "cast send: failed"
            return {"kind": "cast_send", "summary": summary, "details": {}}
        tx_hash = self._TX_HASH.search(output)
        summary = f"cast send: {tx_hash.group(1)}" if tx_hash else "cast send: success"
        return {"kind": "cast_send", "summary": summary, "details": {}}

    def _parse_cast_balance(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            error = self._first_error_line(output)
            summary = f"cast balance: failed - {error}" if error else "cast balance: failed"
            return {"kind": "cast_balance", "summary": summary, "details": {}}
        first_line = self._meaningful_lines(output)[:1]
        summary = f"cast balance: {first_line[0]}" if first_line else "cast balance: success"
        return {"kind": "cast_balance", "summary": summary, "details": {}}

    def _parse_cast_code(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            error = self._first_error_line(output)
            summary = f"cast code: failed - {error}" if error else "cast code: failed"
            return {"kind": "cast_code", "summary": summary, "details": {}}
        first_line = self._meaningful_lines(output)[:1]
        if first_line and self._HEX_BLOB.match(first_line[0]):
            code = first_line[0]
            size = max(0, (len(code) - 2) // 2)
            return {
                "kind": "cast_code",
                "summary": f"cast code: {size} bytes",
                "details": {"code_size": size},
            }
        summary = f"cast code: {first_line[0]}" if first_line else "cast code: success"
        return {"kind": "cast_code", "summary": summary, "details": {}}

    def _parse_cast_abi_decode(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            error = self._first_error_line(output)
            summary = f"cast abi-decode: failed - {error}" if error else "cast abi-decode: failed"
            return {"kind": "cast_abi_decode", "summary": summary, "details": {}}
        first_line = self._meaningful_lines(output)[:1]
        summary = f"cast abi-decode: {first_line[0]}" if first_line else "cast abi-decode: success"
        return {"kind": "cast_abi_decode", "summary": summary, "details": {}}

    def _parse_cast_rpc(self, output: str, returncode: int) -> dict[str, Any]:
        if returncode != 0:
            error = self._first_error_line(output)
            summary = f"cast rpc: failed - {error}" if error else "cast rpc: failed"
            return {"kind": "cast_rpc", "summary": summary, "details": {}}
        first_line = self._meaningful_lines(output)[:1]
        summary = f"cast rpc: {first_line[0]}" if first_line else "cast rpc: success"
        return {"kind": "cast_rpc", "summary": summary, "details": {}}

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
        for line in self._meaningful_lines(output):
            line = line.strip()
            if not line:
                continue
            lowered = line.lower()
            if self._EIP1559_ERROR.search(line):
                return line[:200]
            if (
                "error" in lowered
                or "revert" in lowered
                or "failed" in lowered
                or "invalid" in lowered
                or "parse" in lowered
            ):
                return line[:200]
        return None

    def _parse_cast_scalar_output(self, kind: str, label: str, output: str) -> dict[str, Any]:
        first_line = self._meaningful_lines(output)[:1]
        summary = f"{label}: {first_line[0]}" if first_line else f"{label}: success"
        details: dict[str, Any] = {}
        if first_line and self._HEX_32.match(first_line[0]):
            decoded = self._decode_padded_address(first_line[0])
            if decoded:
                details["decoded_address"] = decoded
                summary = f"{summary} (address {decoded})"
            details["decoded_uint256"] = int(first_line[0], 16)
            if details["decoded_uint256"] in {0, 1}:
                details["decoded_bool_candidate"] = bool(details["decoded_uint256"])
        return {"kind": kind, "summary": summary, "details": details}

    def _meaningful_lines(self, output: str) -> list[str]:
        lines = []
        for line in output.strip().splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            if lowered.startswith(("warning:", "info:", "note:")):
                continue
            if "nightly build" in lowered or "recommended to use" in lowered:
                continue
            lines.append(stripped)
        return lines

    @staticmethod
    def _decode_padded_address(value: str) -> str | None:
        if not value.startswith("0x") or len(value) != 66:
            return None
        if value[2:26] != "0" * 24:
            return None
        return "0x" + value[26:]


class ParsedFoundryEnvironment(FoundryEnvironment):
    """Foundry environment with parsing for blockchain command outputs."""

    def __init__(self, *args, parser: BlockchainCommandParser | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._parser = parser or BlockchainCommandParser()

    def execute(self, action: dict | str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        from minisweagent.utils.actions import get_action_command

        command = get_action_command(action)
        result = super().execute(action, cwd=cwd, timeout=timeout)
        parsed = self._parser.parse(command, result)
        if not parsed:
            return result

        result = dict(result)
        result["parsed"] = parsed
        result.setdefault("raw_output", result.get("output", ""))
        result["output"] = parsed.get("summary", result["output"])
        return result

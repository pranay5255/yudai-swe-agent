# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mini-swe-agent is a minimal (~100 lines) AI software engineering agent that solves GitHub issues. Built by the Princeton & Stanford team behind SWE-bench and SWE-agent, it scores >74% on SWE-bench verified.

Key design choices:
- **No tools except bash** - doesn't use LM tool-calling interface, works with any model
- **Linear history** - every step appends to messages (great for fine-tuning/debugging)
- **Stateless execution** - uses `subprocess.run`, not persistent shell sessions
- **Polymorphic** - pick one agent + one environment + one model per run script

## Commands

```bash
# Install in development mode
pip install -e '.[full]'

# Run interactive CLI
mini -t "Your task"          # Simple REPL
mini -v -t "Your task"       # Visual TUI

# Run tests
pytest -v --cov --cov-branch -n auto    # All tests with coverage
pytest tests/agents/test_default.py -v   # Single test file
pytest -k "not slow"                      # Skip slow tests

# Linting
ruff check src/ tests/
ruff format src/ tests/
pre-commit run --all-files
```

## Architecture

```
src/minisweagent/
├── __init__.py        # Protocols: Model, Environment, Agent (lines 41-71)
├── agents/            # Agent control flow
│   └── default.py     # Core ~100-line agent loop
├── environments/      # Execution backends (local, docker, singularity)
├── models/            # LM interfaces (litellm, anthropic, openrouter)
├── config/            # YAML templates (system_template, instance_template, etc.)
└── run/               # Entry point scripts (mini.py, hello_world.py)
```

### Agent Loop (default.py)

1. Initialize with system message + task template
2. Loop: `query()` → model parses actions/tool calls → `execute_action()` → `has_finished()`
3. `FormatError` / `UserInterruption` → add message and continue
4. `Submitted` / `LimitsExceeded` → exit with status

Agent signals completion by outputting `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`.

### Protocols

Models must implement: `query(messages, tools) → dict`, `format_message()`, `format_observation_messages()`, `get_template_vars()`, `serialize()`.
Environments must implement: `execute(action) → dict`, `get_template_vars()`, `get_tools()`, `serialize()`.

## Code Style

1. Python 3.10+, type annotations with `list` not `List`
2. `pathlib` over `os.path`, `Path.read_text()` over `with open()`
3. Minimal code - inline expressions instead of intermediate variables:
   ```python
   # Good
   Class(func())
   # Bad
   a = func()
   Class(a)
   ```
4. Don't catch exceptions unless explicitly needed
5. Jinja2 templates with `StrictUndefined`
6. Pydantic `BaseModel` for configs, `typer` for CLIs

## Test Style

1. pytest only, no unittest
2. **Do not mock/patch** unless explicitly asked
3. No trivial tests - each test should check multiple failure points
4. Inline assertions: `assert func() == b` not `result = func(); assert result == b`
5. `pytest.mark.parametrize`: first arg is tuple, second is list

## Configuration

- Global config: `~/.config/mini-swe-agent/.env` (API keys)
- Agent config: YAML files in `src/minisweagent/config/` define templates
- Template variables available from agent config, environment, and model

## Key Files

| Purpose | Location |
|---------|----------|
| Agent loop | `src/minisweagent/agents/default.py` |
| Protocols | `src/minisweagent/__init__.py:41-71` |
| Default config | `src/minisweagent/config/default.yaml` |
| Main CLI | `src/minisweagent/run/mini.py` |
| Tests | `tests/` |

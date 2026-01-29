# Workspace & Environment Architecture Study Guide

This document explains how workspace templates, environments, and configurations work together in the exploit generation system, and how to extend them for new use cases.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component Interaction Diagram](#2-component-interaction-diagram)
3. [Template System Deep Dive](#3-template-system-deep-dive)
4. [Environment Inheritance Hierarchy](#4-environment-inheritance-hierarchy)
5. [Creating New Workspace Modes](#5-creating-new-workspace-modes)
6. [Creating Custom Environments](#6-creating-custom-environments)
7. [User-Provided Contract Flow (Future Feature)](#7-user-provided-contract-flow-future-feature)
8. [State Diagrams](#8-state-diagrams)

---

## 1. Architecture Overview

The system follows a **polymorphic design** where each run combines:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RUNTIME COMPOSITION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│   │   AGENT     │ +  │ ENVIRONMENT │ +  │    MODEL    │  = Episode         │
│   │             │    │             │    │             │                    │
│   │ DefaultAgent│    │ FoundryEnv  │    │ OpenRouter  │                    │
│   │ Interactive │    │ ExploitEnv  │    │ Anthropic   │                    │
│   │ Textual     │    │ LocalEnv    │    │ Litellm     │                    │
│   └─────────────┘    └─────────────┘    └─────────────┘                    │
│         │                  │                  │                            │
│         │                  │                  │                            │
│         ▼                  ▼                  ▼                            │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                    YAML CONFIGURATION                            │      │
│   │  agent:              environment:           model:               │      │
│   │    system_template     environment_class     model_class         │      │
│   │    instance_template   image                 model_kwargs        │      │
│   │    action_regex        project_path                              │      │
│   │    step_limit          timeout                                   │      │
│   │    cost_limit          forward_env                               │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          FULL DATA FLOW: TEMPLATE → EXECUTION                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                    TEMPLATE LAYER                           RUNTIME LAYER
              ┌──────────────────────────┐          ┌──────────────────────────────────┐
              │   exploit_generation/    │          │      benchmark_episode.py        │
              │       templates/         │          │                                  │
              │                          │          │  ┌────────────────────────────┐  │
              │  ┌──────────────────┐    │          │  │   _setup_workspace()       │  │
              │  │ Strategy.sol.tmpl│────┼──────────┼─▶│   Template substitution:   │  │
              │  │                  │    │          │  │   {{case_name}}            │  │
              │  │ {{case_name}}    │    │          │  │   {{target_address}}       │  │
              │  │ {{target_address}│    │          │  │   {{chain_id}}             │  │
              │  │ {{chain_id}}     │    │          │  │   {{block_number}}         │  │
              │  │ {{block_number}} │    │          │  │   {{player_address}}       │  │
              │  └──────────────────┘    │          │  └────────────┬───────────────┘  │
              │                          │          │               │                  │
              │  ┌──────────────────┐    │          │               ▼                  │
              │  │Harness.s.sol.tmpl│────┼──────────┼─▶  ┌─────────────────────────┐   │
              │  │                  │    │          │    │   WORKSPACE (temp dir)  │   │
              │  │ {{player_address}│    │          │    │   /tmp/benchmark_xxx/   │   │
              │  │ {{target_address}│    │          │    │   ├── foundry.toml      │   │
              │  └──────────────────┘    │          │    │   ├── src/              │   │
              │                          │          │    │   │   ├── Target.sol    │   │
              │  ┌──────────────────┐    │          │    │   │   ├── Strategy.sol  │◀──┼── Agent edits
              │  │  DexUtils.sol    │────┼──────────┼─▶  │   │   └── DexUtils.sol  │   │
              │  │ (static, no vars)│    │          │    │   ├── script/           │   │
              │  └──────────────────┘    │          │    │   │   └── Harness.s.sol │   │
              │                          │          │    │   └── lib/forge-std/    │   │
              └──────────────────────────┘          │    └─────────────┬───────────┘   │
                                                    │                  │               │
                                                    │                  ▼               │
              ┌──────────────────────────┐          │    ┌─────────────────────────┐   │
              │    YAML CONFIG           │          │    │   DOCKER CONTAINER      │   │
              │  benchmark_exploit.yaml  │          │    │                         │   │
              │                          │          │    │   Volume Mount:         │   │
              │  agent:                  │──────────┼───▶│   host:/tmp/xxx →       │   │
              │    system_template: |    │          │    │   container:/workspace  │   │
              │      Target: {{target_*}}│          │    │                         │   │
              │      Chain: {{chain_id}} │          │    │   Tools available:      │   │
              │    step_limit: 15        │          │    │   - forge build/test    │   │
              │    cost_limit: 10.0      │          │    │   - cast call/storage   │   │
              │                          │          │    │   - anvil (fork)        │   │
              │  environment:            │          │    │   - slither (optional)  │   │
              │    environment_class:    │──────────┼───▶│                         │   │
              │      exploit_foundry     │          │    └─────────────┬───────────┘   │
              │    image: yudai-base     │          │                  │               │
              │                          │          │                  ▼               │
              │  model:                  │          │    ┌─────────────────────────┐   │
              │    model_class: openrouter────────────┼─▶│   AGENT LOOP            │   │
              │    temperature: 0.0      │          │    │                         │   │
              └──────────────────────────┘          │    │   1. query() → LLM      │   │
                                                    │    │   2. parse_action()     │   │
                                                    │    │   3. execute_action()   │   │
                                                    │    │      └─▶ docker exec    │   │
                                                    │    │   4. observe() → output │   │
                                                    │    │   5. loop or terminate  │   │
                                                    │    └─────────────────────────┘   │
                                                    └──────────────────────────────────┘
```

---

## 3. Template System Deep Dive

### 3.1 Template Variable Sources

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TEMPLATE VARIABLE RESOLUTION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Variables come from THREE sources (merged in order):                       │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  1. AGENT CONFIG (from YAML)                                          │  │
│  │     - system_template, instance_template                              │  │
│  │     - Variables defined in agent.run() kwargs                         │  │
│  │     Example: target_addresses, chain_id, block_number, source_code    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  2. ENVIRONMENT.get_template_vars()                                   │  │
│  │     - cwd, timeout, image                                             │  │
│  │     - foundry_available, project_mounted                              │  │
│  │     - anvil_port, anvil_fork_url                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  3. MODEL.get_template_vars()                                         │  │
│  │     - model_name, provider                                            │  │
│  │     - max_tokens, temperature                                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  JINJA2 RENDERING (StrictUndefined)                                   │  │
│  │                                                                       │  │
│  │  system_template.render(**all_vars)                                   │  │
│  │  instance_template.render(**all_vars)                                 │  │
│  │  action_observation_template.render(**all_vars + output)              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Workspace Template File Flow

```
exploit_generation/templates/
├── Strategy.sol.tmpl          ← Jinja-style {{var}} placeholders
│   │
│   │  Contents:
│   │  ┌─────────────────────────────────────────────────────────────┐
│   │  │  contract Strategy {                                        │
│   │  │      address constant TARGET = {{target_address}};          │
│   │  │      // Target: {{target_address}} on chain {{chain_id}}    │
│   │  │      function run() public { /* exploit here */ }           │
│   │  │  }                                                          │
│   │  └─────────────────────────────────────────────────────────────┘
│   │
│   └─────▶ _setup_workspace() does string.replace() ─────▶ src/Strategy.sol
│
├── Harness.s.sol.tmpl
│   │
│   │  Contents:
│   │  ┌─────────────────────────────────────────────────────────────┐
│   │  │  contract ExploitHarness is Script {                        │
│   │  │      address constant PLAYER = {{player_address}};          │
│   │  │      function run() external {                              │
│   │  │          // Deploy Strategy, measure profit                 │
│   │  │      }                                                      │
│   │  │  }                                                          │
│   │  └─────────────────────────────────────────────────────────────┘
│   │
│   └─────▶ _setup_workspace() does string.replace() ─────▶ script/Harness.s.sol
│
└── DexUtils.sol               ← Static file (no templating)
    │
    └─────▶ Direct copy ─────▶ src/DexUtils.sol
```

### 3.3 Template Substitution Code

```python
# From benchmark_episode.py:_setup_workspace()

# Read template
strategy_tmpl = templates_dir / "Strategy.sol.tmpl"
strategy_content = strategy_tmpl.read_text()

# Simple string replacement (NOT Jinja2 for .sol files)
strategy_content = strategy_content.replace("{{case_name}}", case.case_name)
strategy_content = strategy_content.replace("{{target_address}}", case.target_contract_address)
strategy_content = strategy_content.replace("{{chain_id}}", str(chain_id))
strategy_content = strategy_content.replace("{{block_number}}", str(case.fork_block_number))

# Write to workspace
(workspace / "src" / "Strategy.sol").write_text(strategy_content)
```

---

## 4. Environment Inheritance Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ENVIRONMENT CLASS HIERARCHY                              │
└─────────────────────────────────────────────────────────────────────────────┘

                              Protocol
                          ┌─────────────┐
                          │ Environment │
                          │  (Protocol) │
                          ├─────────────┤
                          │ execute()   │
                          │ cleanup()   │
                          │ get_template│
                          │   _vars()   │
                          └──────┬──────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
     ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
     │LocalEnvironment │ │DockerEnvironment│ │SingularityEnv   │
     │                 │ │                 │ │                 │
     │ subprocess.run()│ │ docker exec     │ │ singularity exec│
     │ No isolation    │ │ Container       │ │ HPC clusters    │
     └─────────────────┘ └────────┬────────┘ └─────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
           ┌─────────────────┐        ┌─────────────────────────┐
           │FoundryEnvironment       │BubblewrapEnvironment    │
           │                 │        │ (sandboxed local)       │
           ├─────────────────┤        └─────────────────────────┘
           │ + project_path  │
           │ + volume mount  │
           │ + start_anvil() │
           │ + get_anvil_rpc │
           │   _url()        │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────────────┐
           │ExploitFoundryEnvironment│
           ├─────────────────────────┤
           │ + ExploitCommandParser  │
           │ + execution_traces[]    │
           │ + fund_account()        │
           │ + deploy_contract()     │
           │ + get_balance_ether()   │
           │                         │
           │ Extends execute() to    │
           │ parse forge script      │
           │ output into structured  │
           │ trace summaries         │
           └─────────────────────────┘
```

### 4.1 Key Methods by Layer

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        METHOD INHERITANCE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DockerEnvironment                                                          │
│  ├── execute(command, cwd, timeout)                                         │
│  │   └── docker exec -w {cwd} {container_id} bash -lc "{command}"          │
│  ├── cleanup()                                                              │
│  │   └── docker stop/rm container                                          │
│  └── get_template_vars()                                                    │
│      └── {cwd, timeout, image, ...}                                        │
│                                                                             │
│  FoundryEnvironment (extends DockerEnvironment)                             │
│  ├── __init__() - adds volume mount to run_args                            │
│  ├── start_anvil(fork_url, block_number)                                   │
│  │   └── nohup anvil --fork-url ... &                                      │
│  ├── get_anvil_rpc_url()                                                   │
│  │   └── "http://127.0.0.1:{port}"                                         │
│  └── get_template_vars() - adds foundry_available, project_mounted         │
│                                                                             │
│  ExploitFoundryEnvironment (extends FoundryEnvironment)                     │
│  ├── execute() - OVERRIDES to add parsing                                  │
│  │   ├── result = super().execute(command)                                 │
│  │   ├── parsed = self._parser.parse(command, result)                      │
│  │   ├── result["parsed"] = parsed                                         │
│  │   ├── result["raw_output"] = result["output"]                           │
│  │   └── result["output"] = parsed["summary"]  # condensed for LLM        │
│  ├── fund_account(address, balance_wei)                                    │
│  │   └── cast rpc anvil_setBalance ...                                     │
│  ├── deploy_contract(target, private_key)                                  │
│  │   └── forge create ... → parse deployed address                         │
│  └── get_balance_ether(address)                                            │
│      └── cast balance ... --ether                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Creating New Workspace Modes

### 5.1 Pattern for New Workspace Setup

```python
# In minisweagent/workspace/setup.py or exploit_generation/workspace_setup.py

from pathlib import Path
from dataclasses import dataclass

@dataclass
class WorkspaceConfig:
    """Configuration for workspace setup."""
    mode: str                    # "exploit", "audit", "development"
    target_source: str           # Contract source code
    chain_id: int = 1
    block_number: int | None = None
    player_address: str = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    include_libs: list[str] = None  # ["openzeppelin", "uniswap-v4"]


def setup_workspace(workspace: Path, config: WorkspaceConfig) -> None:
    """Set up workspace with appropriate structure and templates."""

    # 1. Create directory structure
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "script").mkdir(parents=True, exist_ok=True)
    (workspace / "test").mkdir(parents=True, exist_ok=True)
    (workspace / "lib").mkdir(parents=True, exist_ok=True)

    # 2. Load and render templates based on mode
    templates_dir = Path(__file__).parent / "templates" / config.mode

    for tmpl_file in templates_dir.glob("*.tmpl"):
        content = tmpl_file.read_text()
        content = _render_template(content, config)

        # Determine output path from template name
        output_name = tmpl_file.stem  # removes .tmpl
        if output_name.endswith(".s"):
            output_path = workspace / "script" / (output_name + ".sol")
        elif output_name.endswith(".t"):
            output_path = workspace / "test" / (output_name + ".sol")
        else:
            output_path = workspace / "src" / (output_name + ".sol")

        output_path.write_text(content)

    # 3. Copy static files
    for static_file in templates_dir.glob("*.sol"):
        shutil.copy(static_file, workspace / "src" / static_file.name)

    # 4. Generate foundry.toml
    foundry_config = _generate_foundry_toml(config)
    (workspace / "foundry.toml").write_text(foundry_config)

    # 5. Install libraries
    _install_libraries(workspace, config.include_libs or [])


def _render_template(content: str, config: WorkspaceConfig) -> str:
    """Replace {{placeholders}} with config values."""
    replacements = {
        "{{chain_id}}": str(config.chain_id),
        "{{block_number}}": str(config.block_number or "latest"),
        "{{player_address}}": config.player_address,
        # Add more as needed
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    return content
```

### 5.2 Adding a New Template Set (Example: Security Audit Mode)

```
templates/
├── exploit/                    # Existing
│   ├── Strategy.sol.tmpl
│   ├── Harness.s.sol.tmpl
│   └── DexUtils.sol
│
└── audit/                      # NEW: Security audit mode
    ├── AuditTarget.sol.tmpl    # Target contract wrapper
    ├── Findings.s.sol.tmpl     # Script to execute findings
    ├── SlitherConfig.json      # Slither detector config
    └── AuditReport.md.tmpl     # Report template

# AuditTarget.sol.tmpl
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title Audit Target: {{contract_name}}
 * @notice Chain: {{chain_id}}, Block: {{block_number}}
 * @dev Audit started: {{timestamp}}
 */
interface IAuditTarget {
    // Extract interface from target
}

// Findings.s.sol.tmpl
contract AuditFindings is Script {
    // Finding #1: {{finding_1_title}}
    function testFinding1() public {
        // POC code here
    }
}
```

---

## 6. Creating Custom Environments

### 6.1 Environment Creation Pattern

```python
# minisweagent/environments/my_custom_env.py

from pydantic import BaseModel, Field
from minisweagent.environments.foundry import FoundryEnvironment, FoundryEnvironmentConfig


class MyCustomEnvConfig(FoundryEnvironmentConfig):
    """Extended config with custom options."""

    # Add your custom config fields
    custom_rpc_url: str = ""
    custom_timeout_multiplier: float = 1.0
    enable_feature_x: bool = False


class MyCustomEnvironment(FoundryEnvironment):
    """Custom environment with specialized features."""

    def __init__(self, *, config_class: type = MyCustomEnvConfig, **kwargs):
        super().__init__(config_class=config_class, **kwargs)
        self._custom_config = config_class(**kwargs)

        # Initialize custom state
        self.custom_state = []

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict:
        """Override execute to add custom behavior."""

        # Pre-execution hook
        if self._should_intercept(command):
            return self._handle_custom_command(command)

        # Call parent
        result = super().execute(command, cwd=cwd, timeout=timeout)

        # Post-execution hook
        result = self._post_process(command, result)

        return result

    def _should_intercept(self, command: str) -> bool:
        """Check if command should be handled specially."""
        return command.startswith("custom:")

    def _handle_custom_command(self, command: str) -> dict:
        """Handle custom command prefix."""
        # Parse and execute custom logic
        return {"output": "Custom result", "returncode": 0}

    def _post_process(self, command: str, result: dict) -> dict:
        """Add custom post-processing."""
        # Store traces, modify output, etc.
        return result

    def get_template_vars(self) -> dict:
        """Add custom template variables."""
        base_vars = super().get_template_vars()
        return base_vars | {
            "custom_rpc_url": self._custom_config.custom_rpc_url,
            "feature_x_enabled": self._custom_config.enable_feature_x,
        }


# Register in minisweagent/environments/__init__.py
_ENVIRONMENT_MAPPING = {
    # ... existing ...
    "my_custom": "minisweagent.environments.my_custom_env.MyCustomEnvironment",
}
```

### 6.2 Environment Registration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENVIRONMENT REGISTRATION & LOADING                        │
└─────────────────────────────────────────────────────────────────────────────┘

    YAML Config                      environments/__init__.py
    ┌─────────────────┐             ┌─────────────────────────────────────┐
    │environment:     │             │ _ENVIRONMENT_MAPPING = {            │
    │  environment_   │             │   "docker": "...DockerEnvironment", │
    │    class:       │─────────────│   "foundry": "...FoundryEnv",       │
    │    my_custom ◀──┼─────────────│   "exploit_foundry": "...Exploit",  │
    │  image: ...     │             │   "my_custom": "...MyCustomEnv",  ◀─┼── Add here
    │  custom_rpc: ...│             │ }                                   │
    └─────────────────┘             │                                     │
           │                        │ def get_environment(config: dict):  │
           │                        │   cls = config.pop("environment_    │
           │                        │            class")                  │
           │                        │   env_class = get_environment_class │
           │                        │            (cls)                    │
           │                        │   return env_class(**config)        │
           │                        └─────────────────────────────────────┘
           │                                        │
           │                                        ▼
           │                        ┌─────────────────────────────────────┐
           │                        │ importlib.import_module(module)     │
           │                        │ getattr(module, class_name)         │
           └───────────────────────▶│ MyCustomEnvironment(**config)       │
                                    └─────────────────────────────────────┘
```

---

## 7. User-Provided Contract Flow (Future Feature)

### 7.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              USER-PROVIDED CONTRACT EXPLOIT FLOW                             │
│              (Future Feature: mini-blockchain exploit)                       │
└─────────────────────────────────────────────────────────────────────────────┘

                                USER INPUT
                    ┌───────────────────────────────────┐
                    │  mini-blockchain exploit          │
                    │    --contract 0x1234...           │ ← Option A: Address
                    │    --chain mainnet                │
                    │    --block latest                 │ ← Default: current block
                    │                                   │
                    │  OR                               │
                    │                                   │
                    │  mini-blockchain exploit          │
                    │    --file ./MyContract.sol        │ ← Option B: Local file
                    │    --deploy-and-test              │
                    └───────────────────┬───────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: INPUT VALIDATION                               │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                    INPUT ROUTER                                             │  │
│  │  ─────────────────────────────────────────────────────────────────────────  │  │
│  │                                                                             │  │
│  │  if --contract (address):                                                   │  │
│  │      1. Validate address format (0x + 40 hex chars)                         │  │
│  │      2. Resolve ENS if needed: cast resolve-name <ens>                      │  │
│  │      3. Check contract exists: cast code <addr> --rpc-url $RPC             │  │
│  │      4. Route to → ON-CHAIN PATH                                            │  │
│  │                                                                             │  │
│  │  if --file (path):                                                          │  │
│  │      1. Validate file exists and is .sol                                    │  │
│  │      2. Parse pragma solidity version                                       │  │
│  │      3. Route to → LOCAL PATH                                               │  │
│  │                                                                             │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│         ON-CHAIN PATH                  │   │           LOCAL PATH                   │
│    (Address + Chain + Block)           │   │      (Local .sol File)                 │
├───────────────────────────────────────┤   ├───────────────────────────────────────┤
│                                       │   │                                       │
│  PHASE 2A: SOURCE FETCHING            │   │  PHASE 2B: LOCAL SETUP                │
│  ───────────────────────────────      │   │  ───────────────────────────────      │
│                                       │   │                                       │
│  1. Get current block (if latest):    │   │  1. Create temp workspace             │
│     cast block-number --rpc-url $RPC  │   │                                       │
│                                       │   │  2. Copy contract to src/Target.sol   │
│  2. Fetch source from Etherscan:      │   │                                       │
│     EtherscanFetcher.get_source_code()│   │  3. Generate mock dependencies        │
│     - Try mainnet API first           │   │     if imports detected               │
│     - Cache result locally            │   │                                       │
│                                       │   │  4. Run forge build to validate       │
│  3. If verified source available:     │   │                                       │
│     - Extract ABI                     │   │  5. If --deploy-and-test:             │
│     - Parse contract name             │   │     - Start anvil (no fork)           │
│     - Detect solidity version         │   │     - Deploy contract                 │
│                                       │   │     - Fund player                     │
│  4. If NOT verified:                  │   │                                       │
│     - Fetch bytecode                  │   └───────────────────────────────────────┘
│     - Attempt decompilation (optional)│
│     - Warn user: "unverified contract"│
│                                       │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 3: WORKSPACE SETUP                                │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │  setup_user_exploit_workspace(                                              │  │
│  │      workspace: Path,                                                       │  │
│  │      source_code: str,                                                      │  │
│  │      target_address: str,                                                   │  │
│  │      chain_id: int,                                                         │  │
│  │      block_number: int,                                                     │  │
│  │      player_address: str,                                                   │  │
│  │  )                                                                          │  │
│  │                                                                             │  │
│  │  Creates:                                                                   │  │
│  │  /tmp/user_exploit_{timestamp}/                                             │  │
│  │  ├── foundry.toml                                                           │  │
│  │  ├── src/                                                                   │  │
│  │  │   ├── Target.sol        ← Source code (fetched or provided)              │  │
│  │  │   ├── Strategy.sol      ← From template (agent edits this)               │  │
│  │  │   └── DexUtils.sol      ← Helper library                                 │  │
│  │  ├── script/                                                                │  │
│  │  │   └── Harness.s.sol     ← Test harness                                   │  │
│  │  └── lib/forge-std/                                                         │  │
│  │                                                                             │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 4: ENVIRONMENT SETUP                              │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │  ExploitFoundryEnvironment                                                  │  │
│  │  ─────────────────────────                                                  │  │
│  │                                                                             │  │
│  │  1. Start Docker container with volume mount                                │  │
│  │                                                                             │  │
│  │  2. Start Anvil fork:                                                       │  │
│  │     ┌──────────────────────────────────────────────────────────────────┐    │  │
│  │     │ if block_number == "latest":                                     │    │  │
│  │     │     anvil --fork-url $RPC_URL                                   │    │  │
│  │     │ else:                                                            │    │  │
│  │     │     anvil --fork-url $RPC_URL --fork-block-number {block}       │    │  │
│  │     │                                                                  │    │  │
│  │     │ NOTE: Historical blocks require ARCHIVE RPC!                     │    │  │
│  │     │ Latest block works with any RPC.                                 │    │  │
│  │     └──────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                             │  │
│  │  3. Fund player account:                                                    │  │
│  │     cast rpc anvil_setBalance {player} {balance}                           │  │
│  │                                                                             │  │
│  │  4. Build workspace:                                                        │  │
│  │     forge build                                                             │  │
│  │                                                                             │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 5: AGENT EXECUTION                                │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │  AGENT LOOP (same as benchmark)                                             │  │
│  │  ─────────────────────────────                                              │  │
│  │                                                                             │  │
│  │  Task prompt includes:                                                      │  │
│  │    - Target address: {target_address}                                       │  │
│  │    - Chain: {chain_name} (ID: {chain_id})                                   │  │
│  │    - Block: {block_number} (current or historical)                          │  │
│  │    - Source code: {source_code}                                             │  │
│  │                                                                             │  │
│  │  Agent workflow:                                                            │  │
│  │    1. Analyze source → identify vulnerabilities                             │  │
│  │    2. Probe state → cast call/storage                                       │  │
│  │    3. Write exploit → src/Strategy.sol                                      │  │
│  │    4. Test → forge script Harness.s.sol --broadcast -vvvv                   │  │
│  │    5. Iterate → fix errors, retry                                           │  │
│  │    6. Submit → echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT                   │  │
│  │                                                                             │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 6: RESULT & CLEANUP                               │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  OUTPUT:                                                                          │
│  ├── exploit_results/{episode_id}.result.json                                     │
│  │   {                                                                            │
│  │     "target_address": "0x...",                                                 │
│  │     "chain": "mainnet",                                                        │
│  │     "block_number": 12345678,                                                  │
│  │     "success": true/false,                                                     │
│  │     "profit_native_token": 0.0,                                                │
│  │     "final_exploit_code": "contract Strategy { ... }",                         │
│  │     "execution_traces": [...],                                                 │
│  │     "total_cost_usd": 0.45                                                     │
│  │   }                                                                            │
│  │                                                                                │
│  └── exploit_results/{episode_id}.traj.json                                       │
│      Full agent conversation history                                              │
│                                                                                   │
│  CLEANUP:                                                                         │
│  ├── Stop Docker container                                                        │
│  └── Remove temp workspace (unless --keep)                                        │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Implementation Plan for User-Provided Contract

```python
# New file: src/minisweagent/run/exploit.py

import typer
from pathlib import Path
from rich.console import Console

app = typer.Typer(name="exploit", help="Exploit generation for any contract")
console = Console()

@app.command()
def exploit(
    # Input source (mutually exclusive)
    contract: str = typer.Option(None, "--contract", "-c", help="Contract address (0x...)"),
    file: Path = typer.Option(None, "--file", "-f", help="Local Solidity file path"),

    # Chain & block settings
    chain: str = typer.Option("mainnet", "--chain", help="Chain: mainnet, bsc, base"),
    block: str = typer.Option("latest", "--block", "-b", help="Block number or 'latest'"),

    # Execution settings
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    cost_limit: float = typer.Option(10.0, "--cost-limit", "-l", help="Max cost USD"),

    # Output
    output: Path = typer.Option(Path("exploit_results"), "--output", "-o"),
    keep_workspace: bool = typer.Option(False, "--keep", help="Keep temp workspace"),
):
    """
    Generate exploits for user-provided contracts.

    Examples:
        # Exploit deployed contract at current block
        mini-blockchain exploit -c 0x1234... --chain mainnet

        # Exploit at historical block (requires archive RPC)
        mini-blockchain exploit -c 0x1234... --block 15000000

        # Exploit local contract file
        mini-blockchain exploit -f ./MyContract.sol --deploy-and-test
    """
    # Implementation here...
```

### 7.3 Key Differences: Benchmark vs User-Provided

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BENCHMARK vs USER-PROVIDED COMPARISON                     │
├───────────────────────────┬─────────────────────────┬───────────────────────┤
│         Aspect            │      Benchmark Mode     │   User-Provided Mode  │
├───────────────────────────┼─────────────────────────┼───────────────────────┤
│ Source of cases           │ benchmark.csv           │ CLI arguments         │
│ Block number              │ Fixed (from CSV)        │ Latest or user choice │
│ Archive RPC required      │ Yes (historical)        │ Only if historical    │
│ Source code               │ Pre-cached from CSV     │ Fetched on demand     │
│ Batch execution           │ Yes (--limit N)         │ Single contract       │
│ Run summary JSON          │ Yes (benchmark_*.json)  │ No (single result)    │
│ Case filtering            │ --chain, --case, --index│ N/A                   │
│ Interactive prompts       │ No (batch)              │ Yes (if needed)       │
└───────────────────────────┴─────────────────────────┴───────────────────────┘
```

---

## 8. State Diagrams

### 8.1 Complete Exploit Episode State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXPLOIT EPISODE STATE MACHINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   START     │
                              └──────┬──────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  VALIDATE_INPUT      │
                          │  - Check API keys    │
                          │  - Validate address  │
                          │  - Check RPC access  │
                          └──────────┬───────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │ Error          │ OK             │
                    ▼                ▼                │
           ┌────────────────┐  ┌──────────────────┐   │
           │ FAILED_EARLY   │  │ FETCH_SOURCE     │   │
           │ - Missing key  │  │ - Etherscan API  │   │
           │ - Bad address  │  │ - Cache lookup   │   │
           └────────────────┘  └──────────┬───────┘   │
                                          │           │
                           ┌──────────────┼───────────┤
                           │ Not verified │ OK        │
                           ▼              ▼           │
                  ┌────────────────┐ ┌───────────────┐│
                  │ WARN_UNVERIFIED│ │ SETUP_        ││
                  │ Continue?      │ │ WORKSPACE     ││
                  └────────┬───────┘ │ - Create dirs ││
                           │         │ - Copy source ││
                           └────────▶│ - Templates   ││
                                     │ - foundry.toml││
                                     └───────┬───────┘│
                                             │        │
                                             ▼        │
                                     ┌───────────────┐│
                                     │ START_DOCKER  ││
                                     │ - Container   ││
                                     │ - Volume mount││
                                     └───────┬───────┘│
                                             │        │
                              ┌──────────────┼────────┤
                              │ Error        │ OK     │
                              ▼              ▼        │
                     ┌────────────────┐ ┌───────────────┐
                     │ FAILED_DOCKER  │ │ START_ANVIL  │
                     │ - Image pull?  │ │ - Fork RPC   │
                     │ - Permissions? │ │ - Block num  │
                     └────────────────┘ └───────┬───────┘
                                                │
                                 ┌──────────────┼──────────────┐
                                 │ Error        │ OK           │
                                 ▼              ▼              │
                        ┌────────────────┐ ┌───────────────────┐
                        │ FAILED_ANVIL   │ │ FUND_PLAYER       │
                        │ - Archive RPC? │ │ - anvil_setBalance│
                        │ - Rate limit?  │ └─────────┬─────────┘
                        └────────────────┘           │
                                                     ▼
                                             ┌───────────────┐
                                             │ BUILD_PROJECT │
                                             │ - forge build │
                                             └───────┬───────┘
                                                     │
                                      ┌──────────────┼──────────────┐
                                      │ Errors       │ OK           │
                                      ▼              ▼              │
                             ┌────────────────┐ ┌───────────────────┐
                             │ BUILD_WARNING  │ │ AGENT_RUNNING     │
                             │ Agent will fix │ │                   │
                             └────────┬───────┘ │ ┌───────────────┐ │
                                      │         │ │ query() → LLM │ │
                                      └────────▶│ └───────┬───────┘ │
                                                │         │         │
                                                │         ▼         │
                                                │ ┌───────────────┐ │
                                                │ │ parse_action()│ │
                                                │ └───────┬───────┘ │
                                                │         │         │
                                                │         ▼         │
                                                │ ┌───────────────┐ │
                                                │ │execute_action │ │
                                                │ │ docker exec   │ │
                                                │ └───────┬───────┘ │
                                                │         │         │
                                                │    ┌────┴────┐    │
                                                │    │ Check   │    │
                                                │    │terminate│    │
                                                │    └────┬────┘    │
                                                │         │         │
                                          ┌─────┴─────┐   │ No      │
                                          │ Yes       │   └────┐    │
                                          ▼                    │    │
                                 ┌─────────────────┐           │    │
                                 │ AGENT_FINISHED  │◀──────────┘    │
                                 │ - Submitted     │                │
                                 │ - LimitsExceeded│                │
                                 │ - Error         │                │
                                 └────────┬────────┘                │
                                          │                         │
                                          ▼                         │
                                 ┌─────────────────┐                │
                                 │ MEASURE_PROFIT  │                │
                                 │ balance_after - │                │
                                 │ balance_before  │                │
                                 └────────┬────────┘                │
                                          │                         │
                              ┌───────────┼───────────┐             │
                              │ profit>0  │ profit<=0 │             │
                              ▼           ▼           │             │
                     ┌─────────────┐ ┌─────────────┐  │             │
                     │ SUCCESS     │ │ FAILED      │  │             │
                     └──────┬──────┘ └──────┬──────┘  │             │
                            │               │         │             │
                            └───────┬───────┘         │             │
                                    ▼                 │             │
                           ┌─────────────────┐        │             │
                           │ SAVE_RESULTS    │        │             │
                           │ - result.json   │        │             │
                           │ - traj.json     │        │             │
                           └────────┬────────┘        │             │
                                    │                 │             │
                                    ▼                 │             │
                           ┌─────────────────┐        │             │
                           │ CLEANUP         │        │             │
                           │ - Stop container│        │             │
                           │ - Remove temp   │        │             │
                           └────────┬────────┘        │             │
                                    │                 │             │
                                    ▼                 │             │
                              ┌─────────────┐         │             │
                              │    END      │         │             │
                              └─────────────┘         │             │
                                                      │             │
            ◀─────────────────────────────────────────┴─────────────┘
                        (loop back for batch mode)
```

### 8.2 Agent Loop Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT LOOP DETAIL                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌───────────────────────────┐
                         │        LOOP START         │
                         │     step_count = 0        │
                         │     total_cost = 0        │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
              ┌────────────────────────────────────────────────┐
              │                 CHECK LIMITS                    │
              │  ─────────────────────────────────────────────  │
              │  if step_count >= step_limit: raise LimitsExceeded
              │  if total_cost >= cost_limit: raise LimitsExceeded
              └────────────────────────┬───────────────────────┘
                                       │
                                       ▼
              ┌────────────────────────────────────────────────┐
              │                   QUERY LLM                     │
              │  ─────────────────────────────────────────────  │
              │  messages = [system_msg, instance_msg] +        │
              │             conversation_history                │
              │                                                 │
              │  response = model.query(messages)               │
              │  step_count += 1                                │
              │  total_cost += response.cost                    │
              └────────────────────────┬───────────────────────┘
                                       │
                                       ▼
              ┌────────────────────────────────────────────────┐
              │                 PARSE ACTION                    │
              │  ─────────────────────────────────────────────  │
              │  actions = re.findall(action_regex, response)   │
              │                                                 │
              │  if len(actions) != 1:                          │
              │      append format_error_template to history    │
              │      continue (loop back)                       │
              │                                                 │
              │  action = actions[0]                            │
              └────────────────────────┬───────────────────────┘
                                       │
                                       ▼
              ┌────────────────────────────────────────────────┐
              │              CHECK TERMINATION                  │
              │  ─────────────────────────────────────────────  │
              │  if "COMPLETE_TASK_AND_SUBMIT" in action:       │
              │      raise Submitted(action)                    │
              └────────────────────────┬───────────────────────┘
                                       │
                                       ▼
              ┌────────────────────────────────────────────────┐
              │               EXECUTE ACTION                    │
              │  ─────────────────────────────────────────────  │
              │                                                 │
              │  ┌──────────────────────────────────────────┐   │
              │  │ ExploitFoundryEnvironment.execute()      │   │
              │  │                                          │   │
              │  │ 1. docker exec ... bash -lc "{action}"   │   │
              │  │ 2. parser.parse(action, result)          │   │
              │  │    ├─ forge build → build summary        │   │
              │  │    ├─ forge script → trace summary       │   │
              │  │    ├─ cast call → decoded output         │   │
              │  │    └─ other → pass through               │   │
              │  │ 3. result["output"] = parsed["summary"]  │   │
              │  │    result["raw_output"] = original       │   │
              │  └──────────────────────────────────────────┘   │
              │                                                 │
              │  if timeout:                                    │
              │      append timeout_template to history         │
              │      continue (loop back)                       │
              └────────────────────────┬───────────────────────┘
                                       │
                                       ▼
              ┌────────────────────────────────────────────────┐
              │                 OBSERVE                         │
              │  ─────────────────────────────────────────────  │
              │  observation = action_observation_template.     │
              │                  render(output=result)          │
              │                                                 │
              │  conversation_history.append({                  │
              │      "role": "assistant",                       │
              │      "content": response                        │
              │  })                                             │
              │  conversation_history.append({                  │
              │      "role": "user",                            │
              │      "content": observation                     │
              │  })                                             │
              └────────────────────────┬───────────────────────┘
                                       │
                                       │
                                       └──────────────▶ LOOP START
```

---

## Summary: Key Extension Points

| What to Extend | Where | How |
|----------------|-------|-----|
| Add new workspace mode | `workspace/setup.py` | Create `setup_xxx_workspace()` function |
| Add new templates | `templates/{mode}/` | Create `.sol.tmpl` files with `{{placeholders}}` |
| Add new environment | `environments/xxx.py` | Subclass `FoundryEnvironment` or `DockerEnvironment` |
| Register environment | `environments/__init__.py` | Add to `_ENVIRONMENT_MAPPING` |
| Add new YAML config | `config/xxx.yaml` | Define agent + environment + model sections |
| Add CLI command | `run/xxx.py` | Create typer app, register in `pyproject.toml` |
| Add template variables | Environment class | Override `get_template_vars()` |
| Add output parsing | Parser class | Extend `BlockchainCommandParser` |

---

## Next Steps for Implementation

1. **Create `exploit` command** in `run/exploit.py`
2. **Add input validation** for address/file
3. **Create `setup_user_exploit_workspace()`** function
4. **Add current block fetching** logic
5. **Test with latest block** (no archive RPC needed)
6. **Add unverified contract handling**
7. **Create TUI wizard** for interactive mode

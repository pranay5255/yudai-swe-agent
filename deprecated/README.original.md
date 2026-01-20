<div align="center">

# ⚡ YUDAI

### AI-Powered Smart Contract Security Agent

<img src="https://img.shields.io/badge/Solidity-363636?style=for-the-badge&logo=solidity&logoColor=white" alt="Solidity"/>
<img src="https://img.shields.io/badge/Foundry-000000?style=for-the-badge&logo=foundry&logoColor=white" alt="Foundry"/>
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>

**Find vulnerabilities. Understand exploits. Ship secure code.**

[![Tools](https://img.shields.io/badge/Security_Tools-8%2F8_Working-success?style=flat-square)](./FINAL_TEST_RESULTS.md)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](./LICENSE.md)

---

*Built on [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) by the Princeton & Stanford team behind SWE-bench*

</div>

## What is Yudai?

Yudai is an **AI coding agent specialized in smart contract security**. It combines the simplicity of mini-swe-agent (~100 lines) with a complete security analysis toolkit running in Docker.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  "Audit the Token.sol contract for reentrancy vulnerabilities"         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  YUDAI AGENT                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. Compiles with Forge        → forge build                      │   │
│  │ 2. Static analysis            → slither . + aderyn .             │   │
│  │ 3. Symbolic execution         → myth analyze Token.sol           │   │
│  │ 4. Fuzzing (if needed)        → echidna --contract Token         │   │
│  │ 5. Generates PoC exploit      → forge test -vvvv                 │   │
│  │ 6. Recommends fixes           → Structured report                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  📋 AUDIT REPORT                                                        │
│  ────────────────────────────────────────────────────────────────────── │
│  CRITICAL: Reentrancy in withdraw() at Token.sol:47                     │
│  IMPACT: Attacker can drain all funds                                   │
│  FIX: Apply checks-effects-interactions pattern                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              YUDAI ARCHITECTURE                                   │
└──────────────────────────────────────────────────────────────────────────────────┘

                                ┌─────────────────┐
                                │   User Input    │
                                │  "Audit X.sol"  │
                                └────────┬────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                            AGENT LOOP (default.py)                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                          │  │
│  │   ┌─────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────┐  │  │
│  │   │  QUERY  │───▶│ PARSE ACTION │───▶│ EXECUTE ACTION │───▶│ OBSERVE  │  │  │
│  │   │   LLM   │    │  (bash ````) │    │  (subprocess)  │    │  OUTPUT  │  │  │
│  │   └─────────┘    └──────────────┘    └───────────────┘    └──────────┘  │  │
│  │        ▲                                      │                  │       │  │
│  │        │                                      │                  │       │  │
│  │        └──────────────────────────────────────┴──────────────────┘       │  │
│  │                        (Loop until SUBMITTED or LIMIT_EXCEEDED)          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                         │                                       │
│                                         │ docker exec                           │
│                                         ▼                                       │
└────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                         DOCKER ENVIRONMENT (yudai-complete)                     │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                          │  │
│  │   ┌────────────────────────────────────────────────────────────────┐    │  │
│  │   │                    FOUNDRY SUITE (Native)                      │    │  │
│  │   │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐     │    │  │
│  │   │  │ FORGE   │    │  CAST   │    │  ANVIL  │    │ CHISEL  │     │    │  │
│  │   │  │ Build   │    │  Call   │    │  Fork   │    │  REPL   │     │    │  │
│  │   │  │ Test    │    │  Send   │    │  Mine   │    │         │     │    │  │
│  │   │  └─────────┘    └─────────┘    └─────────┘    └─────────┘     │    │  │
│  │   └────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                          │  │
│  │   ┌────────────────────────────────────────────────────────────────┐    │  │
│  │   │                 SECURITY ANALYSIS TOOLS                         │    │  │
│  │   │                                                                  │    │  │
│  │   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │    │  │
│  │   │  │  SLITHER    │  │   MYTHRIL   │  │   ADERYN    │  │ECHIDNA │ │    │  │
│  │   │  │             │  │             │  │             │  │        │ │    │  │
│  │   │  │  Static     │  │  Symbolic   │  │  Pattern    │  │ Fuzz   │ │    │  │
│  │   │  │  Analysis   │  │  Execution  │  │  Detection  │  │ Testing│ │    │  │
│  │   │  │  93+ rules  │  │  Deep bugs  │  │  Fast scan  │  │ Props  │ │    │  │
│  │   │  └─────────────┘  └─────────────┘  └─────────────┘  └────────┘ │    │  │
│  │   └────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                          │  │
│  │   ┌────────────────────────────────────────────────────────────────┐    │  │
│  │   │                      SOLIDITY COMPILER                          │    │  │
│  │   │  ┌─────────────────────────────┐  ┌─────────────────────────┐  │    │  │
│  │   │  │        solc 0.8.24          │  │      solc-select        │  │    │  │
│  │   │  │        (Default)            │  │   (Version Manager)     │  │    │  │
│  │   │  └─────────────────────────────┘  └─────────────────────────┘  │    │  │
│  │   └────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  Volumes: /workspace ◀──── Mounted from host project                           │
│  Python: 3.12 + uv package manager                                              │
│  venvs: /opt/venv-main (Slither) + /opt/venv-mythril (Mythril isolated)        │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Analysis Tools

Each tool has different strengths. Yudai orchestrates them together for comprehensive coverage.

### Tool Comparison Matrix

| Tool | Type | Speed | Depth | Best For | Detectors |
|------|------|-------|-------|----------|-----------|
| **Slither** | Static Analysis | ⚡⚡⚡⚡⚡ | ●●●○○ | Quick scans, CI/CD | 93+ built-in |
| **Aderyn** | Pattern Detection | ⚡⚡⚡⚡⚡ | ●●○○○ | Fast audits, Rust speed | 60+ patterns |
| **Mythril** | Symbolic Execution | ⚡○○○○ | ●●●●● | Deep bugs, edge cases | SMT-based |
| **Echidna** | Fuzz Testing | ⚡⚡○○○ | ●●●●○ | Property testing, invariants | Custom props |

### What Each Tool Finds Best

<table>
<tr>
<td width="50%">

#### 🔍 Slither (Static Analysis)
**Speed:** ~5 seconds per project
**Best at finding:**
- ✅ Reentrancy vulnerabilities
- ✅ Unchecked return values
- ✅ Dangerous delegatecalls
- ✅ Uninitialized storage
- ✅ Shadowing variables
- ✅ Incorrect ERC20 implementations

```bash
slither . --print human-summary
```

</td>
<td width="50%">

#### 🧠 Mythril (Symbolic Execution)
**Speed:** 1-10 minutes per contract
**Best at finding:**
- ✅ Integer overflow/underflow
- ✅ Transaction order dependence
- ✅ Unprotected selfdestruct
- ✅ Assertion violations
- ✅ Complex state-dependent bugs
- ✅ Edge case vulnerabilities

```bash
myth analyze src/Contract.sol --execution-timeout 120
```

</td>
</tr>
<tr>
<td width="50%">

#### ⚡ Aderyn (Pattern Detection)
**Speed:** ~2 seconds per project
**Best at finding:**
- ✅ Centralization risks
- ✅ Missing zero-address checks
- ✅ Floating pragma issues
- ✅ Missing events
- ✅ Gas optimization opportunities
- ✅ Code quality issues

```bash
aderyn .
```

</td>
<td width="50%">

#### 🎲 Echidna (Fuzz Testing)
**Speed:** Configurable (seconds to hours)
**Best at finding:**
- ✅ Invariant violations
- ✅ Property-based failures
- ✅ Unexpected state transitions
- ✅ Economic exploits
- ✅ Complex multi-step attacks
- ✅ Custom security properties

```bash
echidna . --contract Token --test-mode assertion
```

</td>
</tr>
</table>

### Vulnerability Coverage by 2024 Attack Data

| Vulnerability Class | 2024 Losses | Slither | Mythril | Aderyn | Echidna |
|---------------------|-------------|---------|---------|--------|---------|
| Access Control | $953M | ✅ | ✅ | ✅ | ⚠️ |
| Logic Errors | $64M | ⚠️ | ✅ | ⚠️ | ✅ |
| Reentrancy | $36M | ✅ | ✅ | ✅ | ✅ |
| Flash Loan Attacks | $34M | ⚠️ | ✅ | ⚠️ | ✅ |
| Oracle Manipulation | $28M | ⚠️ | ⚠️ | ⚠️ | ✅ |
| Rounding/Precision | $15M | ✅ | ✅ | ⚠️ | ✅ |

**Legend:** ✅ Strong detection | ⚠️ Partial/manual review needed

---

## Quick Start

### 1. Build the Docker Environment

```bash
# Clone the repository
git clone https://github.com/your-org/yudai-swe-agent.git
cd yudai-swe-agent

# Build the complete security environment
docker build -t yudai-complete -f docker/Dockerfile.yudai.fixed .
```

### 2. Install the Agent

```bash
# Install with full dependencies
pip install -e '.[full]'
```

### 3. Run Security Audit

```bash
# Interactive audit session
mini -c security -t "Audit the contracts in this project for vulnerabilities"

# Visual TUI mode
mini -v -c security -t "Find reentrancy bugs in src/Token.sol"
```

---

## Usage Examples

### Run a Quick Security Scan

```bash
# Mount your project and run Slither
docker run --rm -v "$(pwd):/workspace" yudai-complete \
  bash -lc ". /opt/venv-main/bin/activate && slither /workspace"
```

### Deep Analysis with Mythril

```bash
docker run --rm -v "$(pwd):/workspace" yudai-complete \
  bash -lc "myth analyze /workspace/src/Contract.sol --execution-timeout 120"
```

### Fuzz Testing with Echidna

```bash
docker run --rm -v "$(pwd):/workspace" yudai-complete \
  bash -lc "cd /workspace && echidna . --contract Token --test-mode assertion"
```

### Full Foundry Workflow

```bash
# Start interactive session
docker run --rm -it -v "$(pwd):/workspace" yudai-complete bash

# Inside container:
forge build                          # Compile
forge test -vvv                      # Run tests
. /opt/venv-main/bin/activate       # Activate for Slither
slither . --print human-summary     # Quick audit
```

### Python API

```python
from minisweagent import DefaultAgent
from minisweagent.models import LitellmModel
from minisweagent.environments import FoundryEnvironment

# Create security audit agent
agent = DefaultAgent(
    LitellmModel(model_name="claude-3-opus"),
    FoundryEnvironment(project_path="./my-foundry-project"),
    config_file="security.yaml"
)

# Run audit
status, report = agent.run("Audit the Vault.sol contract for vulnerabilities")
print(report)
```

---

## Agent Loop Flow

```
                    ┌─────────────────────────────────────────┐
                    │           SECURITY AUDIT FLOW            │
                    └─────────────────────────────────────────┘

                                    START
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │  1. COMPILE                              │
                    │     forge build                          │
                    │     └─▶ Check for compiler errors       │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │  2. QUICK STATIC ANALYSIS               │
                    │     slither . + aderyn .                 │
                    │     └─▶ ~10 seconds total               │
                    │     └─▶ 150+ detectors combined         │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │  3. DEEP ANALYSIS (if needed)           │
                    │     myth analyze src/Critical.sol        │
                    │     └─▶ 1-5 minutes per contract        │
                    │     └─▶ Finds edge cases & complex bugs │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │  4. FUZZ TESTING (optional)             │
                    │     echidna . --contract Token           │
                    │     └─▶ Tests invariants & properties   │
                    │     └─▶ Finds economic exploits         │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │  5. GENERATE PROOF-OF-CONCEPT           │
                    │     anvil fork → deploy → exploit       │
                    │     └─▶ Verifies vulnerability          │
                    │     └─▶ Demonstrates impact             │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │  6. GENERATE REPORT                      │
                    │     Severity: Critical/High/Medium/Low   │
                    │     Location: file.sol:line              │
                    │     Impact: What attacker can do         │
                    │     Remediation: How to fix              │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
                                    DONE
```

---

## Tool Versions

All tools are verified working (100% success rate):

| Component | Version | Status |
|-----------|---------|--------|
| **Foundry** | v1.5.1-nightly | ✅ Working |
| **Slither** | 0.10.2 | ✅ Working |
| **Mythril** | 0.24.8 | ✅ Working |
| **Aderyn** | 0.6.5 | ✅ Working |
| **Echidna** | 2.2.5 | ✅ Working |
| **solc** | 0.8.24 | ✅ Working |
| **Python** | 3.12 | ✅ Working |
| **uv** | 0.9.21 | ✅ Working |

---

## Configuration

### Security Audit Config (`security.yaml`)

```yaml
agent:
  system_template: |
    You are an expert smart contract security auditor...
  step_limit: 150
  cost_limit: 10.0

environment:
  environment_class: foundry
  image: "yudai/foundry-full:latest"
  timeout: 180  # Longer for Mythril
```

### Foundry Development Config (`foundry.yaml`)

```yaml
agent:
  system_template: |
    You are a Solidity developer...
  step_limit: 100
  cost_limit: 5.0

environment:
  environment_class: foundry
  image: "yudai/foundry-full:latest"
  timeout: 120
```

---

## Project Structure

```
yudai-swe-agent/
├── src/minisweagent/
│   ├── agents/
│   │   └── default.py          # ~100 line agent loop
│   ├── environments/
│   │   ├── foundry.py          # Foundry Docker environment
│   │   └── docker.py           # Base Docker environment
│   ├── config/
│   │   ├── security.yaml       # Security audit workflow
│   │   └── foundry.yaml        # Development workflow
│   └── models/
│       └── litellm_model.py    # LLM interface
├── docker/
│   ├── Dockerfile.yudai        # Original Dockerfile
│   └── Dockerfile.yudai.fixed  # ✅ Production (all tools working)
├── tests/
└── docs/
    └── ARCHITECTURE.md         # Detailed architecture
```

---

## Why Yudai?

| Feature | Yudai | Manual Auditing | Other Tools |
|---------|-------|-----------------|-------------|
| **Setup Time** | 5 minutes | N/A | Hours |
| **Tool Integration** | 8 tools unified | Manual switching | 1-2 tools |
| **Context Awareness** | Full Solidity understanding | Human expertise | Pattern matching |
| **PoC Generation** | Automatic | Manual | Limited |
| **Cost** | ~$0.50/audit | $$$$ | Varies |
| **Speed** | Minutes | Days | Minutes |

---

## Contributing

See [CONTRIBUTING.md](./docs/contributing.md) for guidelines.

```bash
# Development setup
pip install -e '.[full]'
pre-commit install

# Run tests
pytest -v --cov --cov-branch -n auto

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

---

## Documentation

- [Architecture Deep Dive](./docs/ARCHITECTURE.md)
- [Docker Setup Guide](./DOCKER_ENV_SETUP.md)
- [Test Results](./FINAL_TEST_RESULTS.md)
- [Security Config Reference](./src/minisweagent/config/security.yaml)

---

## Acknowledgments

Built on [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) by the Princeton & Stanford team behind [SWE-bench](https://swebench.com) and [SWE-agent](https://swe-agent.com).

Security tools:
- [Slither](https://github.com/crytic/slither) by Trail of Bits
- [Mythril](https://github.com/Consensys/mythril) by ConsenSys
- [Aderyn](https://github.com/Cyfrin/aderyn) by Cyfrin
- [Echidna](https://github.com/crytic/echidna) by Trail of Bits
- [Foundry](https://github.com/foundry-rs/foundry) by Paradigm

---

<div align="center">

**[Documentation](./docs/) · [Issues](https://github.com/your-org/yudai-swe-agent/issues) · [Contributing](./docs/contributing.md)**

Made with ⚡ for the smart contract security community

</div>

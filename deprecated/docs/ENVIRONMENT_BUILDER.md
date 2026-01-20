# Environment Builder System

## Overview

The Environment Builder system creates **compilation-ready Foundry projects** for vulnerability fixing tasks. Inspired by [SCONE-bench](https://scone-bench.github.io/)'s containerized evaluation framework, this system ensures contracts compile successfully **before** the agent starts execution.

### Problem Solved

Previously, the agent would encounter compilation failures due to:
- Missing dependencies (OpenZeppelin, external contracts)
- Wrong Solidity version
- Unresolved imports
- Missing stub contracts

The agent would waste time and tokens trying to debug these environmental issues instead of focusing on fixing vulnerabilities.

### Solution

Pre-build complete Foundry environments with:
1. **Contract Analysis**: Detect version, imports, dependencies
2. **Dependency Resolution**: Install required libraries (OpenZeppelin, etc.)
3. **Stub Generation**: Create minimal stubs for external contracts
4. **Compilation Verification**: Ensure `forge build` succeeds before agent starts

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Episode Runner                                                   │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 1. Contract Analysis (contract_analyzer.py)                │  │
│  │    - Parse Solidity version from pragma                    │  │
│  │    - Detect OpenZeppelin imports and version               │  │
│  │    - Extract all import statements                         │  │
│  │    - Identify external contract references                 │  │
│  │    - Recommend Foundry template                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 2. Environment Building (environment_builder.py)           │  │
│  │    - Create Foundry project structure                      │  │
│  │    - Generate foundry.toml with correct solc version       │  │
│  │    - Run `forge install` for dependencies                  │  │
│  │    - Create stub contracts for missing imports             │  │
│  │    - Copy contract to src/                                 │  │
│  │    - Run `forge build` to verify compilation               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 3. Ready Environment (passed to agent)                     │  │
│  │    /workspace/                                             │  │
│  │    ├── foundry.toml         (configured for contract)     │  │
│  │    ├── src/                                                │  │
│  │    │   ├── Contract.sol      (the vulnerable contract)    │  │
│  │    │   └── stubs/            (generated stubs if needed)  │  │
│  │    ├── lib/                                                │  │
│  │    │   └── openzeppelin-contracts/  (if needed)           │  │
│  │    ├── test/                                               │  │
│  │    └── .contract_metadata.json  (analysis results)        │  │
│  │                                                            │  │
│  │    ✅ forge build SUCCEEDS before agent starts            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 4. Agent Execution                                         │  │
│  │    - Agent focuses on fixing vulnerability                 │  │
│  │    - No time wasted on environment setup                   │  │
│  │    - Can test fix immediately with `forge build`           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Contract Analyzer (`contract_analyzer.py`)

Analyzes Solidity contracts to extract metadata:

```python
from vulnerability_injection.contract_analyzer import analyze_contract

metadata = analyze_contract(Path("contracts/SimpleBank.sol"))

# Returns ContractMetadata with:
# - solidity_version: str (e.g., "0.8.20")
# - pragma_range: str (e.g., "^0.8.0")
# - has_openzeppelin: bool
# - oz_version: str | None (e.g., "v4", "v5")
# - imports: list[str]
# - external_contracts: list[str]
# - is_standalone: bool
# - recommended_template: str
# - needs_network: bool
```

**Detection Logic:**

| Feature | Detection Method |
|---------|------------------|
| Solidity Version | Regex on `pragma solidity` statement |
| OpenZeppelin | Search for `openzeppelin` in imports |
| OZ Version | Import path structure + contract patterns |
| External Contracts | Find referenced but undeclared contracts |
| Network Need | Check for DEX/Oracle/ETH transfer patterns |

### 2. Environment Builder (`environment_builder.py`)

Builds compilation-ready Foundry projects:

```python
from vulnerability_injection.environment_builder import build_environment_for_contract

result = build_environment_for_contract(
    contract_path=Path("contracts/vulnerable.sol"),
    output_dir=Path("/tmp/project"),
    use_docker=False
)

# Returns BuildResult with:
# - success: bool
# - workspace: Path
# - metadata: ContractMetadata
# - errors: list[str]
# - template_used: str
# - compilation_output: str
```

**Build Steps:**

1. **Analyze** contract using `contract_analyzer`
2. **Create** project structure:
   ```
   workspace/
   ├── foundry.toml
   ├── src/
   ├── test/
   ├── lib/
   └── script/
   ```
3. **Install dependencies** via `forge install`:
   - OpenZeppelin v3/v4/v5 based on detected version
4. **Generate stubs** for external contracts:
   ```solidity
   contract ExternalDependency {
       function placeholder() public pure returns (bool) {
           return true;
       }
   }
   ```
5. **Copy contract** to `src/`
6. **Verify compilation** with `forge build`

### 3. Updated Episode Runner (`episode.py`)

Integrated into the RL episode workflow:

```python
# OLD (would fail on compilation issues)
def setup_foundry_project(contract_path, workspace):
    # Minimal setup, no dep resolution
    shutil.copy(contract_path, workspace / "src")
    # Agent would fail on first `forge build`

# NEW (guarantees compilation before agent starts)
def setup_foundry_project(contract_path, workspace, use_docker=False):
    builder = EnvironmentBuilder(use_docker=use_docker)
    result = builder.build_environment(contract_path, workspace)

    if not result.success:
        # Handle compilation failure
        logger.error(f"Failed to build: {result.errors}")

    return workspace, result.success, result.compilation_output
```

## Template System

### Current Templates

The system recommends templates based on analysis:

| Template | Use Case | Solc Version | Dependencies |
|----------|----------|--------------|--------------|
| `sol-0.4-standalone` | Old vulnerable contracts | 0.4.26 | None |
| `sol-0.5-standalone` | Mid-era contracts | 0.5.17 | None |
| `sol-0.8-standalone` | Modern standalone | 0.8.20 | None |
| `sol-0.8-oz-v4` | With OpenZeppelin v4 | 0.8.20 | OZ v4.9.6 |
| `sol-0.8-oz-v5` | With OpenZeppelin v5 | 0.8.24 | OZ v5.0.2 |

### Creating Templates

Templates can be pre-built and cached for faster setup:

```bash
# Create a template manually
mkdir -p /templates/sol-0.8-oz-v4
cd /templates/sol-0.8-oz-v4

forge init --no-commit
echo 'solc = "0.8.20"' >> foundry.toml
forge install OpenZeppelin/openzeppelin-contracts@v4.9.6 --no-commit

# Now it can be reused for all similar contracts
```

## Usage

### Analyzing Contracts

```bash
# Analyze a single contract
python vulnerability_injection/contract_analyzer.py contracts/SimpleBank.sol

# Output:
# Contract Analysis: SimpleBank.sol
# ==================================================
# Solidity Version: 0.8.20
# Pragma: ^0.8.0
# OpenZeppelin: False
# Imports: 0
# External Contracts: []
# Standalone: True
# Needs Network: False
# Recommended Template: sol-0.8-standalone
```

### Building Environments

```bash
# Build environment for a contract
python vulnerability_injection/environment_builder.py contracts/SimpleBank.sol

# Output:
# Building environment for: SimpleBank.sol
# ============================================================
# INFO: Analyzing contract: SimpleBank.sol
# INFO:   Version: 0.8.20
# INFO:   Template: sol-0.8-standalone
# INFO: Creating workspace at: /tmp/foundry_env_xyz
# INFO: Creating minimal project
# INFO: Copied contract to: /tmp/foundry_env_xyz/src/SimpleBank.sol
# INFO: Verifying compilation...
# INFO: ✓ Environment ready - contract compiles!
```

### Testing All Contracts

```bash
# Test analyzer and builder on all contracts
python scripts/test_environment_builder.py

# Test specific category
python scripts/test_environment_builder.py --category vulnerabilities

# Only analyze, don't compile
python scripts/test_environment_builder.py --no-compile

# Test single contract
python scripts/test_environment_builder.py -c contracts/SimpleBank.sol
```

### Running Episodes

The environment builder is automatically used in episodes:

```bash
# Run episode with new system
python scripts/run_minimal_episode.py -c contracts/SimpleBank.sol

# The environment is built before agent starts:
# 1. Contract analyzed
# 2. Dependencies installed
# 3. Compilation verified
# 4. Agent receives working environment
```

## Comparison with SCONE-bench

### Similarities
- **Docker-based execution** for isolation
- **Pre-configured environment** before agent starts
- **Persistent bash session** for iterative work
- **Metadata injection** for context

### Differences

| Aspect | SCONE-bench | Our System |
|--------|-------------|------------|
| **Goal** | Find exploits in deployed contracts | Fix vulnerabilities in source code |
| **Target** | Mainnet contracts (forked state) | Local contracts (clean slate) |
| **Success Metric** | Profit > 0.1 ETH | Vulnerability removed + compiles |
| **Network** | Forked mainnet at block | Local anvil (optional) |
| **Focus** | Blockchain interaction (cast, forge test) | Code editing (forge build, slither) |
| **Timeout** | 60 minutes | 10-20 minutes |

## Advanced Features

### Network Forking (Future)

For contracts that interact with external protocols:

```python
metadata = analyze_contract(contract)

if metadata.needs_network:
    # Start anvil fork
    env.start_anvil(fork_url="https://eth-mainnet.g.alchemy.com/v2/KEY")

    # Agent can test against real protocols
    # Similar to SCONE-bench's approach
```

### Iterative Dependency Resolution (Future)

```python
def iterative_resolve(contract, workspace):
    """Try compilation, parse errors, fix dependencies, retry."""

    for attempt in range(max_attempts):
        success, output = try_compile(workspace)

        if success:
            return True

        # Parse error and fix
        if "File import callback not supported" in output:
            install_missing_import(output)
        elif "Source file requires different compiler" in output:
            update_solc_version(output)
        else:
            break

    return False
```

### Template Learning

```python
def save_as_template(contract, workspace):
    """Save successful build as template for similar contracts."""

    template_name = f"learned_{contract.stem}_{hash(contract)}"
    template_path = templates_dir / template_name

    # Copy successful configuration
    shutil.copytree(workspace, template_path)

    # Future contracts with similar patterns can reuse
```

## Troubleshooting

### Common Issues

**Issue**: OpenZeppelin version mismatch
```
Error: Source file requires different compiler version
```

**Solution**: Update version map in `contract_analyzer.py`:
```python
oz_version_map = {
    "v3": "v3.4.2",
    "v4": "v4.9.6",  # Update this
    "v5": "v5.0.2",
}
```

---

**Issue**: External contract not found
```
Error: Source "contracts/External.sol" not found
```

**Solution**: Analyzer will create stubs automatically. Check `src/stubs/` directory.

---

**Issue**: Compilation timeout
```
Error: Compilation timeout after 180s
```

**Solution**: Increase timeout in `environment_builder.py`:
```python
timeout=300  # 5 minutes for large contracts
```

## Performance

### Typical Build Times

| Contract Type | Analysis | Dep Install | Compilation | Total |
|---------------|----------|-------------|-------------|-------|
| Standalone (0.8.x) | 0.1s | 0s | 2-5s | ~5s |
| With OZ v4 | 0.1s | 30-60s | 5-10s | ~70s |
| With OZ v5 | 0.1s | 30-60s | 5-10s | ~70s |
| Old (0.4.x) | 0.1s | 0s | 3-8s | ~8s |

**Note**: First-time `forge install` is slow (~60s). Subsequent installs are cached by Foundry.

### Optimization Strategies

1. **Pre-build Docker image** with common templates
2. **Cache forge installations** across episodes
3. **Skip compilation verification** if template is known good
4. **Use template matching** before dynamic resolution

## Future Enhancements

### 1. Advanced Dependency Detection
- Parse Solidity AST for exact imports
- Detect Hardhat remappings
- Support npm packages via `package.json`

### 2. Test Harness Generation
```solidity
// Auto-generate test contract
contract VulnerabilityTest is Test {
    TargetContract target;

    function setUp() public {
        target = new TargetContract();
    }

    function testVulnerabilityFixed() public {
        // Based on vulnerability type
    }
}
```

### 3. Multi-File Projects
- Handle contracts spread across multiple files
- Resolve internal imports
- Maintain project structure

### 4. Mainnet Forking
- Fork at block where contract was deployed
- Test fixes against real state
- Validate behavioral equivalence

## References

- **SCONE-bench**: [https://scone-bench.github.io/](https://scone-bench.github.io/)
- **Foundry Book**: [https://book.getfoundry.sh/](https://book.getfoundry.sh/)
- **OpenZeppelin**: [https://docs.openzeppelin.com/contracts/](https://docs.openzeppelin.com/contracts/)
- **SWE-agent**: [https://swe-agent.com/](https://swe-agent.com/)

---

**Last Updated**: 2026-01-13

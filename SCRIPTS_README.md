# Scripts Guide - Yudai SWE Agent

This guide explains how to run the various scripts in the `scripts/` directory and their differences.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Benchmark Exploit Scripts](#benchmark-exploit-scripts)
  - [V1: run_benchmark_exploit.py](#v1-run_benchmark_exploitpy)
  - [V2: run_benchmark_exploit_v2.py](#v2-run_benchmark_exploit_v2py)
  - [Key Differences V1 vs V2](#key-differences-v1-vs-v2)
- [Single Contract Scripts](#single-contract-scripts)
  - [run_exploit_episode.py](#run_exploit_episodepy)
  - [run_minimal_episode.py](#run_minimal_episodepy)
  - [run_security_task.py](#run_security_taskpy)
- [Environment Setup](#environment-setup)
- [Configuration Files](#configuration-files)

---

## Quick Reference

| Script | Purpose | Main Use Case | Version |
|--------|---------|---------------|---------|
| `run_benchmark_exploit.py` | Benchmark exploit generation | Run exploits against benchmark cases (basic output) | V1 |
| `run_benchmark_exploit_v2.py` | Benchmark exploit generation | Run exploits against benchmark cases (rich UI) | V2 |
| `run_exploit_episode.py` | Single contract exploit | Generate exploit for a local contract | - |
| `run_minimal_episode.py` | Security fix episode | Fix vulnerabilities using MuSe operators | - |
| `run_security_task.py` | Mini-swe-agent security fix | Fix vulnerabilities in training pairs | - |

---

## Benchmark Exploit Scripts

These scripts run exploit generation against the benchmark cases defined in `benchmark.csv`.

### V1: run_benchmark_exploit.py

**Purpose**: Run exploit generation with simple text-based output.

**Backend**:
- Environment: `ExploitFoundryEnvironment` → `FoundryEnvironment`
- Parser: `BlockchainCommandParser`
- Config: `benchmark_exploit.yaml`

**Basic Usage**:

```bash
# Run single case by index
python scripts/run_benchmark_exploit.py --index 0

# Run single case by name
python scripts/run_benchmark_exploit.py --case bancor

# Run all mainnet cases
python scripts/run_benchmark_exploit.py --chain mainnet

# Run with custom model
python scripts/run_benchmark_exploit.py --index 0 --model google/gemini-3-flash-preview

# Run first N cases
python scripts/run_benchmark_exploit.py --chain mainnet --limit 5
```

**Key Arguments**:

- `--index N`: Run case by 0-based row index
- `--case NAME`: Run specific case by name (e.g., 'bancor')
- `--chain CHAIN`: Filter by chain (`mainnet`, `bsc`, `base`)
- `--limit N`: Limit number of cases to run
- `--output DIR`: Output directory (default: `exploit_results`)
- `--config PATH`: Agent config name or path (default: `benchmark_exploit.yaml`)
- `--model NAME`: Model name override
- `--image IMAGE`: Docker image override (default: `yudai-base:latest`)
- `--cost-limit FLOAT`: Cost limit per episode (default: 10.0)
- `--no-yolo`: Disable yolo mode (require confirmations)
- `--interactive`: Use interactive agent
- `--env-file PATH`: Path to .env file
- `--benchmark-csv PATH`: Path to benchmark.csv
- `--cache-dir PATH`: Directory to cache fetched sources
- `-v, --verbose`: Enable verbose logging

**Environment Variables**:

```bash
# Required
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL_NAME=anthropic/claude-3.5-sonnet  # or use --model flag
ETHERSCAN_API_KEY=your_etherscan_key_here

# Optional
EXPLOIT_OUTPUT_DIR=exploit_results
EXPLOIT_CONFIG=benchmark_exploit.yaml
EXPLOIT_DOCKER_IMAGE=yudai-base:latest
EXPLOIT_COST_LIMIT=10.0
PLAYER_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
PLAYER_BALANCE_WEI=100000000000000000000000  # 100k ETH in wei
PLAYER_BALANCE_ETH=100000  # Alternative to PLAYER_BALANCE_WEI
ETH_RPC_URL=https://eth-mainnet.alchemyapi.io/v2/your_key
BSC_RPC_URL=https://bsc-dataseed.binance.org/
```

**Output**:

- Run summary: `exploit_results/benchmark_YYYYMMDD_HHMMSS_PID.json`
- Trajectories: `exploit_results/benchmark_*_N_casename.traj.json`
- Results: `exploit_results/benchmark_*_N_casename.result.json`

---

### V2: run_benchmark_exploit_v2.py

**Purpose**: Run exploit generation with rich UI and better progress tracking.

**Backend**:
- Environment: `ExploitFoundryEnvironmentV2` → `FoundryEnvironmentV2`
- Parser: `BlockchainCommandParserV2`
- Config: `benchmark_exploit_v2.yaml`
- UI: `BenchmarkUI` with live progress updates

**Basic Usage**:

```bash
# Run with beautiful UI (default)
python scripts/run_benchmark_exploit_v2.py --index 0 -v

# Run with simple output (no UI)
python scripts/run_benchmark_exploit_v2.py --index 0 --simple

# Run single case by name
python scripts/run_benchmark_exploit_v2.py --case bancor

# Run all mainnet cases
python scripts/run_benchmark_exploit_v2.py --chain mainnet

# Run with custom model
python scripts/run_benchmark_exploit_v2.py --index 0 --model google/gemini-3-flash-preview

# Run first N cases
python scripts/run_benchmark_exploit_v2.py --chain mainnet --limit 5
```

**Key Arguments**:

All arguments from V1, plus:

- `--simple`: Use simple output instead of rich UI
- `--no-ui`: Disable live UI (same as --simple)

**Environment Variables**:

Same as V1, with V2-specific overrides:

```bash
# V2-specific (fall back to V1 vars if not set)
EXPLOIT_OUTPUT_DIR_V2=exploit_results_v2
EXPLOIT_CONFIG_V2=benchmark_exploit_v2.yaml
EXPLOIT_COST_LIMIT_V2=20.0  # Note: higher default than V1
```

**Output**:

- Run summary: `exploit_results_v2/benchmark_YYYYMMDD_HHMMSS_PID.json`
- Trajectories: `exploit_results_v2/benchmark_*_N_casename.traj.json`
- Results: `exploit_results_v2/benchmark_*_N_casename.result.json`
- Live UI with progress bars and status updates (unless --simple)

---

### Key Differences V1 vs V2

| Feature | V1 | V2 |
|---------|----|----|
| **Environment Class** | `ExploitFoundryEnvironment` | `ExploitFoundryEnvironmentV2` |
| **Parser Class** | `BlockchainCommandParser` | `BlockchainCommandParserV2` |
| **UI** | Text-based output | Rich UI with progress bars |
| **Default Cost Limit** | 10.0 USD | 20.0 USD |
| **Default Output Dir** | `exploit_results` | `exploit_results_v2` |
| **Default Config** | `benchmark_exploit.yaml` | `benchmark_exploit_v2.yaml` |
| **UI Toggle** | N/A | `--simple` or `--no-ui` |
| **Verbose Flag** | `-v` for debug logs | `-v` for debug logs + UI details |

**When to use V1**:
- Simple CI/CD pipelines
- Headless environments without terminal UI support
- Debugging with raw text output
- Lower cost limits per case

**When to use V2**:
- Interactive development
- Monitoring long-running benchmarks
- Better visualization of progress
- Higher cost limits for complex exploits

---

## Single Contract Scripts

### run_exploit_episode.py

**Purpose**: Run a single exploit generation episode against a local contract.

**Basic Usage**:

```bash
# Run on default contract
python scripts/run_exploit_episode.py

# Run on specific contract
python scripts/run_exploit_episode.py --contract contracts/MyContract.sol

# Run with custom model and settings
python scripts/run_exploit_episode.py \
  --contract contracts/SimpleBank.sol \
  --model anthropic/claude-3.5-sonnet \
  --output exploit_results \
  --cost-limit 5.0
```

**Key Arguments**:

- `--contract PATH`: Path to target contract (default: `contracts/SimpleBank.sol`)
- `--output DIR`: Output directory (default: `exploit_results`)
- `--config PATH`: Agent config name or path (default: `foundry_exploit.yaml`)
- `--model NAME`: Model name override
- `--image IMAGE`: Docker image override
- `--cost-limit FLOAT`: Cost limit override (default: 5.0)
- `--no-yolo`: Disable yolo mode
- `--interactive`: Use interactive agent
- `--env-file PATH`: Path to .env file

**Environment Variables**:

```bash
# Required
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL_NAME=anthropic/claude-3.5-sonnet
DEPLOYER_PRIVATE_KEY=0x...  # Or PRIVATE_KEY
PLAYER_ADDRESS=0x...

# Optional
EXPLOIT_CONTRACT_PATH=contracts/SimpleBank.sol
EXPLOIT_OUTPUT_DIR=exploit_results
EXPLOIT_CONFIG=foundry_exploit.yaml
EXPLOIT_DOCKER_IMAGE=yudai-base:latest
EXPLOIT_COST_LIMIT=5.0
PLAYER_BALANCE_WEI=100000000000000000000000
PLAYER_BALANCE_ETH=100000
ANVIL_PORT=8545
ETH_RPC_URL=https://eth-mainnet.alchemyapi.io/v2/your_key
EXPLOIT_FORK_URL=https://eth-mainnet.alchemyapi.io/v2/your_key
EXPLOIT_FORK_BLOCK=12345678
```

**Output**:

- Episode result JSON with profit metrics
- Target contract address and name
- Success/failure status

---

### run_minimal_episode.py

**Purpose**: Run a minimal security-fix episode using vulnerability injection (MuSe operators).

**Basic Usage**:

```bash
# Run with default contract and RE operator
python scripts/run_minimal_episode.py

# Run on specific contract with specific operators
python scripts/run_minimal_episode.py \
  -c contracts/SimpleBank.sol \
  --operators RE,TX

# Run with custom model
python scripts/run_minimal_episode.py \
  -c contracts/MyContract.sol \
  -m anthropic/claude-3.5-sonnet \
  --operators RE
```

**Key Arguments**:

- `--contract, -c PATH`: Path to clean Solidity contract (default: `contracts/SimpleBank.sol`)
- `--model, -m NAME`: Model name (overrides `OPENROUTER_MODEL_NAME`)
- `--operators, -o LIST`: Comma-separated MuSe operators (default: `RE`)
- `--output DIR`: Directory for results (default: `rl_results`)
- `--image IMAGE`: Docker image (default: `yudai-complete:latest`)
- `--config NAME`: Agent config (default: `security_fix_openrouter`)
- `--cost-limit FLOAT`: Max cost in USD (default: 3.0)
- `--no-yolo`: Disable yolo mode
- `--env-file PATH`: Path to .env file

**MuSe Operators**:

Common operators for vulnerability injection:
- `RE`: Reentrancy
- `TX`: Transaction ordering
- `IO`: Integer overflow
- `AC`: Access control
- `UV`: Uninitialized variables
- ... (see MuSe documentation for full list)

**Environment Variables**:

```bash
# Required
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL_NAME=anthropic/claude-3.5-sonnet
```

**Output**:

- Episode ID
- Mutation operator used
- Vulnerability fixed: true/false
- Compilation passed: true/false
- New vulnerabilities introduced
- Total reward score
- Results JSON: `rl_results/{episode_id}.result.json`

---

### run_security_task.py

**Purpose**: Run mini-swe-agent on vulnerable contracts from training pairs.

**Basic Usage**:

```bash
# Run on a training pair
python scripts/run_security_task.py --pair dataset/pairs/Token-m46f345c9/

# Run with custom model
python scripts/run_security_task.py \
  --pair dataset/pairs/Token-m46f345c9/ \
  --model claude-sonnet-4-20250514

# Run in interactive mode
python scripts/run_security_task.py \
  --pair dataset/pairs/Token-m46f345c9/ \
  --interactive

# Dry run (show prompt without running)
python scripts/run_security_task.py \
  --pair dataset/pairs/Token-m46f345c9/ \
  --dry-run
```

**Key Arguments**:

- `--pair, -p PATH`: Path to training pair directory (required)
- `--model, -m NAME`: Model to use (default: `claude-sonnet-4-20250514`)
- `--config, -c NAME`: Config file (default: `security`)
- `--output, -o PATH`: Output file for trajectory JSON
- `--interactive, -i`: Run in interactive mode
- `--dry-run`: Show task prompt without running agent

**Training Pair Structure**:

Each training pair directory should contain:
```
dataset/pairs/Token-m46f345c9/
├── original.sol       # Original clean contract
├── vulnerable.sol     # Contract with injected vulnerability
└── metadata.json      # Vulnerability metadata (type, location, severity)
```

**Output**:

- Trajectory JSON: `trajectories/{pair_id}.json` (or custom path)
- Status and message count
- Agent execution details

---

## Environment Setup

### 1. Install Dependencies

```bash
# Install the package in development mode
pip install -e '.[full]'
```

### 2. Create .env File

```bash
# Copy example file
cp .env.example .env

# Edit with your API keys
nano .env
```

### 3. Minimal .env Configuration

```bash
# Required for all scripts
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL_NAME=anthropic/claude-3.5-sonnet

# Required for benchmark scripts
ETHERSCAN_API_KEY=your_etherscan_api_key_here
ETH_RPC_URL=https://eth-mainnet.alchemyapi.io/v2/your_key
BSC_RPC_URL=https://bsc-dataseed.binance.org/

# Required for local contract scripts
DEPLOYER_PRIVATE_KEY=0x1234...  # Private key for contract deployment
PLAYER_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

### 4. Docker Setup (Optional)

```bash
# Build docker image
cd docker
docker build -t yudai-base:latest -f Dockerfile.base .

# Or use pre-built image
docker pull your-registry/yudai-base:latest
```

---

## Configuration Files

Configuration files are located in `src/minisweagent/config/`:

| Config File | Used By | Purpose |
|-------------|---------|---------|
| `benchmark_exploit.yaml` | V1 benchmark script | V1 exploit generation settings |
| `benchmark_exploit_v2.yaml` | V2 benchmark script | V2 exploit generation settings |
| `foundry_exploit.yaml` | Single contract script | Local contract exploitation |
| `security_fix_openrouter.yaml` | Minimal episode script | Security fix with OpenRouter |
| `security.yaml` | Security task script | Mini-swe-agent security config |

**Key Configuration Settings**:

- System templates: Instructions given to the LLM
- Instance templates: Task-specific prompts
- Model parameters: Temperature, max tokens, etc.
- Environment settings: Timeout, memory limits, etc.
- Cost limits: Per-episode spending caps

---

## Common Workflows

### Benchmark Testing Workflow (V2)

```bash
# 1. Test single case first
python scripts/run_benchmark_exploit_v2.py --index 0 -v

# 2. Run a few cases to validate
python scripts/run_benchmark_exploit_v2.py --chain mainnet --limit 3 -v

# 3. Run full benchmark
python scripts/run_benchmark_exploit_v2.py --chain mainnet

# 4. Analyze results
jupyter notebook exploit_results_eda.ipynb
```

### Local Contract Development Workflow

```bash
# 1. Deploy and test contract
python scripts/run_exploit_episode.py \
  --contract contracts/MyContract.sol \
  --interactive

# 2. Review results
cat exploit_results/latest_episode.result.json | jq .

# 3. Iterate on contract or agent config
# ... make changes ...

# 4. Re-run
python scripts/run_exploit_episode.py \
  --contract contracts/MyContract.sol
```

### Security Training Workflow

```bash
# 1. Create training pair with vulnerability
python scripts/run_minimal_episode.py \
  -c contracts/CleanContract.sol \
  --operators RE

# 2. Test security fix agent
python scripts/run_security_task.py \
  --pair dataset/pairs/CleanContract-mXXXXXX/

# 3. Validate fix
forge build
slither vulnerable.sol
```

---

## Troubleshooting

### Common Issues

**1. API Key Not Found**
```bash
Error: OPENROUTER_API_KEY not set
```
→ Solution: Check `.env` file exists and contains API key

**2. Benchmark CSV Not Found**
```bash
Error: benchmark.csv not found
```
→ Solution: Ensure `benchmark.csv` exists in project root or use `--benchmark-csv`

**3. Contract Not Found**
```bash
Error: Contract not found: contracts/MyContract.sol
```
→ Solution: Use absolute path or ensure contract exists relative to project root

**4. Docker Image Not Found**
```bash
Error: Docker image 'yudai-base:latest' not found
```
→ Solution: Build docker image or use `--image` flag with existing image

**5. Cost Limit Exceeded**
```bash
Warning: Episode stopped due to cost limit
```
→ Solution: Increase with `--cost-limit` or `EXPLOIT_COST_LIMIT` env var

**6. RPC URL Issues**
```bash
Warning: No RPC URL for mainnet
```
→ Solution: Set `ETH_RPC_URL` and `BSC_RPC_URL` in `.env`

### Debug Mode

Enable verbose logging for all scripts:

```bash
python scripts/run_benchmark_exploit_v2.py --index 0 -v
```

This will show:
- Detailed command execution
- Environment variable values (masked for API keys)
- Agent reasoning steps
- Full error tracebacks

---

## Performance Tips

1. **Use V2 with --simple for CI/CD**: Disables UI overhead
2. **Set appropriate cost limits**: Avoid runaway costs
3. **Cache source code**: Use `--cache-dir` to avoid re-fetching from Etherscan
4. **Limit concurrent runs**: Benchmark scripts run sequentially by design
5. **Use faster models for testing**: e.g., `google/gemini-3-flash-preview`
6. **Monitor output files**: Check `exploit_results_v2/*.json` for progress

---

## Additional Resources

- [CLAUDE.md](./CLAUDE.md) - Project overview and architecture
- [EXPLOIT_EDA_README.md](./EXPLOIT_EDA_README.md) - Results analysis guide
- [benchmark.csv](./benchmark.csv) - Benchmark case definitions
- [MuSe/README.md](./MuSe/README.md) - Mutation operators documentation
- [docker/README.md](./docker/README.md) - Docker setup guide

---

## Contributing

When adding new scripts:

1. Follow naming convention: `run_{purpose}.py`
2. Add comprehensive docstring with usage examples
3. Support `--help` flag with argparse
4. Load `.env` file for configuration
5. Output structured JSON results
6. Update this README with new script documentation

---

**Last Updated**: 2026-02-15

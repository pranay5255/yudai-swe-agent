# Complete System Index

## Overview

This document provides a complete index of the vulnerability fixing system with Docker hierarchy and environment builder.

## System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VULNERABILITY FIXING SYSTEM                      │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Contract Analysis│→ │Environment Builder│→ │ Episode Runner  │  │
│  │ (Detect deps)    │  │(Create workspace) │  │ (Agent + Reward)│  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│          │                      │                      │           │
│          ▼                      ▼                      ▼           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Docker Image Hierarchy                          │  │
│  │  yudai-base → sol-0.4 / sol-0.8 / sol-0.8-oz-v4 / oz-v5     │  │
│  │  (15x faster with pre-built templates)                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Documentation Structure

### 🚀 Quick Start Guides

| Document | Purpose | Time to Read |
|----------|---------|--------------|
| **[DOCKER_HIERARCHY_QUICKSTART.md](DOCKER_HIERARCHY_QUICKSTART.md)** | **Start here!** Quick reference for using Docker hierarchy | 5 min |
| **[ENVIRONMENT_SETUP_SUMMARY.md](ENVIRONMENT_SETUP_SUMMARY.md)** | Environment builder overview and next steps | 10 min |

### 📚 Comprehensive Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [docker/README.md](docker/README.md) | Complete Docker hierarchy reference | Developers building/maintaining images |
| [docs/ENVIRONMENT_BUILDER.md](docs/ENVIRONMENT_BUILDER.md) | Environment builder technical docs | Developers extending the system |
| [CLAUDE.md](CLAUDE.md) | Project structure and coding conventions | Claude Code (AI assistant) |

### 📊 Technical Details

| Document | Purpose | Contains |
|----------|---------|----------|
| [DOCKER_HIERARCHY_SUMMARY.md](DOCKER_HIERARCHY_SUMMARY.md) | Complete implementation summary | Architecture, performance, integration |
| [docker/ARCHITECTURE_DIAGRAM.md](docker/ARCHITECTURE_DIAGRAM.md) | Visual system architecture | Diagrams, workflows, decision trees |

## File Locations

### Core Implementation

```
vulnerability_injection/
├── contract_analyzer.py          # Analyze contracts for deps/version
├── environment_builder.py         # Build compilation-ready workspaces
├── episode.py                     # Run RL episodes (updated)
├── muse_wrapper.py               # Vulnerability injection
├── security_tools.py             # Slither/Aderyn wrappers
└── models.py                     # Data models
```

### Docker Images

```
docker/
├── Dockerfile.base                # Parent image (Foundry + tools)
├── templates/
│   ├── Dockerfile.sol-0.4-standalone
│   ├── Dockerfile.sol-0.8-standalone
│   ├── Dockerfile.sol-0.8-oz-v4
│   └── Dockerfile.sol-0.8-oz-v5
├── build-all.sh                   # Build all images
├── docker-compose.templates.yml   # Docker Compose config
├── README.md                      # Full Docker docs
└── ARCHITECTURE_DIAGRAM.md        # Visual diagrams
```

### Scripts

```
scripts/
├── run_minimal_episode.py         # Run single episode
├── test_environment_builder.py    # Test builder on all contracts
└── run_security_task.py          # Run security fix task
```

### Contracts

```
contracts/
├── vulnerabilities/               # 14 vulnerable contracts
│   ├── reentrancy/
│   ├── arithmetic/
│   ├── access_control/
│   ├── unchecked_calls/
│   ├── denial_of_service/
│   └── time_manipulation/
├── audited/                       # 3 production tokens
├── real_world/                    # 4 real contracts (secure/vulnerable)
└── README.md                      # Contract collection docs
```

## Getting Started

### Step 1: Build Docker Images (One-Time, ~12 min)

```bash
# Build all images
./docker/build-all.sh

# Or build only what you need
./docker/build-all.sh --base-only
docker compose -f docker/docker-compose.templates.yml build sol-0.8-oz-v4
```

### Step 2: Test the System

```bash
# Test contract analysis
python vulnerability_injection/contract_analyzer.py contracts/SimpleBank.sol

# Test environment building
python vulnerability_injection/environment_builder.py contracts/SimpleBank.sol

# Test on all contracts
python scripts/test_environment_builder.py
```

### Step 3: Run an Episode

```bash
# Simple example
python scripts/run_minimal_episode.py -c contracts/SimpleBank.sol

# With options
python scripts/run_minimal_episode.py \
  -c contracts/vulnerabilities/reentrancy/ethbank_reentrancy.sol \
  --model anthropic/claude-3.5-sonnet \
  --operators RE \
  --output results/
```

### Step 4: Check Performance

```bash
# Watch the logs for:
# - Selected Docker image
# - Template extraction time
# - Compilation time
# - Total setup time

# Compare with old system:
# Old: ~75-85s setup
# New: ~5-7s setup
# Speedup: 12-15x
```

## Usage Patterns

### Pattern 1: Auto-Selection (Recommended)

System automatically picks the right Docker image:

```python
from vulnerability_injection.environment_builder import EnvironmentBuilder

# Auto-select based on contract analysis
builder = EnvironmentBuilder(
    use_docker=True,
    auto_select_image=True  # Default
)

result = builder.build_environment(contract_path, workspace)
print(f"Selected: {result.docker_image}")
```

### Pattern 2: Manual Image Selection

Force a specific image:

```python
builder = EnvironmentBuilder(
    use_docker=True,
    docker_image="yudai-sol-0.8-oz-v4:latest",
    auto_select_image=False
)

result = builder.build_environment(contract_path, workspace)
```

### Pattern 3: Local (No Docker)

Use local Foundry installation:

```python
builder = EnvironmentBuilder(
    use_docker=False  # No Docker, uses local forge
)

result = builder.build_environment(contract_path, workspace)
```

## Decision Trees

### Which Image Should I Use?

```
My contract uses Solidity...

0.4.x → yudai-sol-0.4-standalone:latest
0.5.x → yudai-sol-0.8-standalone:latest (fallback)
0.6.x → yudai-sol-0.8-standalone:latest (fallback)
0.7.x → yudai-sol-0.8-standalone:latest (fallback)
0.8.x:
  ├─ imports OpenZeppelin?
  │  ├─ Yes:
  │  │  ├─ v5 features (custom errors, Ownable(msg.sender))? → yudai-sol-0.8-oz-v5:latest
  │  │  └─ v4 style? → yudai-sol-0.8-oz-v4:latest
  │  └─ No → yudai-sol-0.8-standalone:latest
```

### Which Documentation Should I Read?

```
I want to...

Build Docker images:
  └→ docker/README.md + DOCKER_HIERARCHY_QUICKSTART.md

Understand the system:
  └→ DOCKER_HIERARCHY_SUMMARY.md + docker/ARCHITECTURE_DIAGRAM.md

Extend the environment builder:
  └→ docs/ENVIRONMENT_BUILDER.md

Add a new template:
  └→ docker/README.md (Maintenance section)

Troubleshoot issues:
  └→ DOCKER_HIERARCHY_QUICKSTART.md (Troubleshooting section)

Run experiments:
  └→ ENVIRONMENT_SETUP_SUMMARY.md (Next Steps section)
```

## Key Concepts

### Contract Analysis
- **What**: Parsing contracts to detect version, dependencies, imports
- **Why**: Select appropriate template/image automatically
- **Code**: `vulnerability_injection/contract_analyzer.py`

### Environment Building
- **What**: Creating compilation-ready Foundry workspaces
- **Why**: Agent needs working environment before starting
- **Code**: `vulnerability_injection/environment_builder.py`

### Docker Hierarchy
- **What**: Parent-child image structure with pre-built templates
- **Why**: 15x faster setup (no runtime dependency installation)
- **Code**: `docker/` directory

### Episode Running
- **What**: Complete workflow: inject vuln → build env → agent fixes → compute reward
- **Why**: Training data for RL-based vulnerability fixing
- **Code**: `vulnerability_injection/episode.py`

## Performance Metrics

### Setup Time

| Stage | Before | After | Improvement |
|-------|--------|-------|-------------|
| Project init | 5s | 2s | 2.5x |
| Dep install | 60s | 0s | ∞ |
| First compile | 10s | 3s | 3.3x |
| **Total** | **75s** | **5s** | **15x** |

### Episode Metrics

- **Break-even**: 11 episodes (12 min build time ÷ 70s savings)
- **Typical usage**: 100-1000 episodes
- **Time saved**: Hours over the lifetime of the project

### Disk Usage

- **Without hierarchy**: ~500 MB × N episodes (redundant)
- **With hierarchy**: 1.6 GB base + minimal per episode
- **Savings**: Significant for large-scale experiments

## Common Workflows

### Workflow 1: Develop and Test

```bash
# 1. Make changes to environment_builder.py
vim vulnerability_injection/environment_builder.py

# 2. Test on a single contract
python vulnerability_injection/environment_builder.py contracts/SimpleBank.sol

# 3. Test on all contracts
python scripts/test_environment_builder.py --category vulnerabilities

# 4. Run full episode
python scripts/run_minimal_episode.py -c contracts/SimpleBank.sol
```

### Workflow 2: Add New Template

```bash
# 1. Create Dockerfile
vim docker/templates/Dockerfile.sol-0.8-uniswap

# 2. Add to build script
vim docker/build-all.sh
# Add: templates["sol-0.8-uniswap"]="docker/templates/Dockerfile.sol-0.8-uniswap"

# 3. Build
docker build -t yudai-sol-0.8-uniswap:latest -f docker/templates/Dockerfile.sol-0.8-uniswap .

# 4. Test
docker run -it --rm yudai-sol-0.8-uniswap:latest bash

# 5. Update environment builder
vim vulnerability_injection/environment_builder.py
# Add to TEMPLATE_TO_IMAGE mapping
```

### Workflow 3: Debug Episode Issues

```bash
# 1. Enable verbose logging
python scripts/run_minimal_episode.py -c contracts/problem.sol -v

# 2. Check environment build
python vulnerability_injection/environment_builder.py contracts/problem.sol

# 3. Test template directly
docker run -it --rm yudai-sol-0.8-oz-v4:latest bash
cd /templates/sol-0.8-oz-v4
forge build

# 4. Check contract analysis
python vulnerability_injection/contract_analyzer.py contracts/problem.sol
```

## Troubleshooting Index

| Issue | Solution | Document |
|-------|----------|----------|
| "yudai-base not found" | Build base image | DOCKER_HIERARCHY_QUICKSTART.md |
| Slow template extraction | Check Docker daemon | DOCKER_HIERARCHY_QUICKSTART.md |
| Compilation fails | Verify template | docker/README.md |
| Wrong image selected | Check contract analysis | docs/ENVIRONMENT_BUILDER.md |
| OZ version mismatch | Update version map | vulnerability_injection/contract_analyzer.py |
| Disk space full | Prune images | DOCKER_HIERARCHY_QUICKSTART.md |

## Best Practices

### For Users

1. **Build images once**: One-time 12-minute investment
2. **Use auto-selection**: Let system pick optimal image
3. **Monitor logs**: Check which image was selected
4. **Report issues**: If wrong image is selected, file an issue

### For Developers

1. **Update base sparingly**: Only when tools need updating
2. **Version templates**: Tag with specific versions
3. **Test thoroughly**: Verify each template compiles
4. **Document changes**: Update READMEs when adding templates

### For Researchers

1. **Batch experiments**: Build images once, run many episodes
2. **Track metrics**: Compare setup times before/after
3. **Custom templates**: Create specialized images for your needs
4. **Share results**: Contribute improvements back

## Related Systems

### Comparison with SCONE-bench

| Feature | SCONE-bench | Our System |
|---------|-------------|------------|
| **Goal** | Exploit finding | Vulnerability fixing |
| **Approach** | Monolithic image | Hierarchical images |
| **Setup** | Runtime install | Pre-built templates |
| **Speed** | ~60s | ~5s (12x faster) |
| **Flexibility** | Single config | Multiple templates |

### Integration with mini-swe-agent

- Uses same agent framework
- Compatible with existing configs
- Transparent to agent (no code changes)
- Works with all models (Claude, GPT-4, etc.)

## Future Enhancements

### Short Term
- [ ] Add more templates (Hardhat, Uniswap, Aave)
- [ ] Smart contract test harness generation
- [ ] Mainnet forking support
- [ ] Multi-file project support

### Long Term
- [ ] CI/CD automation for image builds
- [ ] Template recommendation system
- [ ] Automated dependency detection
- [ ] Performance profiling dashboard

## Support and Contributing

### Getting Help

1. **Check documentation**: Start with QUICKSTART guides
2. **Search issues**: GitHub issue tracker
3. **Ask in discussions**: Community forum
4. **File bug report**: Include logs and reproduction steps

### Contributing

1. **Add templates**: New Dockerfiles welcome
2. **Improve detection**: Better contract analysis
3. **Fix bugs**: Bug fixes appreciated
4. **Update docs**: Documentation improvements

## Version History

- **2026-01-13**: Initial release
  - Docker hierarchy with 4 templates
  - Environment builder with auto-selection
  - 15x speedup in setup time
  - Complete documentation

## License

See main project LICENSE file.

---

**Last Updated**: 2026-01-13
**Maintainer**: yudai-team
**Status**: ✅ Production Ready


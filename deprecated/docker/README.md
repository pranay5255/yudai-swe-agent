# Docker Image Hierarchy

## Overview

This directory contains a hierarchical Docker image system optimized for smart contract vulnerability fixing. The hierarchy consists of a **base parent image** with common tools and **specialized child images** with pre-configured Foundry templates.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  yudai-base:latest (Parent Image)                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ - Foundry (forge, cast, anvil, chisel)               │  │
│  │ - Python 3.12 + uv                                    │  │
│  │ - Security Tools:                                     │  │
│  │   * Slither 0.10.2                                    │  │
│  │   * Mythril 0.24.8                                    │  │
│  │   * Aderyn 0.6.5                                      │  │
│  │   * Echidna 2.2.5                                     │  │
│  │ - Multiple solc versions (0.4.26, 0.5.17, ..., 0.8.24)│  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┬────────────────┐
            │               │               │                │
            ▼               ▼               ▼                ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  sol-0.4         │ │  sol-0.8     │ │ sol-0.8-oz-v4│ │ sol-0.8-oz-v5│
│  standalone      │ │  standalone  │ │              │ │              │
├──────────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
│ + solc 0.4.26    │ │ + solc 0.8.20│ │ + solc 0.8.20│ │ + solc 0.8.24│
│ + Template       │ │ + Template   │ │ + Template   │ │ + Template   │
│   (no deps)      │ │   (no deps)  │ │ + OZ v4.9.6  │ │ + OZ v5.0.2  │
└──────────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

## Images

### Parent: `yudai-base:latest`

**Purpose**: Foundation image with all tools
**Size**: ~1.2 GB
**Build Time**: 3-5 minutes (first build), seconds (cached)

**Contents**:
- Foundry toolkit (latest)
- Python 3.12 with uv package manager
- Slither static analyzer
- Mythril symbolic executor
- Aderyn detector
- Echidna fuzzer
- Multiple solc versions: 0.4.26, 0.5.17, 0.6.12, 0.7.6, 0.8.20, 0.8.24

**Dockerfile**: `Dockerfile.base`

### Child: `yudai-sol-0.4-standalone:latest`

**Purpose**: Old Solidity contracts (pre-0.5.0)
**Size**: +50 MB
**Build Time**: 1-2 minutes

**Use Cases**:
- Reentrancy examples
- Integer overflow bugs
- Old audit reports
- Historical vulnerabilities

**Template Location**: `/templates/sol-0.4-standalone`
**Solidity Version**: 0.4.26
**Dependencies**: None

### Child: `yudai-sol-0.8-standalone:latest`

**Purpose**: Modern contracts without external dependencies
**Size**: +50 MB
**Build Time**: 1-2 minutes

**Use Cases**:
- Simple contracts
- Custom implementations
- Educational examples

**Template Location**: `/templates/sol-0.8-standalone`
**Solidity Version**: 0.8.20
**Dependencies**: None

### Child: `yudai-sol-0.8-oz-v4:latest`

**Purpose**: Contracts using OpenZeppelin v4 (most common)
**Size**: +150 MB
**Build Time**: 2-3 minutes

**Use Cases**:
- ERC20/ERC721 tokens
- Access control (Ownable, AccessControl)
- Reentrancy protection
- 2022-2023 era contracts

**Template Location**: `/templates/sol-0.8-oz-v4`
**Solidity Version**: 0.8.20
**Dependencies**: OpenZeppelin Contracts v4.9.6

### Child: `yudai-sol-0.8-oz-v5:latest`

**Purpose**: Contracts using OpenZeppelin v5 (latest)
**Size**: +150 MB
**Build Time**: 2-3 minutes

**Use Cases**:
- Latest OZ features
- Custom errors
- Namespaced storage
- 2024+ contracts

**Template Location**: `/templates/sol-0.8-oz-v5`
**Solidity Version**: 0.8.24
**Dependencies**: OpenZeppelin Contracts v5.0.2

## Building Images

### Option 1: Build Script (Recommended)

```bash
# Build all images
./docker/build-all.sh

# Build only base image
./docker/build-all.sh --base-only

# Build with no cache (force rebuild)
./docker/build-all.sh --no-cache

# Build and push to registry
./docker/build-all.sh --push --registry ghcr.io/username
```

### Option 2: Docker Compose

```bash
# Build all images
docker compose -f docker/docker-compose.templates.yml build

# Build specific image
docker compose -f docker/docker-compose.templates.yml build base
docker compose -f docker/docker-compose.templates.yml build sol-0.8-oz-v4

# Build in parallel
docker compose -f docker/docker-compose.templates.yml build --parallel
```

### Option 3: Manual Build

```bash
# Build base image
docker build -t yudai-base:latest -f docker/Dockerfile.base .

# Build template images (requires base to be built first)
docker build -t yudai-sol-0.4-standalone:latest -f docker/templates/Dockerfile.sol-0.4-standalone .
docker build -t yudai-sol-0.8-standalone:latest -f docker/templates/Dockerfile.sol-0.8-standalone .
docker build -t yudai-sol-0.8-oz-v4:latest -f docker/templates/Dockerfile.sol-0.8-oz-v4 .
docker build -t yudai-sol-0.8-oz-v5:latest -f docker/templates/Dockerfile.sol-0.8-oz-v5 .
```

## Using Images

### In Episodes

The environment builder automatically selects the appropriate image:

```python
# In episode.py or run_minimal_episode.py
result = run_episode(
    clean_contract=Path("contracts/SimpleBank.sol"),
    output_dir=Path("rl_results"),
    model_name="claude-sonnet-4-20250514",
    # Image is auto-selected based on contract analysis
)
```

### Manual Container Launch

```bash
# Launch container with template
docker run -it --rm \
  -v $(pwd):/host \
  yudai-sol-0.8-oz-v4:latest \
  bash

# Inside container, copy template
cp -r /templates/sol-0.8-oz-v4/* /workspace/
cd /workspace
forge build
```

### In Environment Builder

```python
from vulnerability_injection.environment_builder import EnvironmentBuilder

builder = EnvironmentBuilder(
    templates_dir=Path("/templates"),  # Pre-built templates in Docker
    use_docker=True,
    docker_image="yudai-sol-0.8-oz-v4:latest"  # Specific image
)

result = builder.build_environment(contract_path, workspace)
```

## Benefits

### Speed Improvements

| Stage | Without Hierarchy | With Hierarchy | Speedup |
|-------|------------------|----------------|---------|
| Environment Setup | 60-90s | 2-5s | **15-20x** |
| OpenZeppelin Install | 60s | 0s (pre-installed) | **∞x** |
| First `forge build` | 5-10s | 2-3s | **2-3x** |
| **Total per Episode** | **70-100s** | **5-10s** | **10-15x** |

### Disk Space

- **Without**: Every episode downloads OZ (~150 MB each)
- **With**: One-time download, shared across episodes
- **Savings**: ~150 MB × N episodes

### Reliability

- ✅ Pre-verified compilation
- ✅ Consistent environments
- ✅ No internet dependency at runtime
- ✅ Offline-capable

## Template Selection Logic

The environment builder analyzes contracts and selects templates:

```python
def select_template(contract: Path) -> str:
    metadata = analyze_contract(contract)

    # Check Solidity version
    if metadata.solidity_version.startswith("0.4"):
        return "sol-0.4-standalone"

    # Check for OpenZeppelin
    if metadata.has_openzeppelin:
        if metadata.oz_version == "v5":
            return "sol-0.8-oz-v5"
        else:
            return "sol-0.8-oz-v4"  # Default to v4 (most common)

    # Default: standalone 0.8.x
    return "sol-0.8-standalone"
```

## Maintenance

### Adding New Templates

1. Create new Dockerfile in `docker/templates/`:
   ```dockerfile
   FROM yudai-base:latest
   WORKDIR /templates/my-template
   RUN forge init --no-commit .
   # Configure as needed
   ```

2. Add to `build-all.sh`:
   ```bash
   templates["my-template"]="docker/templates/Dockerfile.my-template"
   ```

3. Add to `docker-compose.templates.yml`:
   ```yaml
   my-template:
     build:
       dockerfile: docker/templates/Dockerfile.my-template
   ```

### Updating Base Image

```bash
# Rebuild base with new tools
docker build -t yudai-base:latest -f docker/Dockerfile.base . --no-cache

# Rebuild all children (they'll use new base)
./docker/build-all.sh
```

### Updating Dependencies

To update OpenZeppelin versions:

```dockerfile
# In Dockerfile.sol-0.8-oz-v4
RUN forge install OpenZeppelin/openzeppelin-contracts@v4.9.7 --no-commit
```

Then rebuild:
```bash
docker build -t yudai-sol-0.8-oz-v4:latest -f docker/templates/Dockerfile.sol-0.8-oz-v4 .
```

## Troubleshooting

### Issue: "yudai-base:latest not found"

**Cause**: Child images depend on base image
**Solution**: Build base first
```bash
./docker/build-all.sh --base-only
```

### Issue: Template compilation fails

**Cause**: Dependency version mismatch
**Solution**: Check Solidity version compatibility
```bash
# Inside container
solc-select use 0.8.20
forge build
```

### Issue: Large image sizes

**Solution**: Clean up build artifacts
```dockerfile
RUN forge build && rm -rf out cache
```

### Issue: Slow builds

**Solution**: Use Docker layer caching
```bash
# Don't use --no-cache unnecessarily
docker build -t yudai-base:latest -f docker/Dockerfile.base .
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Build Docker Images

on:
  push:
    branches: [main]
    paths: ['docker/**']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build images
        run: ./docker/build-all.sh
      - name: Push to registry
        run: ./docker/build-all.sh --push --registry ghcr.io/${{ github.repository }}
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
if git diff --cached --name-only | grep -q '^docker/'; then
    echo "Docker files changed, rebuilding base image..."
    ./docker/build-all.sh --base-only
fi
```

## Comparison with SCONE-bench

| Aspect | SCONE-bench | Our System |
|--------|-------------|------------|
| **Base Image** | Single monolithic | Layered hierarchy |
| **Templates** | Runtime setup | Pre-built in image |
| **Dependencies** | Downloaded per run | Cached in image |
| **Setup Time** | ~60s | ~5s |
| **Disk Usage** | High (redundant) | Low (shared layers) |
| **Offline** | No | Yes |

## References

- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Foundry Book](https://book.getfoundry.sh/)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
- [SCONE-bench](https://scone-bench.github.io/)

---

**Last Updated**: 2026-01-13

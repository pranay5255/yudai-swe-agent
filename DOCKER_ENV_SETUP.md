# Docker Environment Setup - Complete Guide

**Status:** ✅ All 8 tools working (100% success rate)
**Date:** 2026-01-06
**Docker Image:** `yudai-complete`

## Overview

This document describes the complete Docker environment setup for the Yudai smart contract security analysis platform. The environment now achieves parity with the local development setup using Python 3.12 and uv package manager.

---

## Environment Comparison

| Component | Local Environment | Docker Environment | Status |
|-----------|-------------------|-------------------|--------|
| Python | 3.12.3 | 3.12.12 | ✅ Compatible |
| Package Manager | uv 0.6.5 | uv 0.9.21 | ✅ Compatible |
| Virtual Env | Supported | Dual venvs (main + mythril) | ✅ Working |
| Foundry Tools | N/A | v1.5.1-nightly | ✅ Working |

---

## Key Features

### 1. Python 3.12 Support
- Both local and Docker environments use Python 3.12.x
- Installed from deadsnakes PPA in Docker
- Managed with uv for consistent dependency resolution

### 2. uv Package Manager
- Fast, modern Python package manager
- Replaces traditional pip+venv workflow
- Shared between local and Docker environments
- Enables reproducible builds with uv.lock

### 3. Dual Virtual Environment Architecture

**Problem Solved:** Slither and Mythril have incompatible dependencies:
- Slither requires: `eth-typing>=3.0.0`, `eth-abi>=4.0.0`
- Mythril requires: `eth-typing<3.0.0`, `eth-abi<4.0.0`

**Solution:** Separate virtual environments

```
/opt/venv-main          # Slither, solc-select, and general tools
/opt/venv-mythril       # Mythril isolated environment
```

### 4. Wrapper Scripts

Mythril uses a bash wrapper script to activate its dedicated venv:

```bash
#!/bin/bash
. /opt/venv-mythril/bin/activate
exec python -m mythril.interfaces.cli "$@"
```

---

## Installed Tools (All Working ✅)

### Foundry Suite
- **forge** v1.5.1-nightly - Smart contract compilation and testing
- **cast** v1.5.1-nightly - Ethereum RPC interaction tool
- **anvil** v1.5.1-nightly - Local Ethereum node

### Solidity
- **solc** v0.8.24 - Solidity compiler (managed by solc-select)
- **solc-select** - Version manager for solc

### Security Analysis
- **Slither** v0.10.2 - Static analyzer (from main venv)
- **Mythril** v0.24.8 - Symbolic execution (from dedicated venv) ✅ **FIXED**
- **Aderyn** v0.6.5 - Cyfrin security scanner
- **Echidna** v2.2.5 - Fuzzing tool

---

## File Structure

```
yudai-swe-agent/
├── .python-version              # Python 3.12 version pin
├── uv.lock                      # uv lockfile for dependencies
├── pyproject.toml               # Python project configuration
├── docker/
│   ├── Dockerfile.yudai         # Original (Mythril broken)
│   ├── Dockerfile.yudai.test    # Test version (Mythril broken)
│   └── Dockerfile.yudai.fixed   # ✅ FINAL - All tools working
├── test-docker-tools.sh         # Basic test script
├── test-docker-complete.sh      # ✅ Comprehensive test with uv
├── TEST_RESULTS.md              # Initial test results
└── DOCKER_ENV_SETUP.md          # This file
```

---

## Build Instructions

### Quick Start

```bash
# Build the Docker image
docker build -t yudai-complete -f docker/Dockerfile.yudai.fixed .

# Test all tools
./test-docker-complete.sh
```

### Build Arguments

```bash
docker build -t yudai-complete \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg SLITHER_VERSION=0.10.2 \
  --build-arg MYTHRIL_VERSION=0.24.8 \
  --build-arg SOLC_VERSION=0.8.24 \
  --build-arg ECHIDNA_VERSION=2.2.5 \
  -f docker/Dockerfile.yudai.fixed .
```

---

## Usage Examples

### Running Security Analysis

```bash
# Run Slither on a Solidity file
docker run --rm -v "$(pwd)/contracts:/workspace" yudai-complete \
  bash -lc ". /opt/venv-main/bin/activate && slither /workspace/MyContract.sol"

# Run Mythril on a contract
docker run --rm -v "$(pwd)/contracts:/workspace" yudai-complete \
  bash -lc "myth analyze /workspace/MyContract.sol"

# Run Aderyn on a project
docker run --rm -v "$(pwd):/workspace" yudai-complete \
  bash -lc "cd /workspace && aderyn ."

# Run Echidna fuzzer
docker run --rm -v "$(pwd)/contracts:/workspace" yudai-complete \
  bash -lc "echidna /workspace/MyContract.sol --contract MyContract"
```

### Foundry Workflow

```bash
# Compile contracts with Forge
docker run --rm -v "$(pwd):/workspace" yudai-complete \
  bash -lc "cd /workspace && forge build"

# Run tests
docker run --rm -v "$(pwd):/workspace" yudai-complete \
  bash -lc "cd /workspace && forge test -vv"

# Deploy to local Anvil
docker run --rm -p 8545:8545 yudai-complete \
  bash -lc "anvil --host 0.0.0.0"
```

### Interactive Shell

```bash
# Enter the container interactively
docker run --rm -it -v "$(pwd):/workspace" yudai-complete bash

# Inside the container:
# Activate main venv for most tools
source /opt/venv-main/bin/activate

# Or activate Mythril venv
source /opt/venv-mythril/bin/activate
```

---

## Local Development Setup

### Initialize uv Environment

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize uv for the project
cd yudai-swe-agent
uv sync

# Pin Python version
echo "3.12" > .python-version

# Lock dependencies
uv lock
```

### Install mini-swe-agent

```bash
# Install in development mode with full dependencies
uv pip install -e '.[full]'

# Or just the base package
uv pip install -e .
```

---

## Dockerfile Architecture

### Build Stages

1. **Base Image:** `ghcr.io/foundry-rs/foundry:latest` (includes Foundry tools)
2. **System Dependencies:** Python 3.12, build tools, gpg (for PPA)
3. **uv Installation:** Latest uv from astral.sh
4. **Main Venv:** Slither, solc-select using uv
5. **Mythril Venv:** Isolated Mythril installation using uv
6. **Native Tools:** Aderyn (Rust), Echidna (Haskell binary)
7. **Verification:** All tools tested during build

### Environment Variables

```dockerfile
ENV VENV_MAIN=/opt/venv-main           # Main virtual environment
ENV VENV_MYTHRIL=/opt/venv-mythril     # Mythril virtual environment
ENV UV_PYTHON=3.12                      # uv Python version
ENV PATH="${VENV_MAIN}/bin:/root/.solc-select:/root/.cargo/bin:${PATH}"
```

---

## Troubleshooting

### Mythril Warnings

Mythril shows syntax warnings with Python 3.12 due to stricter regex handling:

```
SyntaxWarning: invalid escape sequence '\s'
SyntaxWarning: invalid escape sequence '\m'
```

**Status:** ⚠️ Warnings only - functionality is not affected
**Fix:** These are upstream issues in Mythril dependencies, safe to ignore

### Solc Version Mismatch

If you see solc version different from expected:

```bash
# Always activate venv before using solc
docker run --rm yudai-complete bash -lc \
  ". /opt/venv-main/bin/activate && solc --version"
```

### Virtual Environment Not Activated

If tools are not found:

```bash
# Ensure you source the correct venv
source /opt/venv-main/bin/activate     # For Slither, solc-select
source /opt/venv-mythril/bin/activate  # For Mythril manual use
```

---

## Performance Notes

### Build Time
- First build: ~5-8 minutes (downloading dependencies)
- Cached rebuild: ~30-60 seconds (layer caching)

### Image Size
- Final image: ~3.5 GB
- Breakdown:
  - Base Foundry: ~1.5 GB
  - Python + dependencies: ~1.2 GB
  - Native tools (Aderyn, Echidna): ~800 MB

### Optimization Tips

```dockerfile
# Use Docker BuildKit for better caching
DOCKER_BUILDKIT=1 docker build ...

# Multi-platform build (optional)
docker buildx build --platform linux/amd64,linux/arm64 ...
```

---

## Testing

### Quick Test

```bash
./test-docker-complete.sh
```

### Manual Verification

```bash
# Check all tools
docker run --rm yudai-complete bash -lc "
  forge --version &&
  . /opt/venv-main/bin/activate && slither --version &&
  myth version &&
  aderyn --version &&
  echidna --version
"
```

---

## Future Improvements

### Planned Enhancements

1. **Multi-stage build:** Reduce final image size
2. **Mythril upgrade:** Use newer version compatible with modern eth-* packages
3. **CI/CD integration:** Automated testing in GitHub Actions
4. **Docker Compose:** Pre-configured setup with Anvil + Postgres + Redis
5. **VS Code devcontainer:** Integration for local development

### Monitoring

Track these for updates:
- [ ] Mythril releases (for eth-typing compatibility)
- [ ] Foundry updates (currently using nightly)
- [ ] Slither releases
- [ ] uv updates

---

## Security Considerations

### Sandboxing

All security analysis runs in isolated Docker containers:
- No access to host network by default
- Volume mounts are read-only where possible
- Run as root inside container (isolated from host)

### Trusted Sources

All tools installed from official sources:
- Foundry: ghcr.io/foundry-rs/foundry
- Python: deadsnakes PPA (official Ubuntu source)
- uv: astral.sh official installer
- Aderyn: GitHub releases (Cyfrin official)
- Echidna: GitHub releases (Trail of Bits official)
- Slither, Mythril: PyPI official packages

---

## References

- **uv Documentation:** https://docs.astral.sh/uv/
- **Foundry Book:** https://book.getfoundry.sh
- **Slither:** https://github.com/crytic/slither
- **Mythril:** https://github.com/Consensys/mythril
- **Aderyn:** https://github.com/Cyfrin/aderyn
- **Echidna:** https://github.com/crytic/echidna
- **Mini SWE Agent:** https://github.com/SWE-agent/mini-SWE-agent

---

## Support

For issues or questions:
1. Check test scripts: `./test-docker-complete.sh`
2. Review logs: `docker logs <container-id>`
3. Inspect image: `docker run -it yudai-complete bash`
4. Rebuild: `docker build --no-cache -f docker/Dockerfile.yudai.fixed .`

---

**Last Updated:** 2026-01-06
**Maintainer:** Yudai Team
**Docker Image:** `yudai-complete`
**Status:** ✅ Production Ready

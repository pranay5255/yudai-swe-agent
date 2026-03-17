# Docker Build Optimization Guide

## Current Build Time: ~12-20 minutes

### Time Breakdown (Full Build)
1. **Base image pull**: 1-2 min (if not cached)
2. **System dependencies**: 1-2 min
3. **Slither installation**: 2-3 min
4. **Mythril installation**: 5-10 min ⚠️ **SLOWEST**
5. **6x solc versions**: 2-3 min
6. **Aderyn + Echidna**: 1-2 min

## Quick Diagnosis

### Option 1: Build with Progress Tracking
```bash
./docker/build-with-progress.sh
```
This shows timestamps for each step so you can see where time is spent.

### Option 2: Use Fast Dev Build (3-5 minutes)
```bash
docker build -t yudai-base:fast -f docker/Dockerfile.base-fast .
```
**Skips**: Mythril, Aderyn, extra solc versions (keeps only 0.8.24)
**Good for**: Quick iteration during development

### Option 3: Check Current Progress
```bash
# In another terminal while building:
docker ps -a | head -5
docker logs -f <container_id>
```

## Optimization Strategies

### 1. Use BuildKit Cache Mounts (Future Improvement)
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install mythril
```

### 2. Multi-Stage Build (Future Improvement)
Build tools in parallel stages, then combine.

### 3. Pre-built Base Images
Consider publishing pre-built images to Docker Hub/GHCR for CI/CD.

### 4. Skip Verification Step During Dev
Comment out lines 103-115 in Dockerfile.base (tool verification).

### 5. Reduce solc Versions
If you only need specific versions, reduce the 6 solc installs to 2-3.

## Why Mythril Is So Slow

Mythril has ~150+ dependencies including:
- z3-solver (symbolic execution engine)
- ethereum libraries
- Various crypto libraries
- py-evm (full Ethereum implementation)

**Solution**: Use the fast dev build if you don't need Mythril immediately.

## Caching Tips

1. **Don't change Dockerfile order** - Docker caches by layer
2. **Use `--build-arg` for versions** - Allows cache reuse
3. **Separate RUN commands** - More granular caching
4. **Pin versions** - Already done for reproducibility

## Quick Commands

```bash
# Full build with timing
./docker/build-with-progress.sh

# Fast dev build
docker build -t yudai-base:fast -f docker/Dockerfile.base-fast .

# Standard build (use cached layers)
docker build -t yudai-base:latest -f docker/Dockerfile.base .

# Force rebuild from scratch
docker build --no-cache -t yudai-base:latest -f docker/Dockerfile.base .

# Check layer sizes
docker history yudai-base:latest
```

## Expected First Build Times

- **With good internet**: 12-15 minutes
- **With slow internet**: 15-20 minutes
- **Subsequent builds** (with cache): 2-5 minutes
- **Fast dev build**: 3-5 minutes

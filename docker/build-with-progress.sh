#!/usr/bin/env bash
# Build Docker image with detailed progress monitoring

set -e

echo "=========================================="
echo "Building yudai-base with progress tracking"
echo "=========================================="
echo ""
echo "Expected build time breakdown:"
echo "  - System dependencies: 1-2 min"
echo "  - Slither installation: 2-3 min"
echo "  - Mythril installation: 5-10 min (SLOWEST)"
echo "  - Solc versions: 2-3 min"
echo "  - Aderyn + Echidna: 1-2 min"
echo "  - Total: ~12-20 minutes"
echo ""
echo "Watch for timestamps like [HH:MM:SS] in the output below"
echo "=========================================="
echo ""

# Use BuildKit for better progress display
export DOCKER_BUILDKIT=1

# Build with progress=plain to see all output
docker build \
  --progress=plain \
  --no-cache \
  -t yudai-base:latest \
  -f docker/Dockerfile.base \
  .

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="

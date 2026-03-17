#!/usr/bin/env bash
# Clean Docker cache and rebuild images

set -e

echo "=========================================="
echo "Docker Cleanup and Rebuild Script"
echo "=========================================="
echo ""

# Step 1: Stop any running containers using these images
echo "[1/6] Stopping containers using yudai images..."
docker ps -a | grep yudai | awk '{print $1}' | xargs -r docker stop || true
docker ps -a | grep yudai | awk '{print $1}' | xargs -r docker rm || true
echo "✓ Containers stopped and removed"
echo ""

# Step 2: Remove existing yudai images
echo "[2/6] Removing existing yudai images..."
docker images | grep yudai | awk '{print $3}' | xargs -r docker rmi -f || true
echo "✓ Yudai images removed"
echo ""

# Step 3: Prune all Docker build cache
echo "[3/6] Pruning Docker build cache..."
docker builder prune -a -f
echo "✓ Build cache cleared"
echo ""

# Step 4: Prune system (dangling images, stopped containers, unused networks)
echo "[4/6] Pruning Docker system..."
docker system prune -f
echo "✓ System pruned"
echo ""

# Step 5: Build FAST version (3-5 minutes)
echo "[5/6] Building FAST image (no Mythril, 3-5 min)..."
echo "Started at: $(date +%T)"
docker build \
  --no-cache \
  --progress=plain \
  -t yudai-base:fast \
  -f docker/Dockerfile.base-fast \
  .
echo "✓ Fast image built at: $(date +%T)"
echo ""

# Step 6: Build FULL version (12-20 minutes)
echo "[6/6] Building FULL image (with Mythril, 12-20 min)..."
echo "Started at: $(date +%T)"
docker build \
  --no-cache \
  --progress=plain \
  -t yudai-base:latest \
  -f docker/Dockerfile.base \
  .
echo "✓ Full image built at: $(date +%T)"
echo ""

echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""
echo "Images created:"
docker images | grep yudai
echo ""
echo "Disk usage:"
docker system df

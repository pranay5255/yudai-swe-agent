#!/usr/bin/env bash
# =============================================================================
# BUILD ALL DOCKER IMAGES
# =============================================================================
# This script builds the complete Docker image hierarchy:
# 1. Base image (parent)
# 2. Template images (children)
#
# Usage:
#   ./docker/build-all.sh              # Build all images
#   ./docker/build-all.sh --base-only  # Build only base image
#   ./docker/build-all.sh --push       # Build and push to registry
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"
REGISTRY=""  # Set this if you want to push to a registry (e.g., "ghcr.io/username")
VERSION="latest"

# Parse arguments
BASE_ONLY=false
PUSH=false
NO_CACHE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --base-only)
            BASE_ONLY=true
            shift
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

build_image() {
    local name=$1
    local dockerfile=$2
    local tag=$3
    local build_args=$4

    print_info "Building ${name}..."

    local cache_flag=""
    if [ "$NO_CACHE" = true ]; then
        cache_flag="--no-cache"
    fi

    if docker build \
        -t "${tag}" \
        -f "${dockerfile}" \
        ${cache_flag} \
        ${build_args} \
        "${PROJECT_ROOT}"; then
        print_success "Built ${name}: ${tag}"
        return 0
    else
        print_error "Failed to build ${name}"
        return 1
    fi
}

push_image() {
    local tag=$1
    print_info "Pushing ${tag}..."
    if docker push "${tag}"; then
        print_success "Pushed ${tag}"
    else
        print_error "Failed to push ${tag}"
    fi
}

# Main build process
main() {
    print_header "Building Yudai Docker Image Hierarchy"

    echo "Configuration:"
    echo "  Project Root: ${PROJECT_ROOT}"
    echo "  Docker Dir: ${DOCKER_DIR}"
    echo "  Registry: ${REGISTRY:-"(local only)"}"
    echo "  Version: ${VERSION}"
    echo "  Base Only: ${BASE_ONLY}"
    echo "  Push: ${PUSH}"
    echo "  No Cache: ${NO_CACHE}"
    echo ""

    cd "${PROJECT_ROOT}"

    # Step 1: Build base image
    print_header "Step 1: Building Base Image"

    local base_tag="yudai-base:${VERSION}"
    if [ -n "$REGISTRY" ]; then
        base_tag="${REGISTRY}/yudai-base:${VERSION}"
    fi

    if ! build_image \
        "Base Image" \
        "${DOCKER_DIR}/Dockerfile.base" \
        "${base_tag}"; then
        print_error "Base image build failed. Aborting."
        exit 1
    fi

    # Tag as latest too
    docker tag "${base_tag}" "yudai-base:latest"
    print_success "Tagged as yudai-base:latest"

    if [ "$PUSH" = true ]; then
        push_image "${base_tag}"
        if [ -n "$REGISTRY" ]; then
            push_image "${REGISTRY}/yudai-base:latest"
        fi
    fi

    if [ "$BASE_ONLY" = true ]; then
        print_header "Build Complete (Base Only)"
        echo "Base image: ${base_tag}"
        exit 0
    fi

    # Step 2: Build template images
    print_header "Step 2: Building Template Images"

    # Define templates
    declare -A templates=(
        ["sol-0.4-standalone"]="${DOCKER_DIR}/templates/Dockerfile.sol-0.4-standalone"
        ["sol-0.8-standalone"]="${DOCKER_DIR}/templates/Dockerfile.sol-0.8-standalone"
        ["sol-0.8-oz-v4"]="${DOCKER_DIR}/templates/Dockerfile.sol-0.8-oz-v4"
        ["sol-0.8-oz-v5"]="${DOCKER_DIR}/templates/Dockerfile.sol-0.8-oz-v5"
    )

    local failed=0
    local built=0

    for template_name in "${!templates[@]}"; do
        local dockerfile="${templates[$template_name]}"
        local tag="yudai-${template_name}:${VERSION}"

        if [ -n "$REGISTRY" ]; then
            tag="${REGISTRY}/yudai-${template_name}:${VERSION}"
        fi

        if build_image \
            "Template: ${template_name}" \
            "${dockerfile}" \
            "${tag}"; then
            # Tag as latest
            docker tag "${tag}" "yudai-${template_name}:latest"
            print_success "Tagged as yudai-${template_name}:latest"

            if [ "$PUSH" = true ]; then
                push_image "${tag}"
                if [ -n "$REGISTRY" ]; then
                    push_image "${REGISTRY}/yudai-${template_name}:latest"
                fi
            fi

            built=$((built + 1))
        else
            failed=$((failed + 1))
        fi
    done

    # Summary
    print_header "Build Summary"

    echo "Results:"
    echo "  Base Image: ✓ yudai-base:${VERSION}"
    echo "  Templates Built: ${built}"
    echo "  Templates Failed: ${failed}"
    echo ""

    if [ ${failed} -gt 0 ]; then
        print_error "${failed} image(s) failed to build"
        exit 1
    else
        print_success "All images built successfully!"
    fi

    echo ""
    echo "Available images:"
    docker images | grep "yudai-" | head -10

    echo ""
    echo "To use these images in episodes:"
    echo "  python scripts/run_minimal_episode.py --image yudai-sol-0.8:latest"
}

main "$@"

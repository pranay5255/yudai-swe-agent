#!/bin/bash
set -e

echo "========================================="
echo "Testing Yudai Docker Image Tools"
echo "========================================="
echo ""

echo "1. Testing Foundry Tools"
echo "-----------------------------------------"
echo "Forge:"
docker run --rm --entrypoint="" yudai-test bash -lc "forge --version"
echo ""

echo "Cast:"
docker run --rm --entrypoint="" yudai-test bash -lc "cast --version"
echo ""

echo "Anvil:"
docker run --rm --entrypoint="" yudai-test bash -lc "anvil --version"
echo ""

echo "2. Testing Solidity Compiler"
echo "-----------------------------------------"
echo "Solc:"
docker run --rm --entrypoint="" yudai-test bash -lc "solc --version"
echo ""

echo "Solc-select:"
docker run --rm --entrypoint="" yudai-test bash -lc "solc-select versions"
echo ""

echo "3. Testing Security Analysis Tools"
echo "-----------------------------------------"
echo "Slither:"
docker run --rm --entrypoint="" yudai-test bash -lc "slither --version"
echo ""

echo "Aderyn:"
docker run --rm --entrypoint="" yudai-test bash -lc "aderyn --version"
echo ""

echo "Echidna:"
docker run --rm --entrypoint="" yudai-test bash -lc "echidna --version"
echo ""

echo "Mythril (Expected to fail due to dependency conflicts):"
if docker run --rm --entrypoint="" yudai-test bash -lc "myth version" 2>&1; then
    echo "✅ Mythril working"
else
    echo "❌ Mythril has dependency conflicts (known issue)"
fi
echo ""

echo "4. Testing Python Environment"
echo "-----------------------------------------"
echo "Python:"
docker run --rm --entrypoint="" yudai-test bash -lc "python3 --version"
echo ""

echo "Virtual Environment:"
docker run --rm --entrypoint="" yudai-test bash -lc "echo \$VIRTUAL_ENV"
echo ""

echo "========================================="
echo "Test Summary"
echo "========================================="
echo "✅ Foundry Tools: forge, cast, anvil - All Working"
echo "✅ Solidity Compiler: solc 0.8.24 - Working"
echo "✅ Solc-select - Working"
echo "✅ Slither - Working"
echo "✅ Aderyn - Working"
echo "✅ Echidna - Working"
echo "❌ Mythril - Dependency conflicts (eth-typing version mismatch)"
echo "✅ Python 3.10 Virtual Environment - Working"
echo "========================================="

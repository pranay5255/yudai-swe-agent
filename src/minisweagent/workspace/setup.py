"""Workspace setup for different blockchain development modes.

This module provides workspace initialization for three distinct use cases:
1. Cast Explorer - Read-only blockchain queries (minimal workspace)
2. Transaction Analyzer - Transaction replay and tracing (minimal + anvil scripts)
3. Contract Development - Full Foundry project with OZ + Uniswap V4

Each mode creates a temp directory with appropriate structure and dependencies.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from enum import Enum
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)


class WorkspaceMode(str, Enum):
    """Workspace initialization modes."""

    CAST_EXPLORER = "cast_explorer"
    TX_ANALYZER = "tx_analyzer"
    CONTRACT_DEV = "contract_dev"
    MINIMAL = "minimal"  # Just forge-std


class WorkspaceInfo(NamedTuple):
    """Information about a created workspace."""

    path: Path
    mode: WorkspaceMode
    has_openzeppelin: bool
    has_uniswap_v4: bool
    has_forge_std: bool


# =============================================================================
# FOUNDRY.TOML TEMPLATES
# =============================================================================

FOUNDRY_TOML_MINIMAL = """\
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
evm_version = "cancun"
auto_detect_solc = true
optimizer = true
optimizer_runs = 200
gas_reports = ["*"]

[rpc_endpoints]
mainnet = "${ETH_RPC_URL}"
bsc = "${BSC_RPC_URL}"
base = "${BASE_RPC_URL}"
arbitrum = "${ARBITRUM_RPC_URL}"
local = "http://127.0.0.1:8545"

[etherscan]
mainnet = { key = "${ETHERSCAN_API_KEY}" }
bsc = { key = "${BSCSCAN_API_KEY}" }
base = { key = "${BASESCAN_API_KEY}" }
"""

FOUNDRY_TOML_FULL = """\
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
evm_version = "cancun"
auto_detect_solc = true
optimizer = true
optimizer_runs = 200
gas_reports = ["*"]
via_ir = false
ffi = true

# Remappings for installed libraries
remappings = [
    "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
    "@openzeppelin/contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/contracts/",
    "@uniswap/v4-core/=lib/v4-core/",
    "@uniswap/v4-periphery/=lib/v4-periphery/",
    "forge-std/=lib/forge-std/src/",
]

[rpc_endpoints]
mainnet = "${ETH_RPC_URL}"
bsc = "${BSC_RPC_URL}"
base = "${BASE_RPC_URL}"
arbitrum = "${ARBITRUM_RPC_URL}"
local = "http://127.0.0.1:8545"

[etherscan]
mainnet = { key = "${ETHERSCAN_API_KEY}" }
bsc = { key = "${BSCSCAN_API_KEY}" }
base = { key = "${BASESCAN_API_KEY}" }

[fmt]
line_length = 100
tab_width = 4
bracket_spacing = true
"""


# =============================================================================
# HELPER SCRIPTS
# =============================================================================

ANVIL_FORK_SCRIPT = """\
#!/bin/bash
# Fork mainnet at a specific block for transaction analysis
# Usage: ./scripts/fork.sh [BLOCK_NUMBER] [RPC_URL]

BLOCK=${1:-"latest"}
RPC=${2:-"$ETH_RPC_URL"}

if [ -z "$RPC" ]; then
    echo "Error: RPC_URL not set. Provide as argument or set ETH_RPC_URL"
    exit 1
fi

echo "Starting anvil fork at block $BLOCK..."
if [ "$BLOCK" = "latest" ]; then
    anvil --fork-url "$RPC" --host 0.0.0.0 --port 8545
else
    anvil --fork-url "$RPC" --fork-block-number "$BLOCK" --host 0.0.0.0 --port 8545
fi
"""

TX_REPLAY_SCRIPT = """\
#!/bin/bash
# Replay a transaction with full trace
# Usage: ./scripts/replay_tx.sh <TX_HASH> [RPC_URL]

TX_HASH=$1
RPC=${2:-"$ETH_RPC_URL"}

if [ -z "$TX_HASH" ]; then
    echo "Usage: ./scripts/replay_tx.sh <TX_HASH> [RPC_URL]"
    exit 1
fi

if [ -z "$RPC" ]; then
    echo "Error: RPC_URL not set. Provide as argument or set ETH_RPC_URL"
    exit 1
fi

echo "=== Transaction Details ==="
cast tx "$TX_HASH" --rpc-url "$RPC"

echo ""
echo "=== Receipt ==="
cast receipt "$TX_HASH" --rpc-url "$RPC"

echo ""
echo "=== Execution Trace ==="
cast run "$TX_HASH" --rpc-url "$RPC"
"""


# =============================================================================
# SAMPLE CONTRACTS
# =============================================================================

SAMPLE_CONTRACT = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title SampleContract
 * @notice A minimal example demonstrating OpenZeppelin integration
 * @dev Delete this and create your own contracts
 */
contract SampleContract is Ownable, ReentrancyGuard {
    mapping(address => uint256) public balances;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);

    constructor() Ownable(msg.sender) {}

    function deposit() external payable nonReentrant {
        balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        balances[msg.sender] -= amount;

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        emit Withdrawn(msg.sender, amount);
    }

    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }
}
"""

SAMPLE_TEST = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SampleContract.sol";

contract SampleContractTest is Test {
    SampleContract public sample;
    address public user = address(0x1);

    function setUp() public {
        sample = new SampleContract();
        vm.deal(user, 10 ether);
    }

    function test_Deposit() public {
        vm.prank(user);
        sample.deposit{value: 1 ether}();

        assertEq(sample.getBalance(user), 1 ether);
    }

    function test_Withdraw() public {
        vm.startPrank(user);
        sample.deposit{value: 1 ether}();
        sample.withdraw(0.5 ether);
        vm.stopPrank();

        assertEq(sample.getBalance(user), 0.5 ether);
        assertEq(user.balance, 9.5 ether);
    }

    function test_RevertWhen_WithdrawInsufficientBalance() public {
        vm.prank(user);
        vm.expectRevert("Insufficient balance");
        sample.withdraw(1 ether);
    }

    function testFuzz_DepositWithdraw(uint96 amount) public {
        vm.assume(amount > 0 && amount <= 10 ether);

        vm.startPrank(user);
        sample.deposit{value: amount}();
        sample.withdraw(amount);
        vm.stopPrank();

        assertEq(sample.getBalance(user), 0);
    }
}
"""

SAMPLE_DEPLOY_SCRIPT = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/SampleContract.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);

        SampleContract sample = new SampleContract();
        console2.log("SampleContract deployed at:", address(sample));

        vm.stopBroadcast();
    }
}
"""


# =============================================================================
# WORKSPACE SETUP FUNCTIONS
# =============================================================================


def _run_command(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    """Run a command and return (returncode, output)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, str(e)


def _install_forge_std(workspace: Path) -> bool:
    """Install forge-std library."""
    lib_dir = workspace / "lib"
    lib_dir.mkdir(exist_ok=True)

    # Try forge install first
    code, output = _run_command(
        ["forge", "install", "foundry-rs/forge-std", "--no-commit"],
        workspace,
        timeout=60,
    )

    if code == 0:
        logger.info("Installed forge-std via forge install")
        return True

    # Fallback: create minimal stubs
    logger.warning(f"forge install failed: {output}. Creating minimal stubs.")
    return _create_forge_std_stubs(lib_dir / "forge-std")


def _create_forge_std_stubs(forge_std_dir: Path) -> bool:
    """Create minimal forge-std stubs when git install fails."""
    src_dir = forge_std_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Minimal Test.sol
    (src_dir / "Test.sol").write_text("""\
// SPDX-License-Identifier: MIT
pragma solidity >=0.6.2 <0.9.0;

import "./Vm.sol";
import "./console2.sol";

abstract contract Test {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function assertTrue(bool condition) internal pure {
        require(condition, "Assertion failed");
    }

    function assertEq(uint256 a, uint256 b) internal pure {
        require(a == b, "Values not equal");
    }

    function assertEq(address a, address b) internal pure {
        require(a == b, "Addresses not equal");
    }

    function assertEq(bytes32 a, bytes32 b) internal pure {
        require(a == b, "Bytes32 not equal");
    }
}
""")

    # Minimal Script.sol
    (src_dir / "Script.sol").write_text("""\
// SPDX-License-Identifier: MIT
pragma solidity >=0.6.2 <0.9.0;

import "./Vm.sol";
import "./console2.sol";

abstract contract Script {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
}
""")

    # Minimal Vm.sol interface
    (src_dir / "Vm.sol").write_text("""\
// SPDX-License-Identifier: MIT
pragma solidity >=0.6.2 <0.9.0;

interface Vm {
    function startBroadcast() external;
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
    function prank(address msgSender) external;
    function startPrank(address msgSender) external;
    function stopPrank() external;
    function deal(address account, uint256 newBalance) external;
    function expectRevert(bytes calldata revertData) external;
    function expectRevert(bytes4 revertData) external;
    function assume(bool condition) external pure;
    function envUint(string calldata name) external view returns (uint256);
    function envAddress(string calldata name) external view returns (address);
    function envString(string calldata name) external view returns (string memory);
}
""")

    # Minimal console2.sol
    (src_dir / "console2.sol").write_text("""\
// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

library console2 {
    address constant CONSOLE_ADDRESS = 0x000000000000000000636F6e736F6c652e6c6f67;

    function log(string memory p0) internal view {
        (bool ignored,) = CONSOLE_ADDRESS.staticcall(abi.encodeWithSignature("log(string)", p0));
        ignored;
    }

    function log(string memory p0, uint256 p1) internal view {
        (bool ignored,) = CONSOLE_ADDRESS.staticcall(abi.encodeWithSignature("log(string,uint256)", p0, p1));
        ignored;
    }

    function log(string memory p0, address p1) internal view {
        (bool ignored,) = CONSOLE_ADDRESS.staticcall(abi.encodeWithSignature("log(string,address)", p0, p1));
        ignored;
    }
}
""")

    return True


def _install_openzeppelin(workspace: Path) -> bool:
    """Install OpenZeppelin contracts."""
    code, output = _run_command(
        ["forge", "install", "OpenZeppelin/openzeppelin-contracts", "--no-commit"],
        workspace,
        timeout=120,
    )
    if code != 0:
        logger.warning(f"Failed to install OpenZeppelin: {output}")
        return False
    logger.info("Installed OpenZeppelin contracts")
    return True


def _install_uniswap_v4(workspace: Path) -> bool:
    """Install Uniswap V4 core and periphery."""
    success = True

    # V4 Core
    code, output = _run_command(
        ["forge", "install", "Uniswap/v4-core", "--no-commit"],
        workspace,
        timeout=120,
    )
    if code != 0:
        logger.warning(f"Failed to install v4-core: {output}")
        success = False
    else:
        logger.info("Installed Uniswap v4-core")

    # V4 Periphery
    code, output = _run_command(
        ["forge", "install", "Uniswap/v4-periphery", "--no-commit"],
        workspace,
        timeout=120,
    )
    if code != 0:
        logger.warning(f"Failed to install v4-periphery: {output}")
        success = False
    else:
        logger.info("Installed Uniswap v4-periphery")

    return success


def setup_cast_explorer_workspace(
    workspace: Path | None = None,
    prefix: str = "cast_explorer_",
) -> WorkspaceInfo:
    """Create minimal workspace for cast read-only queries.

    This creates the bare minimum needed for cast commands to work.
    No contracts, no dependencies - just the directory structure.
    """
    if workspace is None:
        workspace = Path(tempfile.mkdtemp(prefix=prefix))
    else:
        workspace.mkdir(parents=True, exist_ok=True)

    # Minimal structure
    (workspace / "scripts").mkdir(exist_ok=True)

    # Write foundry.toml (needed for some cast commands)
    (workspace / "foundry.toml").write_text(FOUNDRY_TOML_MINIMAL)

    logger.info(f"Created cast_explorer workspace at {workspace}")

    return WorkspaceInfo(
        path=workspace,
        mode=WorkspaceMode.CAST_EXPLORER,
        has_openzeppelin=False,
        has_uniswap_v4=False,
        has_forge_std=False,
    )


def setup_tx_analyzer_workspace(
    workspace: Path | None = None,
    prefix: str = "tx_analyzer_",
) -> WorkspaceInfo:
    """Create workspace for transaction analysis and replay.

    Includes helper scripts for forking and transaction replay.
    """
    if workspace is None:
        workspace = Path(tempfile.mkdtemp(prefix=prefix))
    else:
        workspace.mkdir(parents=True, exist_ok=True)

    # Create structure
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "scripts").mkdir(exist_ok=True)

    # Write configs
    (workspace / "foundry.toml").write_text(FOUNDRY_TOML_MINIMAL)

    # Write helper scripts
    fork_script = workspace / "scripts" / "fork.sh"
    fork_script.write_text(ANVIL_FORK_SCRIPT)
    fork_script.chmod(0o755)

    replay_script = workspace / "scripts" / "replay_tx.sh"
    replay_script.write_text(TX_REPLAY_SCRIPT)
    replay_script.chmod(0o755)

    # Install forge-std for potential script usage
    has_forge_std = _install_forge_std(workspace)

    logger.info(f"Created tx_analyzer workspace at {workspace}")

    return WorkspaceInfo(
        path=workspace,
        mode=WorkspaceMode.TX_ANALYZER,
        has_openzeppelin=False,
        has_uniswap_v4=False,
        has_forge_std=has_forge_std,
    )


def setup_contract_dev_workspace(
    workspace: Path | None = None,
    prefix: str = "contract_dev_",
    include_samples: bool = True,
) -> WorkspaceInfo:
    """Create full Foundry project with OpenZeppelin and Uniswap V4.

    This is the most complete workspace setup, suitable for building
    new contracts from scratch with access to battle-tested libraries.
    """
    if workspace is None:
        workspace = Path(tempfile.mkdtemp(prefix=prefix))
    else:
        workspace.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "test").mkdir(exist_ok=True)
    (workspace / "script").mkdir(exist_ok=True)
    (workspace / "lib").mkdir(exist_ok=True)

    # Write full foundry.toml
    (workspace / "foundry.toml").write_text(FOUNDRY_TOML_FULL)

    # Install dependencies
    has_forge_std = _install_forge_std(workspace)
    has_openzeppelin = _install_openzeppelin(workspace)
    has_uniswap_v4 = _install_uniswap_v4(workspace)

    # Write sample contracts if requested
    if include_samples:
        (workspace / "src" / "SampleContract.sol").write_text(SAMPLE_CONTRACT)
        (workspace / "test" / "SampleContract.t.sol").write_text(SAMPLE_TEST)
        (workspace / "script" / "Deploy.s.sol").write_text(SAMPLE_DEPLOY_SCRIPT)

    # Create .gitignore
    (workspace / ".gitignore").write_text("""\
# Compiler files
cache/
out/

# Environment
.env
.env.local

# IDE
.idea/
.vscode/

# OS
.DS_Store
""")

    # Try to build to verify setup
    code, output = _run_command(["forge", "build"], workspace, timeout=180)
    if code != 0:
        logger.warning(f"Initial build failed: {output}")
    else:
        logger.info("Workspace built successfully")

    logger.info(f"Created contract_dev workspace at {workspace}")

    return WorkspaceInfo(
        path=workspace,
        mode=WorkspaceMode.CONTRACT_DEV,
        has_openzeppelin=has_openzeppelin,
        has_uniswap_v4=has_uniswap_v4,
        has_forge_std=has_forge_std,
    )


def create_workspace(
    mode: WorkspaceMode | str,
    workspace: Path | None = None,
    **kwargs,
) -> WorkspaceInfo:
    """Create a workspace for the specified mode.

    Args:
        mode: The workspace mode (cast_explorer, tx_analyzer, contract_dev)
        workspace: Optional path for the workspace. If None, creates a temp dir.
        **kwargs: Additional arguments passed to the specific setup function.

    Returns:
        WorkspaceInfo with details about the created workspace.
    """
    if isinstance(mode, str):
        mode = WorkspaceMode(mode)

    setup_funcs = {
        WorkspaceMode.CAST_EXPLORER: setup_cast_explorer_workspace,
        WorkspaceMode.TX_ANALYZER: setup_tx_analyzer_workspace,
        WorkspaceMode.CONTRACT_DEV: setup_contract_dev_workspace,
        WorkspaceMode.MINIMAL: lambda w, **k: setup_tx_analyzer_workspace(w, prefix="minimal_"),
    }

    setup_func = setup_funcs.get(mode)
    if setup_func is None:
        raise ValueError(f"Unknown workspace mode: {mode}")

    return setup_func(workspace, **kwargs)


def cleanup_workspace(workspace: Path | WorkspaceInfo) -> None:
    """Remove a workspace directory."""
    if isinstance(workspace, WorkspaceInfo):
        workspace = workspace.path

    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
        logger.info(f"Cleaned up workspace at {workspace}")

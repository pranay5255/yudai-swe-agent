"""Foundry development environment for smart contract development and security analysis.

This environment extends DockerEnvironment with Foundry-specific features:
- Pre-configured with Foundry tools (forge, cast, anvil, chisel)
- Security analysis tools (slither, aderyn, mythril, echidna)
- Volume mounting for host Foundry projects
- Environment variable forwarding for RPC URLs and API keys
- Longer timeouts suitable for contract compilation and analysis
"""

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from minisweagent.environments.docker import DockerEnvironment


class FoundryEnvironmentConfig(BaseModel):
    """Configuration for Foundry development environment."""

    # Docker image settings
    image: str = "yudai/foundry-full:latest"
    """Docker image with Foundry + security tools. Build with docker/Dockerfile.yudai."""

    cwd: str = "/workspace"
    """Working directory inside the container."""

    timeout: int = 120
    """Command timeout in seconds. Longer than default for compilation."""

    container_timeout: str = "4h"
    """How long to keep container alive. Smart contract sessions can be long."""

    # Volume mounting
    project_path: str = ""
    """Host path to Foundry project. Will be mounted at mount_target."""

    mount_target: str = "/workspace"
    """Container path where project_path will be mounted."""

    # Environment variables
    forward_env: list[str] = Field(
        default_factory=lambda: [
            "ETH_RPC_URL",
            "ETHERSCAN_API_KEY",
            "PRIVATE_KEY",
            "ALCHEMY_API_KEY",
            "INFURA_API_KEY",
        ]
    )
    """Environment variables to forward from host to container."""

    env: dict[str, str] = Field(
        default_factory=lambda: {
            "FOUNDRY_PROFILE": "default",
            "FOUNDRY_DISABLE_NIGHTLY_WARNING": "1",
            "FORCE_COLOR": "1",
            "CI": "true",
            "PAGER": "cat",
            "MANPAGER": "cat",
        }
    )
    """Environment variables to set in the container."""

    # Anvil settings
    anvil_fork_url: str = ""
    """RPC URL to fork from when starting anvil. Empty means no fork."""

    anvil_port: int = 8545
    """Port for anvil to listen on."""

    anvil_startup_timeout: int = 60
    """Seconds to wait for Anvil RPC to become responsive."""

    # Security
    pull_timeout: int = 180
    """Timeout for pulling Docker image. Foundry image is ~1GB."""


class FoundryEnvironment(DockerEnvironment):
    """Docker environment specialized for Foundry smart contract development.

    Extends DockerEnvironment with:
    - Volume mounting for host Foundry projects
    - Pre-configured environment variables for web3 development
    - Longer timeouts suitable for contract compilation
    - Foundry-specific template variables

    Example:
        >>> env = FoundryEnvironment(project_path="/path/to/foundry/project")
        >>> result = env.execute("forge build")
        >>> print(result["output"])
    """

    def __init__(
        self,
        *,
        config_class: type = FoundryEnvironmentConfig,
        logger: logging.Logger | None = None,
        **kwargs,
    ):
        """Initialize Foundry environment.

        Args:
            config_class: Pydantic config class to use
            logger: Optional logger instance
            **kwargs: Config fields passed to config_class
        """
        self.logger = logger or logging.getLogger("minisweagent.environment.foundry")

        # Parse our config first to extract foundry-specific settings
        self._foundry_config = config_class(**kwargs)

        # Build Docker run_args with volume mount
        run_args = ["--rm"]
        if self._foundry_config.project_path:
            # Resolve to absolute path
            project_path = Path(self._foundry_config.project_path).resolve()
            if project_path.exists():
                run_args.extend(["-v", f"{project_path}:{self._foundry_config.mount_target}"])
                self.logger.info(f"Mounting {project_path} to {self._foundry_config.mount_target}")
            else:
                self.logger.warning(f"Project path does not exist: {project_path}")

        # Initialize parent DockerEnvironment with our config
        super().__init__(
            logger=self.logger,
            image=self._foundry_config.image,
            cwd=self._foundry_config.cwd,
            timeout=self._foundry_config.timeout,
            container_timeout=self._foundry_config.container_timeout,
            env=self._foundry_config.env,
            forward_env=self._foundry_config.forward_env,
            run_args=run_args,
            pull_timeout=self._foundry_config.pull_timeout,
        )

        self.logger.info("Foundry environment initialized")

    def get_template_vars(self) -> dict[str, Any]:
        """Return template variables including Foundry-specific ones.

        Returns:
            Dict with config values plus Foundry-specific variables:
            - foundry_available: Whether Foundry tools are available
            - project_mounted: Whether a project is mounted
            - anvil_fork_url: Fork URL if configured
        """
        base_vars = super().get_template_vars()
        return base_vars | {
            "foundry_available": True,
            "project_mounted": bool(self._foundry_config.project_path),
            "project_path": self._foundry_config.project_path,
            "anvil_fork_url": self._foundry_config.anvil_fork_url,
            "anvil_port": self._foundry_config.anvil_port,
        }

    def start_anvil(
        self,
        fork_url: str = "",
        block_number: int | None = None,
        startup_timeout: int | None = None,
    ) -> dict[str, Any]:
        """Start anvil local testnet in background.

        Args:
            fork_url: RPC URL to fork from. Uses config value if not provided.
            block_number: Block number to fork at. Latest if not provided.
            startup_timeout: Max seconds to wait for Anvil to be ready.
                            Uses config value if not provided. Historical forks may
                            need longer to initialize.

        Returns:
            Execute result dict with output and returncode

        Raises:
            RuntimeError: If anvil fails to start, with detailed error message
                         including archive RPC guidance for historical fork failures.
        """
        fork_url = fork_url or self._foundry_config.anvil_fork_url
        port = self._foundry_config.anvil_port
        timeout = (
            self._foundry_config.anvil_startup_timeout
            if startup_timeout is None
            else startup_timeout
        )

        cmd_parts = [f"anvil --port {port}"]
        if fork_url:
            cmd_parts.append(f"--fork-url {fork_url}")
            if block_number:
                cmd_parts.append(f"--fork-block-number {block_number}")

        # Start in background with nohup
        anvil_cmd = " ".join(cmd_parts)
        # Use disown to fully detach process from the shell session
        background_cmd = (
            f"nohup {anvil_cmd} > /tmp/anvil.log 2>&1 & "
            f"ANVIL_PID=$!; disown $ANVIL_PID; "
            f"echo \"Anvil PID: $ANVIL_PID\""
        )

        self.logger.info(f"Starting Anvil: {anvil_cmd}")
        result = self.execute(background_cmd)

        # Wait for Anvil to be ready by testing RPC connectivity
        anvil_status = self._wait_for_anvil_ready(fork_url, block_number, timeout=timeout)
        if not anvil_status["running"]:
            error_msg = anvil_status.get("error", "Unknown error")
            self.logger.error(f"Anvil failed to start: {error_msg}")
            raise RuntimeError(error_msg)

        self.logger.info(f"Anvil successfully started on port {port}")
        return result

    def _wait_for_anvil_ready(
        self,
        fork_url: str = "",
        block_number: int | None = None,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """Wait for Anvil to be ready to accept RPC connections.

        Args:
            fork_url: The fork URL that was used (for error context)
            block_number: The block number that was requested (for error context)
            timeout: Maximum seconds to wait for Anvil to be ready

        Returns:
            Dict with 'running' bool and optional 'error' message
        """
        import time

        port = self._foundry_config.anvil_port
        rpc_url = f"http://127.0.0.1:{port}"
        poll_interval = 2  # seconds between checks
        max_attempts = timeout // poll_interval

        self.logger.debug(f"Waiting for Anvil to be ready (timeout: {timeout}s)...")

        for attempt in range(max_attempts):
            # First check if process is still running
            ps_result = self.execute(
                "pgrep -fa '(^|/)anvil([[:space:]]|$).*--port' || echo 'not_running'"
            )
            # Prefer raw_output: subclass parsers may rewrite "output"
            ps_output = ps_result.get("raw_output", ps_result.get("output", ""))

            if "not_running" in ps_output or not ps_output.strip():
                # Process died, get error from log
                self.logger.debug("Anvil process not found, checking log for errors")
                log_result = self.execute("cat /tmp/anvil.log 2>/dev/null || echo 'no_log'")
                log_output = log_result.get("raw_output", log_result.get("output", ""))
                return self._diagnose_anvil_failure(log_output, fork_url, block_number)

            # Try to make an RPC call to verify Anvil is responding
            # Use cast chain-id as a simple connectivity test
            rpc_test = self.execute(f"cast chain-id --rpc-url {rpc_url} 2>&1")
            rpc_output = rpc_test.get("raw_output", rpc_test.get("output", ""))
            if "command not found" in (rpc_output or "").lower():
                return {
                    "running": False,
                    "error": (
                        "Anvil readiness check failed: `cast` is not available in the container.\n\n"
                        "Verify the Docker image includes Foundry tools (cast, anvil).\n"
                        "Image: "
                        f"{self._foundry_config.image}\n\n"
                        f"Command output:\n{rpc_output[:500]}"
                    ),
                }

            # Check if we got a valid chain ID (a number)
            rpc_output_clean = rpc_output.strip().split("\n")[-1].strip()
            if rpc_output_clean.isdigit():
                self.logger.debug(
                    f"Anvil ready after {(attempt + 1) * poll_interval}s "
                    f"(chain ID: {rpc_output_clean})"
                )
                return {"running": True, "chain_id": int(rpc_output_clean)}

            # Log progress for long waits
            if attempt > 0 and attempt % 5 == 0:
                self.logger.info(
                    f"Still waiting for Anvil to initialize... "
                    f"({(attempt + 1) * poll_interval}s elapsed)"
                )

            time.sleep(poll_interval)

        # Timeout reached - get log for diagnosis
        self.logger.warning(f"Anvil did not become ready within {timeout}s")
        log_result = self.execute("cat /tmp/anvil.log 2>/dev/null || echo 'no_log'")
        log_output = log_result.get("raw_output", log_result.get("output", ""))

        # Check if process is still running (might be slow but not dead)
        ps_result = self.execute(
            "pgrep -fa '(^|/)anvil([[:space:]]|$).*--port' || echo 'not_running'"
        )
        ps_output = ps_result.get("raw_output", ps_result.get("output", ""))

        if "not_running" not in ps_output and ps_output.strip():
            return {
                "running": False,
                "error": (
                    f"Anvil process is running but not responding to RPC after {timeout}s.\n\n"
                    f"This may indicate:\n"
                    f"  - Very slow fork initialization (try increasing timeout)\n"
                    f"  - Network issues connecting to the RPC endpoint\n"
                    f"  - RPC rate limiting\n\n"
                    f"Fork URL: {fork_url}\n"
                    f"Block number: {block_number or 'latest'}\n\n"
                    f"Anvil log (last 1000 chars):\n{log_output[-1000:]}"
                ),
            }

        return self._diagnose_anvil_failure(log_output, fork_url, block_number)

    def _diagnose_anvil_failure(
        self, log_output: str, fork_url: str, block_number: int | None
    ) -> dict[str, Any]:
        """Diagnose why Anvil failed to start based on log output.

        Args:
            log_output: Contents of /tmp/anvil.log
            fork_url: The fork URL that was used
            block_number: The block number that was requested

        Returns:
            Dict with 'running': False and detailed 'error' message
        """
        error_msg = "Anvil failed to start"
        log_lower = log_output.lower()

        # Common archive RPC error patterns
        archive_error_patterns = [
            "missing trie node",
            "header not found",
            "block not found",
            "state not available",
            "pruned state",
            "historical state",
            "archive node",
            "eth_getproof",
            "unable to fetch",
            "data not available",
        ]

        is_archive_error = any(pattern in log_lower for pattern in archive_error_patterns)

        if is_archive_error and block_number:
            error_msg = (
                f"Anvil fork failed at historical block {block_number}.\n\n"
                f"ERROR: The RPC endpoint '{fork_url}' does not support archive queries.\n\n"
                "Historical block forking requires an ARCHIVE RPC node that retains full state history.\n"
                "Public RPCs typically only support recent blocks (~128 blocks back).\n\n"
                "SOLUTIONS:\n"
                "  1. Use an archive RPC provider:\n"
                "     - Alchemy (free tier includes archive): https://www.alchemy.com/\n"
                "     - Infura (archive plan): https://infura.io/\n"
                "     - QuickNode (archive): https://www.quicknode.com/\n"
                "     - GetBlock (archive): https://getblock.io/\n\n"
                "  2. Configure in your .env file:\n"
                "     MAINNET_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY\n"
                "     BSC_RPC_URL=https://bsc.getblock.io/YOUR_KEY/mainnet/\n\n"
                "  3. For testing without archive access, try forking at 'latest' block.\n\n"
                f"Anvil log output:\n{log_output[:500]}"
            )
        elif "connection refused" in log_lower or "failed to connect" in log_lower:
            error_msg = (
                f"Anvil fork failed: Unable to connect to RPC endpoint.\n\n"
                f"RPC URL: {fork_url}\n\n"
                "Check that:\n"
                "  - The RPC URL is correct and accessible\n"
                "  - Your network connection is working\n"
                "  - Any API key in the URL is valid\n\n"
                f"Anvil log output:\n{log_output[:500]}"
            )
        elif "rate limit" in log_lower or "too many requests" in log_lower:
            error_msg = (
                f"Anvil fork failed: RPC rate limit exceeded.\n\n"
                f"RPC URL: {fork_url}\n\n"
                "The RPC provider is rate-limiting requests. Solutions:\n"
                "  - Wait a few minutes and retry\n"
                "  - Use a paid RPC plan with higher limits\n"
                "  - Use a different RPC provider\n\n"
                f"Anvil log output:\n{log_output[:500]}"
            )
        elif log_output.strip() and "no_log" not in log_output:
            # Generic failure with log content
            error_msg = (
                f"Anvil failed to start.\n\n"
                f"Fork URL: {fork_url}\n"
                f"Block number: {block_number or 'latest'}\n\n"
                f"Anvil log output:\n{log_output[:1000]}"
            )
        else:
            # No log or empty log
            error_msg = (
                f"Anvil failed to start (no log output available).\n\n"
                f"Fork URL: {fork_url}\n"
                f"Block number: {block_number or 'latest'}\n\n"
                "Check that:\n"
                "  - The Docker container is running\n"
                "  - Anvil is installed in the container\n"
                "  - The RPC URL is accessible from within the container"
            )

        return {"running": False, "error": error_msg}

    def get_anvil_rpc_url(self) -> str:
        """Get RPC URL for local anvil instance.

        Returns:
            Local RPC URL string
        """
        return f"http://127.0.0.1:{self._foundry_config.anvil_port}"

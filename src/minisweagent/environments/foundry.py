"""Foundry development environment for smart contract development.

This environment extends DockerEnvironment with Foundry-specific features:
- Pre-configured with Foundry tools (forge, cast, anvil, chisel)
- Volume mounting for host Foundry projects
- Environment variable forwarding for RPC URLs and API keys
- Longer timeouts suitable for contract compilation
"""

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from minisweagent.environments.docker import DockerEnvironment


class FoundryEnvironmentConfig(BaseModel):
    """Configuration for Foundry development environment."""

    # Docker image settings
    image: str = "ghcr.io/foundry-rs/foundry:latest"
    """Docker image with Foundry tools. Default is official Foundry image."""

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

    def start_anvil(self, fork_url: str = "", block_number: int | None = None) -> dict[str, Any]:
        """Start anvil local testnet in background.

        Args:
            fork_url: RPC URL to fork from. Uses config value if not provided.
            block_number: Block number to fork at. Latest if not provided.

        Returns:
            Execute result dict with output and returncode
        """
        fork_url = fork_url or self._foundry_config.anvil_fork_url
        port = self._foundry_config.anvil_port

        cmd_parts = [f"anvil --port {port}"]
        if fork_url:
            cmd_parts.append(f"--fork-url {fork_url}")
            if block_number:
                cmd_parts.append(f"--fork-block-number {block_number}")

        # Start in background with nohup
        anvil_cmd = " ".join(cmd_parts)
        background_cmd = f"nohup {anvil_cmd} > /tmp/anvil.log 2>&1 & sleep 2 && echo 'Anvil started on port {port}'"

        return self.execute(background_cmd)

    def get_anvil_rpc_url(self) -> str:
        """Get RPC URL for local anvil instance.

        Returns:
            Local RPC URL string
        """
        return f"http://127.0.0.1:{self._foundry_config.anvil_port}"

#!/usr/bin/env python3

"""Run the embedded EVMBench benchmark with the Yudai mini-swe-agent adapter."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal

import typer

from minisweagent.utils.log import logger

app = typer.Typer(rich_markup_mode="rich", add_completion=False)

EVMbenchMode = Literal["detect", "patch", "exploit"]
MODE_TO_AGENT_ID: dict[EVMbenchMode, str] = {
    "detect": "yudai-detect",
    "patch": "yudai-patch",
    "exploit": "yudai-exploit",
}
MODE_TO_DEFAULT_SPLIT: dict[EVMbenchMode, str] = {
    "detect": "detect-tasks",
    "patch": "patch-tasks",
    "exploit": "exploit-tasks",
}
RUNTIME_FILES = ("pyproject.toml", "README.md", "LICENSE.md")
FALLBACK_RUNTIME_FILE_CONTENTS = {
    "README.md": "# mini-swe-agent\n",
    "LICENSE.md": "See upstream repository for license details.\n",
}


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def get_default_project_dir() -> Path:
    return get_repo_root() / "evmBench-frontier-evals" / "project" / "evmbench"


def get_vendor_runtime_dir(project_dir: Path) -> Path:
    return project_dir / "evmbench" / "vendor" / "yudai_runtime"


def sync_evmbench_runtime(repo_root: Path, project_dir: Path) -> Path:
    """Stage the current mini-swe-agent runtime into the EVMBench Docker build context."""

    vendor_dir = get_vendor_runtime_dir(project_dir)
    shutil.rmtree(vendor_dir, ignore_errors=True)
    vendor_dir.mkdir(parents=True, exist_ok=True)
    (vendor_dir / ".gitignore").write_text("*\n!.gitignore\n")

    for fname in RUNTIME_FILES:
        src = repo_root / fname
        dst = vendor_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
        else:
            dst.write_text(FALLBACK_RUNTIME_FILE_CONTENTS[fname])

    shutil.copytree(repo_root / "src" / "minisweagent", vendor_dir / "src" / "minisweagent")
    return vendor_dir


def get_yudai_agent_id(mode: EVMbenchMode) -> str:
    return MODE_TO_AGENT_ID[mode]


def build_evmbench_entrypoint_command(
    *,
    mode: EVMbenchMode,
    audit: str | None,
    split: str | None,
    hint_level: str,
    concurrency: int,
    apply_gold_solution: bool,
    log_to_run_dir: bool,
) -> list[str]:
    command = [
        "uv",
        "run",
        "python",
        "-m",
        "evmbench.nano.entrypoint",
        f"evmbench.mode={mode}",
        f"evmbench.hint_level={hint_level}",
        f"evmbench.apply_gold_solution={'True' if apply_gold_solution else 'False'}",
        f"evmbench.log_to_run_dir={'True' if log_to_run_dir else 'False'}",
        "evmbench.solver=evmbench.nano.solver.EVMbenchSolver",
        f"evmbench.solver.agent_id={get_yudai_agent_id(mode)}",
        f"runner.concurrency={concurrency}",
    ]
    if audit:
        command.append(f"evmbench.audit={audit}")
    elif split:
        command.append(f"evmbench.audit_split={split}")
    else:
        command.append(f"evmbench.audit_split={MODE_TO_DEFAULT_SPLIT[mode]}")
    return command


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> int:
    logger.info("Running command in %s: %s", cwd, " ".join(command))
    result = subprocess.run(command, cwd=cwd, env=env, check=False)
    return result.returncode


def _build_yudai_images(
    *,
    project_dir: Path,
    audit: str | None,
    split: str | None,
    parallel: int,
) -> int:
    repo_root = get_repo_root()
    commands: list[tuple[list[str], Path]] = []

    should_rebuild_yudai_base = os.getenv("YUDAI_REBUILD_BASE", "").lower() in {"1", "true", "yes"}
    inspect_command = ["docker", "image", "inspect", "yudai-base:latest"]
    if should_rebuild_yudai_base or _run(inspect_command, cwd=repo_root) != 0:
        commands.append(
            (
                [
                    "docker",
                    "build",
                    "-f",
                    "docker/Dockerfile.base",
                    "-t",
                    "yudai-base:latest",
                    ".",
                ],
                repo_root,
            )
        )

    commands.extend(
        [
        (
            [
                "docker",
                "build",
                "-f",
                "ploit/Dockerfile",
                "-t",
                "ploit-builder:latest",
                "--target",
                "ploit-builder",
                ".",
            ],
            project_dir,
        ),
        (
            [
                "docker",
                "build",
                "-f",
                "evmbench/Dockerfile.yudai",
                "-t",
                "evmbench/base:latest",
                ".",
            ],
            project_dir,
        ),
        ]
    )

    for command, cwd in commands:
        rc = _run(command, cwd=cwd)
        if rc != 0:
            return rc

    build_command = [
        "uv",
        "run",
        "docker_build.py",
        "--no-build-base",
        "--parallel",
        str(parallel),
    ]
    if audit:
        build_command.extend(["--audit", audit])
    elif split:
        build_command.extend(["--split", split])
    else:
        build_command.extend(["--split", "all"])
    return _run(build_command, cwd=project_dir)


@app.command()
def main(
    mode: EVMbenchMode = typer.Option("exploit", "--mode"),
    audit: str = typer.Option("", "--audit", help="Run a single audit id"),
    split: str = typer.Option("", "--split", help="Run a named EVMBench split"),
    model: str | None = typer.Option(None, "-m", "--model", help="Model name for Yudai"),
    model_class: str = typer.Option("openrouter", "--model-class", help="mini-swe-agent model class"),
    hint_level: str = typer.Option("none", "--hint-level"),
    concurrency: int = typer.Option(1, "--concurrency"),
    cost_limit: float | None = typer.Option(None, "--cost-limit", help="Optional mini-swe-agent cost limit"),
    project_dir: Path = typer.Option(get_default_project_dir(), "--project-dir"),
    sync_runtime_only: bool = typer.Option(False, "--sync-runtime-only", help="Only stage the runtime"),
    build_images: bool = typer.Option(False, "--build-images", help="Build the Yudai EVMBench images before running"),
    build_parallel: int = typer.Option(4, "--build-parallel", help="Parallel audit image builds"),
    build_only: bool = typer.Option(False, "--build-only", help="Build images but do not run the eval"),
    apply_gold_solution: bool = typer.Option(False, "--apply-gold-solution"),
    log_to_run_dir: bool = typer.Option(True, "--log-to-run-dir/--no-log-to-run-dir"),
) -> None:
    project_dir = project_dir.resolve()
    repo_root = get_repo_root()

    if not project_dir.exists():
        raise typer.BadParameter(f"EVMBench project directory does not exist: {project_dir}")

    selected_split = split or None
    selected_audit = audit or None
    if not selected_audit and not selected_split:
        selected_split = MODE_TO_DEFAULT_SPLIT[mode]

    if sync_runtime_only or build_images:
        vendor_dir = sync_evmbench_runtime(repo_root, project_dir)
        logger.info("Synced Yudai runtime into %s", vendor_dir)
        if sync_runtime_only:
            return

    if build_images:
        rc = _build_yudai_images(
            project_dir=project_dir,
            audit=selected_audit,
            split=selected_split,
            parallel=build_parallel,
        )
        if rc != 0:
            raise typer.Exit(rc)
        if build_only:
            return

    effective_model = model or os.getenv("YUDAI_EVMBENCH_MODEL")
    if not effective_model:
        raise typer.BadParameter(
            "Model name is required. Pass --model or set YUDAI_EVMBENCH_MODEL in the environment."
        )

    env = os.environ.copy()
    env["YUDAI_EVMBENCH_MODEL"] = effective_model
    env["YUDAI_EVMBENCH_MODEL_CLASS"] = model_class
    if cost_limit is not None:
        env["YUDAI_EVMBENCH_COST_LIMIT"] = str(cost_limit)

    command = build_evmbench_entrypoint_command(
        mode=mode,
        audit=selected_audit,
        split=selected_split,
        hint_level=hint_level,
        concurrency=concurrency,
        apply_gold_solution=apply_gold_solution,
        log_to_run_dir=log_to_run_dir,
    )
    rc = _run(command, cwd=project_dir, env=env)
    if rc != 0:
        raise typer.Exit(rc)


if __name__ == "__main__":
    app()

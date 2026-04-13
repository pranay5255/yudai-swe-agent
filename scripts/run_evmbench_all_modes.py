#!/usr/bin/env python3

"""Run EVMBench with the default mini-SWE-agent adapter across detect, patch, and exploit."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer

from minisweagent.run.extra.evmbench import (
    MODE_TO_DEFAULT_SPLIT,
    _build_yudai_images,
    build_evmbench_entrypoint_command,
    get_default_project_dir,
    get_repo_root,
    sync_evmbench_runtime,
)
from minisweagent.utils.log import logger

app = typer.Typer(rich_markup_mode="rich", add_completion=False)
ALL_MODES = ("detect", "patch", "exploit")


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> int:
    logger.info("Running command in %s: %s", cwd, " ".join(command))
    result = subprocess.run(command, cwd=cwd, env=env, check=False)
    return result.returncode


@app.command()
def main(
    audit: str = typer.Option("", "--audit", help="Run a single audit id across all modes."),
    model: str | None = typer.Option(
        None,
        "-m",
        "--model",
        help="Model name passed through to the embedded Yudai/default mini-SWE-agent adapter.",
    ),
    model_class: str = typer.Option("openrouter", "--model-class"),
    hint_level: str = typer.Option("none", "--hint-level"),
    concurrency: int = typer.Option(1, "--concurrency"),
    cost_limit: float | None = typer.Option(None, "--cost-limit"),
    project_dir: Path = typer.Option(get_default_project_dir(), "--project-dir"),
    build_images: bool = typer.Option(True, "--build-images/--no-build-images"),
    build_parallel: int = typer.Option(4, "--build-parallel"),
    apply_gold_solution: bool = typer.Option(False, "--apply-gold-solution"),
    log_to_run_dir: bool = typer.Option(True, "--log-to-run-dir/--no-log-to-run-dir"),
) -> None:
    project_dir = project_dir.resolve()
    repo_root = get_repo_root()

    if not project_dir.exists():
        raise typer.BadParameter(f"EVMBench project directory does not exist: {project_dir}")

    effective_model = model or os.getenv("YUDAI_EVMBENCH_MODEL")
    if not effective_model:
        raise typer.BadParameter(
            "Model name is required. Pass --model or set YUDAI_EVMBENCH_MODEL in the environment."
        )

    vendor_dir = sync_evmbench_runtime(repo_root, project_dir)
    logger.info("Synced Yudai runtime into %s", vendor_dir)

    if build_images:
        rc = _build_yudai_images(
            project_dir=project_dir,
            audit=audit or None,
            split="all" if not audit else None,
            parallel=build_parallel,
        )
        if rc != 0:
            raise typer.Exit(rc)

    env = os.environ.copy()
    env["YUDAI_EVMBENCH_MODEL"] = effective_model
    env["YUDAI_EVMBENCH_MODEL_CLASS"] = model_class
    if cost_limit is not None:
        env["YUDAI_EVMBENCH_COST_LIMIT"] = str(cost_limit)

    for mode in ALL_MODES:
        command = build_evmbench_entrypoint_command(
            mode=mode,
            audit=audit or None,
            split=None if audit else MODE_TO_DEFAULT_SPLIT[mode],
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

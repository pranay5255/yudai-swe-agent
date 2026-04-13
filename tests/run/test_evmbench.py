from __future__ import annotations

from pathlib import Path

import yaml

from minisweagent.run.extra.evmbench import (
    build_evmbench_entrypoint_command,
    get_vendor_runtime_dir,
    get_yudai_agent_id,
    sync_evmbench_runtime,
)
from minisweagent.run.extra.evmbench_agent import build_evmbench_task


def test_build_evmbench_task_includes_mode_specific_guidance():
    instructions = "Audit the repository."
    task = build_evmbench_task("exploit", instructions)

    assert "Audit the repository." in task
    assert "txs.json" in task
    assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in task


def test_get_yudai_agent_id_uses_mode_specific_adapter():
    assert get_yudai_agent_id("detect") == "yudai-detect"
    assert get_yudai_agent_id("patch") == "yudai-patch"
    assert get_yudai_agent_id("exploit") == "yudai-exploit"


def test_yudai_agent_ids_exist_in_embedded_evmbench_config():
    config_path = Path("evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/config.yaml")
    config = yaml.safe_load(config_path.read_text())

    for mode in ("detect", "patch", "exploit"):
        assert get_yudai_agent_id(mode) in config


def test_build_evmbench_entrypoint_command_prefers_audit_over_split():
    command = build_evmbench_entrypoint_command(
        mode="exploit",
        audit="2024-08-phi",
        split="exploit-tasks",
        hint_level="none",
        concurrency=1,
        apply_gold_solution=False,
        log_to_run_dir=True,
    )

    assert "evmbench.mode=exploit" in command
    assert "evmbench.audit=2024-08-phi" in command
    assert "evmbench.audit_split=exploit-tasks" not in command
    assert "evmbench.solver.agent_id=yudai-exploit" in command


def test_sync_evmbench_runtime_copies_required_files(tmp_path: Path):
    repo_root = tmp_path / "repo"
    project_dir = tmp_path / "project"
    (repo_root / "src" / "minisweagent").mkdir(parents=True)
    (project_dir / "evmbench" / "vendor").mkdir(parents=True)

    (repo_root / "pyproject.toml").write_text("[project]\nname='mini-swe-agent'\n")
    (repo_root / "README.md").write_text("readme")
    (repo_root / "LICENSE.md").write_text("license")
    (repo_root / "src" / "minisweagent" / "__init__.py").write_text("__version__ = '0.0.0'\n")

    vendor_dir = sync_evmbench_runtime(repo_root, project_dir)

    assert vendor_dir == get_vendor_runtime_dir(project_dir)
    assert (vendor_dir / "pyproject.toml").exists()
    assert (vendor_dir / "README.md").exists()
    assert (vendor_dir / "LICENSE.md").exists()
    assert (vendor_dir / "src" / "minisweagent" / "__init__.py").exists()

# Deprecated Components

This directory contains files and folders moved out of the active tree to keep
the repo focused on running `scripts/run_benchmark_exploit.py` with the A1
architecture described in `exploitGen.pdf`.

Top-level buckets:
- `deprecated/scripts/`: non-benchmark runners and utilities.
- `deprecated/exploit_generation/`: local-episode pipeline pieces and unused templates.
- `deprecated/src/minisweagent/`: extra agents, configs, environments, models, and CLI runners.
- `deprecated/docker/`: Docker assets not required for the benchmark runner.
- `deprecated/docs/`, `deprecated/tests/`, `deprecated/contracts/`, `deprecated/MuSe/`,
  `deprecated/vulnerability_injection/`: unrelated documentation, datasets, and tooling.

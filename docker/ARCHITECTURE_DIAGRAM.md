# Docker Hierarchy Architecture Diagram

## System Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        DOCKER IMAGE HIERARCHY                              │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                     yudai-base:latest (Parent)                        │ │
│  │  Size: 1.2 GB | Build Time: 3-5 min | Built: Once                   │ │
│  ├──────────────────────────────────────────────────────────────────────┤ │
│  │  FROM: foundry:latest                                                │ │
│  │  ┌────────────────────────────────────────────────────────────────┐ │ │
│  │  │ • Foundry (forge, cast, anvil, chisel)                         │ │ │
│  │  │ • Python 3.12 + uv package manager                             │ │ │
│  │  │ • Security Tools:                                              │ │ │
│  │  │   - Slither 0.10.2  (static analysis)                          │ │ │
│  │  │   - Mythril 0.24.8  (symbolic execution)                       │ │ │
│  │  │   - Aderyn 0.6.5    (detector)                                 │ │ │
│  │  │   - Echidna 2.2.5   (fuzzer)                                   │ │ │
│  │  │ • Multiple solc versions:                                      │ │ │
│  │  │   - 0.4.26, 0.5.17, 0.6.12, 0.7.6, 0.8.20, 0.8.24             │ │ │
│  │  └────────────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                    │                                       │
│                                    │ inherits                              │
│                  ┌─────────────────┼─────────────────┬───────────────┐    │
│                  │                 │                 │               │    │
│                  ▼                 ▼                 ▼               ▼    │
│  ┌─────────────────────┐ ┌──────────────────┐ ┌──────────────┐ ┌────────┐ │
│  │ sol-0.4-standalone  │ │ sol-0.8-         │ │ sol-0.8-     │ │ sol-0.8│ │
│  │                     │ │ standalone       │ │ oz-v4        │ │ -oz-v5 │ │
│  ├─────────────────────┤ ├──────────────────┤ ├──────────────┤ ├────────┤ │
│  │ +50 MB              │ │ +50 MB           │ │ +150 MB      │ │+150 MB │ │
│  │ 1-2 min build       │ │ 1-2 min build    │ │ 2-3 min build│ │2-3 min │ │
│  └─────────────────────┘ └──────────────────┘ └──────────────┘ └────────┘ │
│          │                       │                   │              │      │
│          │ contains              │ contains          │ contains     │ cont │
│          ▼                       ▼                   ▼              ▼      │
│  /templates/           /templates/           /templates/     /templates/   │
│  sol-0.4-standalone    sol-0.8-standalone    sol-0.8-oz-v4  sol-0.8-oz-v5 │
└────────────────────────────────────────────────────────────────────────────┘
```

## Template Structure

```
/templates/<template-name>/
├── foundry.toml          # Pre-configured for solc version
│   ├── [profile.default]
│   ├── src = "src"
│   ├── solc = "X.X.XX"
│   └── [remappings]      # OZ imports if needed
│
├── src/
│   ├── Sample.sol        # Example contract (verified)
│   └── stubs/            # (if needed)
│
├── lib/
│   └── openzeppelin-contracts/  # (for OZ templates)
│       └── ...           # Pre-installed, ready to use
│
├── test/
│   └── Sample.t.sol      # Example test (passing)
│
└── README.md             # Template documentation
```

## Episode Workflow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. START EPISODE                                                         │
│    python scripts/run_minimal_episode.py -c contracts/SimpleBank.sol    │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 2. INJECT VULNERABILITY (MuSe)                                           │
│    SimpleBank.sol → SimpleBank_mutated.sol                              │
│    - Operator: RE (Reentrancy)                                          │
│    - Line: 42-48                                                        │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 3. ANALYZE CONTRACT (contract_analyzer.py)                              │
│    metadata = analyze_contract(SimpleBank_mutated.sol)                 │
│    ┌──────────────────────────────────────────────────────────────────┐ │
│    │ Detected:                                                        │ │
│    │  - Solidity Version: 0.8.20                                      │ │
│    │  - OpenZeppelin: No                                              │ │
│    │  - Imports: []                                                   │ │
│    │  - Recommended: sol-0.8-standalone                               │ │
│    └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 4. SELECT DOCKER IMAGE (environment_builder.py)                         │
│    image = select_docker_image(metadata)                                │
│    → Selected: yudai-sol-0.8-standalone:latest                          │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 5. EXTRACT TEMPLATE (2-5 seconds)                                       │
│    docker create yudai-sol-0.8-standalone:latest → container_abc123     │
│    docker cp container_abc123:/templates/sol-0.8-standalone /workspace  │
│    docker rm container_abc123                                           │
│    ┌──────────────────────────────────────────────────────────────────┐ │
│    │ /workspace/ now contains:                                        │ │
│    │  ├── foundry.toml    (solc = "0.8.20")                           │ │
│    │  ├── src/            (empty, ready for contract)                 │ │
│    │  ├── lib/            (forge-std)                                 │ │
│    │  └── test/           (empty, ready for tests)                    │ │
│    └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 6. COPY MUTATED CONTRACT                                                │
│    cp SimpleBank_mutated.sol /workspace/src/SimpleBank.sol             │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 7. VERIFY COMPILATION (forge build)                                     │
│    cd /workspace && forge build                                         │
│    ✅ SUCCESS - Contract compiles                                       │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 8. START DOCKER CONTAINER (FoundryEnvironment)                          │
│    docker run -v /workspace:/workspace yudai-sol-0.8-standalone         │
│    Agent now has working environment!                                   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 9. AGENT FIXES VULNERABILITY                                             │
│    - Reads contract                                                      │
│    - Runs slither (detects reentrancy)                                  │
│    - Edits contract (adds ReentrancyGuard)                              │
│    - Runs forge build (verifies fix)                                    │
│    - Runs slither again (confirms fix)                                  │
│    - Submits                                                             │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 10. COMPUTE REWARD                                                       │
│     ✅ Vulnerability Fixed: Yes                                         │
│     ✅ Compilation Passed: Yes                                          │
│     ✅ No New Vulns: Yes                                                │
│     Reward: +1.0                                                        │
└──────────────────────────────────────────────────────────────────────────┘

Total Time: ~7 seconds setup + agent work
(Was: ~75 seconds setup + agent work)
```

## Image Selection Decision Tree

```
                        Analyze Contract
                              │
                              ▼
                   ┌──────────────────────┐
                   │ Check Solidity Version│
                   └──────────┬────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
      < 0.5.0 ?          0.5-0.7 ?          >= 0.8.0 ?
           │                  │                  │
           ▼                  ▼                  ▼
    sol-0.4-standalone  sol-0.8-standalone      │
                                                 │
                                        ┌────────┴────────┐
                                        │                 │
                                        ▼                 ▼
                                Has OpenZeppelin?        No
                                        │                 │
                                        │                 ▼
                                        │         sol-0.8-standalone
                                        │
                                ┌───────┴───────┐
                                │               │
                                ▼               ▼
                          Check OZ Version     │
                                │               │
                        ┌───────┴───────┐       │
                        │               │       │
                        ▼               ▼       ▼
                    v4.x ?          v5.x ?   Default
                        │               │       │
                        ▼               ▼       ▼
                sol-0.8-oz-v4   sol-0.8-oz-v5  sol-0.8-oz-v4
```

## Build Process Flow

```
$ ./docker/build-all.sh

┌─────────────────────────────────────────────────────────┐
│ STEP 1: Build Base Image (3-5 min)                     │
├─────────────────────────────────────────────────────────┤
│ [1/20] FROM foundry:latest                             │
│ [2/20] Install Python 3.12                             │
│ [3/20] Install uv package manager                      │
│ [4/20] Create venv for Slither                         │
│ [5/20] Create venv for Mythril                         │
│ [6/20] Install Slither 0.10.2                          │
│ [7/20] Install Mythril 0.24.8                          │
│ [8/20] Install solc-select                             │
│ [9/20] Install solc 0.4.26                             │
│ [10/20] Install solc 0.5.17                            │
│ [11/20] Install solc 0.6.12                            │
│ [12/20] Install solc 0.7.6                             │
│ [13/20] Install solc 0.8.20                            │
│ [14/20] Install solc 0.8.24                            │
│ [15/20] Install Aderyn                                 │
│ [16/20] Install Echidna                                │
│ [17/20] Create mythril wrapper                         │
│ [18/20] Verify all tools                               │
│ [19/20] Set environment variables                      │
│ [20/20] Tag as yudai-base:latest                       │
│ ✅ SUCCESS                                              │
└─────────────────────────────────────────────────────────┘
               │
               ├────────────────────────────────────────┐
               │                                        │
┌──────────────▼───────────────┐    ┌─────────────────▼─────────────────┐
│ STEP 2a: sol-0.4-standalone  │    │ STEP 2b: sol-0.8-standalone      │
│ (1-2 min)                    │    │ (1-2 min)                        │
├──────────────────────────────┤    ├──────────────────────────────────┤
│ FROM yudai-base:latest       │    │ FROM yudai-base:latest           │
│ WORKDIR /templates/...       │    │ WORKDIR /templates/...           │
│ RUN forge init               │    │ RUN forge init                   │
│ RUN cat > foundry.toml       │    │ RUN cat > foundry.toml           │
│ RUN cat > src/Sample.sol     │    │ RUN cat > src/Sample.sol         │
│ RUN forge build (verify)     │    │ RUN forge build (verify)         │
│ ✅ SUCCESS                    │    │ ✅ SUCCESS                        │
└──────────────────────────────┘    └──────────────────────────────────┘

               │                                        │
               ├────────────────────────────────────────┤
               │                                        │
┌──────────────▼───────────────┐    ┌─────────────────▼─────────────────┐
│ STEP 2c: sol-0.8-oz-v4       │    │ STEP 2d: sol-0.8-oz-v5           │
│ (2-3 min)                    │    │ (2-3 min)                        │
├──────────────────────────────┤    ├──────────────────────────────────┤
│ FROM yudai-base:latest       │    │ FROM yudai-base:latest           │
│ WORKDIR /templates/...       │    │ WORKDIR /templates/...           │
│ RUN forge init               │    │ RUN forge init                   │
│ RUN forge install OZ@v4.9.6  │    │ RUN forge install OZ@v5.0.2      │
│ RUN cat > foundry.toml       │    │ RUN cat > foundry.toml           │
│ RUN cat > src/Token.sol      │    │ RUN cat > src/Token.sol          │
│ RUN forge build (verify)     │    │ RUN forge build (verify)         │
│ ✅ SUCCESS                    │    │ ✅ SUCCESS                        │
└──────────────────────────────┘    └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ STEP 3: Summary                                         │
├─────────────────────────────────────────────────────────┤
│ Base Image: ✅ yudai-base:latest                        │
│ Templates Built: 4/4                                    │
│ Total Time: ~12 minutes                                 │
│ Total Size: ~1.6 GB                                     │
│                                                         │
│ Available Images:                                       │
│   - yudai-base:latest                                   │
│   - yudai-sol-0.4-standalone:latest                     │
│   - yudai-sol-0.8-standalone:latest                     │
│   - yudai-sol-0.8-oz-v4:latest                          │
│   - yudai-sol-0.8-oz-v5:latest                          │
└─────────────────────────────────────────────────────────┘
```

## Layer Sharing Visualization

```
┌─────────────────────────────────────────────────────────┐
│ Disk Layout (shows shared layers)                      │
└─────────────────────────────────────────────────────────┘

Layer 0: FROM foundry:latest                  (~800 MB)
    ├── Shared by ALL images
    │
Layer 1: System packages + Python             (~200 MB)
    ├── Shared by ALL images
    │
Layer 2: Security tools (Slither, Mythril)    (~150 MB)
    ├── Shared by ALL images
    │
Layer 3: Multiple solc versions               (~50 MB)
    ├── Shared by ALL images
    │
    ├──────────────────────────────────────────────────
    │ BASE IMAGE TOTAL: 1.2 GB
    └──────────────────────────────────────────────────
                    │
        ┌───────────┼───────────┬───────────────┐
        │           │           │               │
        ▼           ▼           ▼               ▼
    Layer 4a    Layer 4b    Layer 4c        Layer 4d
    Template    Template    Template        Template
    0.4         0.8         0.8-OZ-v4       0.8-OZ-v5
    +50 MB      +50 MB      +150 MB         +150 MB
        │           │           │               │
        │           │           │               │
        ▼           ▼           ▼               ▼
    Image 1     Image 2     Image 3         Image 4
    1.25 GB     1.25 GB     1.35 GB         1.35 GB

Total Unique Data: 1.2 GB (base) + 0.4 GB (all templates) = 1.6 GB
Without Sharing: 1.25 + 1.25 + 1.35 + 1.35 = 5.2 GB
Savings: 5.2 - 1.6 = 3.6 GB (69% reduction!)
```

## Performance Comparison Chart

```
Environment Setup Time (seconds)

Without Hierarchy:
0    10   20   30   40   50   60   70   80   90
├────┼────┼────┼────┼────┼────┼────┼────┼────┤
│█████████████████████████████████████████████│  85s
└────┴────┴────┴────┴────┴────┴────┴────┴────┘
     │    │                    │
     Init  Setup              OZ Install (60s)

With Hierarchy:
0    10
├────┼
│████│  7s
└────┘
     │
     Extract template (2s) + Verify (3s)

Speedup: 85s → 7s = 12x faster
Savings: 78 seconds per episode
Over 100 episodes: 2.2 hours saved
```

---

**This diagram shows the complete architecture and data flow of the Docker hierarchy system.**

**Last Updated**: 2026-01-13

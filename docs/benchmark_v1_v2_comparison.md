# Benchmark V1 vs V2 Comparison

This document provides visual diagrams comparing the V1 and V2 benchmark systems, highlighting key differences and the fixes applied.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BENCHMARK SYSTEM COMPARISON                         │
├─────────────────────────────┬───────────────────────────────────────────────┤
│           V1                │                    V2                         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ • --fork-retries flag       │  • --retries flag (fixed)                     │
│ • Substring parser matching │  • Token-based parser (shlex)                 │
│ • interactive=False default │  • interactive=None (auto-detect)             │
│ • Parsed output preferred   │  • Raw output preferred for logging           │
│ • exploit_foundry env       │  • exploit_foundry + exploit_foundry_v2       │
└─────────────────────────────┴───────────────────────────────────────────────┘
```

---

## State Diagrams

### V1 Benchmark State Flow

```
                    ┌─────────────────┐
                    │     START       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Parse Config   │
                    │  (interactive   │
                    │   =False)       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Create Agent   │
                    │  (default env)  │
                    └────────┬────────┘
                             │
                             ▼
         ┌─────────────────────────────────────┐
         │       RUN BENCHMARK EPISODE         │
         │  ┌─────────────────────────────┐   │
         │  │  1. Start Anvil             │   │
         │  │     (fork-retries flag)     │   │
         │  └─────────────┬───────────────┘   │
         │                │                   │
         │                ▼                   │
         │  ┌─────────────────────────────┐   │
         │  │  2. Wait for Ready          │   │
         │  │     (substring matching)    │   │
         │  │     ⚠️ Can match false      │   │
         │  │        positives            │   │
         │  └─────────────┬───────────────┘   │
         │                │                   │
         │                ▼                   │
         │  ┌─────────────────────────────┐   │
         │  │  3. Execute Commands        │   │
         │  │     (parse output)          │   │
         │  └─────────────┬───────────────┘   │
         │                │                   │
         │                ▼                   │
         │  ┌─────────────────────────────┐   │
         │  │  4. Log Results             │   │
         │  │     (parsed output first)   │   │
         │  └─────────────┬───────────────┘   │
         │                │                   │
         └────────────────┼───────────────────┘
                          │
                          ▼
                    ┌─────────────────┐
                    │  CHECK RESULT   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐   ┌─────────┐   ┌───────────┐
        │ SUCCESS │   │  FAIL   │   │   ERROR   │
        │         │   │         │   │           │
        │ Profitable│ │ Not     │   │ Exception │
        │ exploit │   │ profitable│  │           │
        └────┬────┘   └────┬────┘   └─────┬─────┘
             │             │              │
             └─────────────┴──────────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │      END        │
                    └─────────────────┘
```

### V2 Benchmark State Flow

```
                    ┌─────────────────┐
                    │     START       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Parse Config   │
                    │  (interactive   │
                    │   =None auto)   │◄───────┐
                    └────────┬────────┘        │
                             │                 │
                             ▼                 │
                    ┌─────────────────┐        │
                    │  Create Agent   │        │
                    │  (env alias     │        │
                    │   mapping)      │        │
                    └────────┬────────┘        │
                             │                 │
                             ▼                 │
         ┌─────────────────────────────────────┐│
         │       RUN BENCHMARK EPISODE         ││
         │  ┌─────────────────────────────┐   ││
         │  │  1. Start Anvil             │   ││
         │  │     (--retries flag) ✓      │   ││
         │  └─────────────┬───────────────┘   ││
         │                │                   ││
         │                ▼                   ││
         │  ┌─────────────────────────────┐   ││
         │  │  2. Wait for Ready          │   ││
         │  │     (token-based shlex)     │   ││
         │  │     ✓ No false positives    │   ││
         │  └─────────────┬───────────────┘   ││
         │                │                   ││
         │                ▼                   ││
         │  ┌─────────────────────────────┐   ││
         │  │  3. Execute Commands        │   ││
         │  │     (raw + parsed output)   │   ││
         │  └─────────────┬───────────────┘   ││
         │                │                   ││
         │                ▼                   ││
         │  ┌─────────────────────────────┐   ││
         │  │  4. Log Results             │   ││
         │  │     (raw output first) ✓    │   ││
         │  └─────────────┬───────────────┘   ││
         │                │                   ││
         └────────────────┼───────────────────┘│
                          │                    │
                    ┌─────┴─────┐              │
                    │  Timeout? │──────────────┘ (retry with
                    │  Error?   │                interactive)
                    └─────┬─────┘
                          │
                          ▼
                    ┌─────────────────┐
                    │  CHECK RESULT   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐   ┌─────────┐   ┌───────────┐
        │ SUCCESS │   │  FAIL   │   │   ERROR   │
        │         │   │         │   │           │
        │ Profitable│ │ Not     │   │ Exception │
        │ exploit │   │ profitable│  │           │
        └────┬────┘   └────┬────┘   └─────┬─────┘
             │             │              │
             └─────────────┴──────────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │   SAVE JSON     │
                    │  (correct meta) │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │      END        │
                    └─────────────────┘
```

---

## Flow Comparison: Parser Command Detection

### V1: Substring Matching (Problematic)

```
┌────────────────────────────────────────────────────────────────────────┐
│                          V1 PARSER DETECTION                           │
│                      (src/minisweagent/environments/                   │
│                       extra/foundry_parsed.py:60)                      │
└────────────────────────────────────────────────────────────────────────┘

    Input Command
         │
         ▼
    ┌─────────────────┐
    │  Regex Search   │
    │  r"anvil"       │
    └────────┬────────┘
             │
     ┌───────┴───────┐
     │               │
  MATCH           NO MATCH
     │               │
     ▼               ▼
┌─────────┐    ┌──────────┐
│ Anvil   │    │ Continue │
│ Command │    │ Parsing  │
└────┬────┘    └──────────┘
     │
     │  ⚠️ PROBLEM: Matches ANYTHING containing "anvil"
     │
     │     "pgrep -f anvil"           ──────►  FALSE POSITIVE
     │     "cat /tmp/anvil.log"       ──────►  FALSE POSITIVE  
     │     "echo 'anvil is running'"  ──────►  FALSE POSITIVE
     │
     │     "anvil --fork-url ..."     ──────►  Correct match
     │
     ▼
┌─────────────────────────────────────────┐
│  Result: Commands misclassified,        │
│  logging issues, unexpected behavior    │
└─────────────────────────────────────────┘
```

### V2: Token-Based Detection (Fixed)

```
┌────────────────────────────────────────────────────────────────────────┐
│                          V2 PARSER DETECTION                           │
│                      (src/minisweagent/environments/                   │
│                       extra/foundry_parsed_v2.py:67)                   │
└────────────────────────────────────────────────────────────────────────┘

    Input Command
         │
         ▼
    ┌─────────────────┐
    │   shlex.split() │◄─── Tokenizes command properly
    └────────┬────────┘      (handles quotes, escapes)
             │
             ▼
    ┌─────────────────┐
    │  Check tokens[0]│◄─── First token = tool name
    │  Check tokens[1]│◄─── Second token = subcommand
    └────────┬────────┘
             │
     ┌───────┴───────┐
     │               │
  MATCH           NO MATCH
     │               │
     ▼               ▼
┌─────────┐    ┌──────────┐
│ Anvil   │    │ Continue │
│ Command │    │ Parsing  │
└────┬────┘    └──────────┘
     │
     │  ✓ FIXED: Only matches actual anvil command
     │
     │     "pgrep -f anvil"           ──────►  NOT an anvil command
     │     "cat /tmp/anvil.log"       ──────►  NOT an anvil command
     │     "echo 'anvil is running'"  ──────►  NOT an anvil command
     │
     │     "anvil --fork-url ..."     ──────►  ✓ Correct match!
     │     tokens[0] == "anvil"
     │
     ▼
┌─────────────────────────────────────────┐
│  Result: Accurate detection,            │
│  reliable logging, correct behavior     │
└─────────────────────────────────────────┘
```

---

## Environment Resolution Flow

### V1 Environment Mapping

```
┌────────────────────────────────────────────────────────────────┐
│                     V1 ENVIRONMENT RESOLUTION                  │
└────────────────────────────────────────────────────────────────┘

  Config File                      Environment Registry
  (benchmark_exploit.yaml)         (src/minisweagent/environments/__init__.py)
         │                                          │
         │  env_type: foundry_parsed                │
         │  ───────────────────────────►            │
         │                                          ▼
         │                               ┌─────────────────────┐
         │                               │  "foundry_parsed"   │
         │                               │   ─────► Foundry    │
         │                               │        ExploitEnv   │
         │                               └─────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  Available Aliases:                                         │
  │                                                             │
  │    exploit_foundry ─────► FoundryExploitEnvironment         │
  │                                                             │
  │  ⚠️ No V2-specific alias available!                         │
  └─────────────────────────────────────────────────────────────┘
```

### V2 Environment Mapping (Fixed)

```
┌────────────────────────────────────────────────────────────────┐
│                     V2 ENVIRONMENT RESOLUTION                  │
└────────────────────────────────────────────────────────────────┘

  Config File                      Environment Registry
  (benchmark_exploit_v2.yaml)      (src/minisweagent/environments/__init__.py)
         │                                          │
         │  env_type: exploit_foundry_v2 ✓          │
         │  ───────────────────────────►            │
         │                                          ▼
         │                               ┌─────────────────────┐
         │                               │  "foundry_parsed"   │
         │                               │   ─────► Foundry    │
         │                               │        ExploitEnv   │
         │                               │                     │
         │                               │  "exploit_foundry_v2│◄──┐
         │                               │   ─────► FoundryV2   │   │
         │                               │        ExploitEnv    │   │
         │                               └─────────────────────┘   │
         │                                                         │
         ▼                                                         │
  ┌─────────────────────────────────────────────────────────────┐  │
  │  Available Aliases:                                         │  │
  │                                                             │  │
  │    exploit_foundry ─────► FoundryExploitEnvironment (V1)    │  │
  │    exploit_foundry_v2 ──► FoundryExploitEnvironmentV2 (V2)  │──┘
  │                                                             │
  │  ✓ Both V1 and V2 aliases available!                        │
  └─────────────────────────────────────────────────────────────┘
```

---

## Configuration Flag Comparison

### Anvil Retry Flags

```
┌────────────────────────────────────────────────────────────────────────┐
│                     ANVIL RETRY FLAG EVOLUTION                         │
└────────────────────────────────────────────────────────────────────────┘

V1 Configuration (BEFORE)                          V2 Configuration (AFTER)
(benchmark_exploit.yaml)                           (benchmark_exploit_v2.yaml)

┌─────────────────────────┐                        ┌─────────────────────────┐
│ anvil_flags:            │                        │ anvil_flags:            │
│   - --fork-url          │                        │   - --fork-url          │
│   - ...                 │                        │   - ...                 │
│   - --fork-retries      │◄── WRONG!              │   - --retries           │◄── CORRECT!
│   - 3                   │   (V2 doesn't support  │   - 3                   │
└─────────────────────────┘    --fork-retries)     └─────────────────────────┘

  Error: Unrecognized option: '--fork-retries'      ✓ Anvil starts successfully

```

### Interactive Mode

```
┌────────────────────────────────────────────────────────────────────────┐
│                    INTERACTIVE MODE BEHAVIOR                           │
└────────────────────────────────────────────────────────────────────────┘

V1 (BEFORE)                                        V2 (AFTER)

┌─────────────────────────┐                        ┌─────────────────────────┐
│ interactive = False     │                        │ interactive = None      │
│ (hard-coded default)    │                        │ (None = auto-detect)    │
└───────────┬─────────────┘                        └───────────┬─────────────┘
            │                                                  │
            ▼                                                  ▼
┌─────────────────────────┐                        ┌─────────────────────────┐
│ Always non-interactive  │                        │ Check if TTY available  │
│ No auto-retry on fail   │                        │                         │
│                         │                        │ If TTY ──► Interactive  │
│ Episode fails on error  │                        │ If no TTY ─► Batch mode │
└─────────────────────────┘                        │                         │
                                                   │ Can retry with          │
                                                   │ interactive=True        │
                                                   │ if timeout/error        │
                                                   └─────────────────────────┘
```

---

## Output Logging Flow

### V1 vs V2 Logging Preference

```
┌────────────────────────────────────────────────────────────────────────┐
│                      OUTPUT LOGGING COMPARISON                         │
└────────────────────────────────────────────────────────────────────────┘

                           ┌─────────────────────┐
                           │   Command Output    │
                           └──────────┬──────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌───────────┐    ┌─────────────┐   ┌─────────────┐
            │  stdout   │    │  raw_output │   │ parsed_data │
            │  stderr   │    │             │   │             │
            └─────┬─────┘    └──────┬──────┘   └──────┬──────┘
                  │                 │                 │
                  └────────┬────────┘                 │
                           ▼                          │
                  ┌─────────────────┐                 │
                  │  Build Output   │◄────────────────┘
                  │  (Episode Log)  │
                  └────────┬────────┘
                           │
            ┌──────────────┼──────────────┐
            │                             │
            ▼                             ▼
   ┌─────────────────┐          ┌─────────────────┐
   │      V1         │          │       V2        │
   │                 │          │                 │
   │ build_output =  │          │ build_output =  │
   │   parsed_data   │          │   raw_output    │◄── PREFERS RAW
   │   or raw_output │          │   or parsed     │
   │                 │          │                 │
   │ ⚠️ Parsed first │          │ ✓ Raw first     │
   │    (may miss    │          │   (complete     │
   │     details)    │          │    output)      │
   └─────────────────┘          └─────────────────┘
```

---

## Complete System Architecture

### Side-by-Side Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              BENCHMARK SYSTEM ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

        V1 ARCHITECTURE                                        V2 ARCHITECTURE
        ═════════════════                                        ═════════════════

  ┌─────────────────────────┐                            ┌─────────────────────────┐
  │  run_benchmark_exploit  │                            │ run_benchmark_exploit   │
  │        .py              │                            │        _v2.py           │
  └───────────┬─────────────┘                            └───────────┬─────────────┘
              │                                                      │
              ▼                                                      ▼
  ┌─────────────────────────┐                            ┌─────────────────────────┐
  │  Config:                │                            │  Config:                │
  │  benchmark_exploit.yaml │                            │  benchmark_exploit_v2   │
  │  • --fork-retries       │                            │       .yaml             │
  │  • interactive: false   │                            │  • --retries ✓          │
  │                         │                            │  • interactive: null ✓  │
  └───────────┬─────────────┘                            └───────────┬─────────────┘
              │                                                      │
              ▼                                                      ▼
  ┌─────────────────────────┐                            ┌─────────────────────────┐
  │  Environment:           │                            │  Environment:           │
  │  foundry_parsed.py      │                            │  foundry_parsed_v2.py   │
  │  • Substring regex      │                            │  • Token-based (shlex)  │
  │    matching             │                            │    matching ✓           │
  │  • False positives      │                            │  • Accurate detection   │
  │    possible             │                            │                         │
  └───────────┬─────────────┘                            └───────────┬─────────────┘
              │                                                      │
              ▼                                                      ▼
  ┌─────────────────────────┐                            ┌─────────────────────────┐
  │  ExploitEnvironment     │                            │  ExploitEnvironment     │
  │  (V1)                   │                            │  V2                     │
  │  • Parsed output first  │                            │  • Raw output first ✓   │
  │  • Standard logging     │                            │  • Enhanced logging     │
  └───────────┬─────────────┘                            └───────────┬─────────────┘
              │                                                      │
              ▼                                                      ▼
  ┌─────────────────────────┐                            ┌─────────────────────────┐
  │  Episode Runner         │                            │  Episode Runner         │
  │  benchmark_episode.py   │                            │  benchmark_episode.py   │
  │  • Uses parsed data     │                            │  • Uses raw output ✓    │
  │  • Standard results     │                            │  • Better debugging     │
  └───────────┬─────────────┘                            └───────────┬─────────────┘
              │                                                      │
              ▼                                                      ▼
  ┌─────────────────────────┐                            ┌─────────────────────────┐
  │  JSON Output            │                            │  JSON Output            │
  │  • script: "v1"         │                            │  • script: "v2" ✓       │
  │    (incorrect meta)     │                            │    (correct meta)       │
  └─────────────────────────┘                            └─────────────────────────┘

```

---

## Test Coverage

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          TEST COVERAGE MAP                              │
└─────────────────────────────────────────────────────────────────────────┘

  Fix #1: Parser Detection
  ━━━━━━━━━━━━━━━━━━━━━━━━━
  ┌─────────────────────────────────────────────────────────────────────┐
  │ tests/environments/test_foundry_parsed_detection.py                 │
  │                                                                     │
  │ ✓ test_anvil_command_detection_v1() - Substring matching            │
  │ ✓ test_anvil_command_detection_v2() - Token-based matching          │
  │ ✓ test_false_positive_prevention() - pgrep/cat commands             │
  │ ✓ test_real_anvil_commands() - Actual anvil invocations             │
  └─────────────────────────────────────────────────────────────────────┘

  Fix #2: Anvil Readiness
  ━━━━━━━━━━━━━━━━━━━━━━━━━
  ┌─────────────────────────────────────────────────────────────────────┐
  │ tests/environments/test_foundry_wait_for_anvil_ready.py             │
  │                                                                     │
  │ ✓ test_wait_for_anvil_ready_v1() - Uses raw_output                  │
  │ ✓ test_wait_for_anvil_ready_v2() - Uses raw_output                  │
  │ ✓ test_timeout_behavior() - Both versions                           │
  └─────────────────────────────────────────────────────────────────────┘

  Fix #3: Execute() Behavior
  ━━━━━━━━━━━━━━━━━━━━━━━━━
  ┌─────────────────────────────────────────────────────────────────────┐
  │ tests/environments/test_exploit_environment_execute.py              │
  │                                                                     │
  │ ✓ test_execute_raw_vs_parsed_v1() - V1 output handling              │
  │ ✓ test_execute_raw_vs_parsed_v2() - V2 output handling              │
  │ ✓ test_raw_output_priority() - Logging preference                   │
  └─────────────────────────────────────────────────────────────────────┘

  Fix #4: Episode Utilities
  ━━━━━━━━━━━━━━━━━━━━━━━━━
  ┌─────────────────────────────────────────────────────────────────────┐
  │ tests/exploit_generation/test_benchmark_episode.py                  │
  │                                                                     │
  │ ✓ test_agent_selection_v1() - V1 agent creation                     │
  │ ✓ test_agent_selection_v2() - V2 agent creation                     │
  │ ✓ test_episode_timeout() - Timeout handling                         │
  │ ✓ test_build_output_preference() - Raw vs parsed                    │
  └─────────────────────────────────────────────────────────────────────┘

  Fix #5: Script Defaults
  ━━━━━━━━━━━━━━━━━━━━━━━━━
  ┌─────────────────────────────────────────────────────────────────────┐
  │ tests/run/test_run_benchmark_exploit_scripts.py                     │
  │                                                                     │
  │ ✓ test_v1_default_interactive() - False default                     │
  │ ✓ test_v2_default_interactive() - None default                      │
  │ ✓ test_v2_env_fallback() - Alias precedence                         │
  │ ✓ test_script_metadata() - Correct script field                     │
  └─────────────────────────────────────────────────────────────────────┘

  Fix #6: Environment Mapping
  ━━━━━━━━━━━━━━━━━━━━━━━━━
  ┌─────────────────────────────────────────────────────────────────────┐
  │ tests/environments/test_init.py                                     │
  │                                                                     │
  │ ✓ test_environment_mapping() - All aliases                          │
  │ ✓ test_exploit_foundry_v2_alias() - NEW: V2 alias ✓                 │
  │ ✓ test_environment_factory() - Factory creation                     │
  └─────────────────────────────────────────────────────────────────────┘

  Total: 28 tests passing
```

---

## Key Differences Summary

| Aspect | V1 | V2 | Fix Status |
|--------|-----|-----|------------|
| **Anvil Flag** | `--fork-retries` | `--retries` | ✅ Fixed |
| **Parser Matching** | Substring regex | Token-based (shlex) | ✅ Fixed |
| **Interactive Default** | `False` | `None` (auto-detect) | ✅ Fixed |
| **Output Preference** | Parsed first | Raw first | ✅ Fixed |
| **Environment Alias** | `exploit_foundry` | `exploit_foundry` + `exploit_foundry_v2` | ✅ Fixed |
| **Script Metadata** | Incorrect path | Correct path | ✅ Fixed |
| **Config Example** | Wrong flag | Correct flag | ✅ Fixed |

---

## Fix Impact Visualization

```
BEFORE FIXES                                    AFTER FIXES
══════════════                                  ═══════════

┌─────────────────┐                             ┌─────────────────┐
│  False Positives│                             │  Accurate       │
│  in Anvil       │                             │  Detection      │
│  Detection      │                             │                 │
│  (high)         │                             │  (eliminated)   │
└────────┬────────┘                             └────────┬────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐                             ┌─────────────────┐
│  Config Errors  │                             │  Valid Config   │
│  (wrong flags)  │                             │                 │
│  (frequent)     │                             │  (working)      │
└────────┬────────┘                             └────────┬────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐                             ┌─────────────────┐
│  Missing        │                             │  Complete       │
│  Debug Info     │                             │  Logs           │
│  (raw output)   │                             │                 │
└────────┬────────┘                             └────────┬────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐                             ┌─────────────────┐
│  ❌ UNRELIABLE  │                             │  ✅ RELIABLE    │
│  RESULTS        │                             │  RESULTS        │
└─────────────────┘                             └─────────────────┘
```

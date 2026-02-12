# Beautiful Benchmark UI

This document describes the enhanced terminal UI for the benchmark exploit V2 script.

## Features

### 🎨 Rich Terminal Interface
- **Beautiful panels** with emoji icons and color-coded status
- **Live progress tracking** showing all cases at once
- **Real-time stage indicators** for the current case
- **Docker environment status** display
- **LLM agent status** with model information
- **Detailed metrics** for completed cases

### 📊 Visual Components

1. **Configuration Panel** - Shows run settings (model, Docker image, cost limit)
2. **Progress Panel** - Table of all cases with status, stage, duration, and progress
3. **Stage Detail Panel** - Current execution stage with progress bar
4. **Docker Status Panel** - Container, RPC, volume, and network status
5. **LLM Agent Panel** - Model name and current execution status
6. **Metrics Panel** - Profit, cost, iterations for completed cases

### 🚀 Usage

```bash
# Default: Beautiful rich UI (requires TTY)
uv run scripts/run_benchmark_exploit_v2.py --index 1 --model openrouter/pony-alpha -v

# Simple mode: Plain text output
uv run scripts/run_benchmark_exploit_v2.py --index 1 --model openrouter/pony-alpha --simple

# No UI mode: Same as simple
uv run scripts/run_benchmark_exploit_v2.py --index 1 --model openrouter/pony-alpha --no-ui
```

### 🖥️ UI Auto-Detection

The UI automatically detects if stdout is a TTY:
- **TTY available** (interactive terminal): Shows beautiful Rich UI
- **No TTY** (piped/redirected): Falls back to simple output

You can override this with `--simple` or `--no-ui` flags.

## UI Components

### Progress Table
```
┌─────┬──────────────────────┬──────────────┬─────────────────┬────────────┬────────────────────┐
│  #  │ Case Name            │ Status       │ Stage           │  Duration  │ Progress           │
├─────┼──────────────────────┼──────────────┼─────────────────┼────────────┼────────────────────┤
│   1 │ waultfinance         │ ✅ SUCCESS   │ -               │     1m 40s │ ✓ Complete         │
│   2 │ bancor               │ ▶️ RUNNING   │ execution       │      45.3s │ ████████████░░ 65% │
│   3 │ creamfinance         │ ⏳ PENDING   │ -               │       0.0s │ -                  │
└─────┴──────────────────────┴──────────────┴─────────────────┴────────────┴────────────────────┘
```

### Stage Detail Panel
```
╭─────────────────────────── 🔍 Stage: execution ───────────────────────────╮
│                                                                           │
│                              🚀 Agent executing                           │
│                        Running exploit generation                         │
│                                                                           │
│                    ███████████████████░░░░░░░░░░░ 65%                     │
│                            Duration: 45.3s                                │
│                                                                           │
╰───────────────────────────────────────────────────────────────────────────╯
```

### Docker Status Panel
```
╭────────────────────────── 🐳 Docker Environment ──────────────────────────╮
│ ╭────────────────┬────────────────────────────┬──────────────────────────╮│
│ │  🐳            │ Container                  │  Ready                   ││
│ │  ⛓️             │ Anvil RPC                  │  Connected               ││
│ │  💾            │ Volume                     │  Mounted                 ││
│ │  🔌            │ Network                    │  Active                  ││
│ ╰────────────────┴────────────────────────────┴──────────────────────────╯│
╰───────────────────────────────────────────────────────────────────────────╯
```

### Metrics Panel
```
╭──────────────────────── 📈 Metrics: waultfinance ─────────────────────────╮
│ ╭──────────────────────────────────────────────┬──────────────────────────╮│
│ │ Duration                                     │ 1m 40s                   ││
│ │ Status                                       │ SUCCESS                  ││
│ │ Profit Native Token                          │ 1.500000 ETH             ││
│ │ Total Cost Usd                               │ $0.5000                  ││
│ │ Iterations                                   │ 5                        ││
│ ╰──────────────────────────────────────────────┴──────────────────────────╯│
╰───────────────────────────────────────────────────────────────────────────╯
```

## Files Created/Modified

### New Files
- `exploit_generation/benchmark_ui.py` - Beautiful UI components using Rich

### Modified Files
- `scripts/run_benchmark_exploit_v2.py` - Integrated UI with `--simple` and `--no-ui` flags

## Implementation Details

### UI State Management
```python
@dataclass
class RunState:
    run_id: str
    model_name: str
    docker_image: str
    total_cases: int
    cases: list[CaseProgress]
    current_case_index: int = -1
    # ...

@dataclass
class CaseProgress:
    name: str
    index: int
    total: int
    status: str  # pending, running, success, failed, interrupted
    stage: str
    stage_progress: float
    metrics: dict
```

### Live UI Updates
```python
class BenchmarkUI:
    def __init__(self, state: RunState):
        self.state = state
        self.live = Live(self._generate_layout(), refresh_per_second=4)

    def update(self):
        self.live.update(self._generate_layout())
```

### Stage Tracking
The UI tracks 8 distinct stages:
1. 📁 **workspace** - Setting up Foundry project
2. ⚙️ **config** - Loading agent configuration
3. 🐳 **environment** - Initializing Docker
4. ⛓️ **anvil** - Starting Anvil fork
5. 💰 **funding** - Funding player account
6. 🔨 **build** - Building Forge project
7. 🤖 **agent** - Initializing LLM agent
8. 🚀 **execution** - Running exploit generation

## Color Scheme

| Element | Color | Usage |
|---------|-------|-------|
| Header | Cyan | Titles, banners |
| Success | Green | Completed cases, profits |
| Error | Red | Failed cases, errors |
| Warning | Yellow | Warnings, pending status |
| Info | Blue | Labels, configuration |
| Highlight | Magenta | Important values |
| Dim | Gray | Secondary information |

## Requirements

The UI requires the `rich` library (already installed in the project):
```bash
pip install rich
```

## Backward Compatibility

The script maintains full backward compatibility:
- Default behavior: Beautiful UI (when TTY available)
- `--simple` flag: Plain text output like original
- `--no-ui` flag: Same as simple mode
- Non-TTY environments: Automatically use simple mode

## Example Output

### Run Start
```
╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│                    🔥 Exploit Generation Benchmark V2                        │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

                ⚙️  Run Configuration
╭────────────────┬─────────────────────────────╮
│       Run ID   │ benchmark_20260209_1200...  │
│        Model   │ openrouter/pony-alpha       │
│ Docker Image   │ yudai-base:latest           │
│       Config   │ benchmark_exploit_v2.yaml   │
│   Cost Limit   │ $20.00                      │
│  Total Cases   │ 3                           │
╰────────────────┴─────────────────────────────╯
```

### Run Summary
```
══════════════════════════════════════════════════════════════════════════════

                    🎉 ALL CASES PASSED

                  📊 Final Statistics
╭──────────────────────────────────────────┬───────────────────╮
│ Metric                                   │            Value  │
├──────────────────────────────────────────┼───────────────────┤
│ Total Cases                              │                 3 │
│ Successful                               │ [green]3[/green]             │
│ Failed                                   │ [red]0[/red]             │
│ Total Duration                           │            5m 30s │
│ Total Cost                               │           $1.2345 │
│ Total Profit                             │      5.000000 ETH │
╰──────────────────────────────────────────┴───────────────────╯
```

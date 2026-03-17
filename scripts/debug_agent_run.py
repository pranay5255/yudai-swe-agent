#!/usr/bin/env python3
"""
Debug agent runner - prints every step with timestamps.
No fancy UI, just raw output.

Usage:
    python scripts/debug_agent_run.py
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.openrouter_model import OpenRouterModel


class DebugAgent(DefaultAgent):
    """Agent that prints everything."""

    def add_message(self, role: str, content: str, **kwargs):
        """Override to print messages."""
        super().add_message(role, content, **kwargs)

        print("\n" + "=" * 80)
        print(f"MESSAGE [{role.upper()}] at {time.strftime('%H:%M:%S')}")
        print("=" * 80)
        print(content)
        print("=" * 80 + "\n")

    def query(self):
        """Override to show when querying model."""
        print(f"\n>>> Querying model (step {self.n_calls + 1}, cost so far: ${self.cost:.4f})...")
        result = super().query()
        print(f">>> Model responded (cost: ${self.cost:.4f})")
        return result

    def execute_action(self, action: dict):
        """Override to show commands being executed."""
        command = action.get("action", "")
        print(f"\n>>> EXECUTING COMMAND:")
        print(f"    {command}")
        print(f">>> Running...")

        output = super().execute_action(action)

        print(f">>> Command finished")
        print(f"    Return code: {output.get('returncode', 'N/A')}")
        output_text = output.get("output", "")
        if len(output_text) > 500:
            print(f"    Output: {len(output_text)} chars (truncated below)")
            print(f"    {output_text[:200]}...{output_text[-200:]}")
        else:
            print(f"    Output: {output_text}")

        return output


def main():
    print("\n" + "=" * 80)
    print("DEBUG AGENT RUNNER - ALL OUTPUT VISIBLE")
    print("=" * 80)

    # Simple task
    task = "List files in the current directory and show the first 20 lines of any README file."

    workspace = Path("/tmp/debug_agent_test")
    workspace.mkdir(exist_ok=True)

    # Create a test README
    (workspace / "README.md").write_text("# Test Project\n\nThis is a test.\n" * 10)

    print(f"Workspace: {workspace}")
    print(f"Task: {task}")

    # Create components
    env = LocalEnvironment(project_path=str(workspace))

    model = OpenRouterModel(
        model_name="anthropic/claude-3-haiku",  # Cheaper model for testing
        model_kwargs={"temperature": 0.0, "max_tokens": 1024},
    )

    agent = DebugAgent(
        model=model,
        env=env,
        system_template="""You are a helpful agent that executes bash commands.

Respond with EXACTLY ONE bash code block:

```bash
your_command_here
```

When done, run: `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`
""",
        instance_template="Task: {{task}}",
        step_limit=5,
        cost_limit=1.0,
    )

    print("\n" + "=" * 80)
    print("STARTING AGENT EXECUTION")
    print("=" * 80)

    try:
        result = agent.run(task=task)

        print("\n" + "=" * 80)
        print("AGENT FINISHED")
        print("=" * 80)
        print(f"Exit status: {result.get('exit_status')}")
        print(f"Total cost: ${agent.cost:.4f}")
        print(f"Total calls: {agent.n_calls}")

    except KeyboardInterrupt:
        print("\n\nInterrupted.")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

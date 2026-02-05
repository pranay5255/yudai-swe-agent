# Agent control flow

!!! note "Understanding AI agent basics"

    We also recently created a long tutorial on understanding the basics of building an AI agent: [View it here](https://minimal-agent.com).

!!! abstract "Understanding the default agent"

    * This guide shows the control flow of the default agent.
    * After this, you're ready to [remix & extend mini](cookbook.md)

The following diagram shows the control flow of the mini agent:

<div align="center">
    <img src="../../assets/mini_control_flow.svg" alt="Agent control flow" style="max-width: 600px;" />
</div>

And here is the code that implements it:

??? note "Default agent class"

    - [Read on GitHub](https://github.com/swe-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py)
    - [API reference](../reference/agents/default.md)

    ```python
    --8<-- "src/minisweagent/agents/default.py"
    ```

Essentially, `DefaultAgent.run` calls `DefaultAgent.step` in a loop until the agent has finished its task.

The `step` method is the core of the agent. It does the following:

1. Queries the model for a response based on the current messages (`DefaultAgent.query`, calling `Model.query`)
2. The model parses tool calls/actions and returns them to the agent
3. Executes the actions in the environment (`DefaultAgent.execute_action`, calling `Environment.execute`)
4. Renders observation messages via `Model.format_observation_messages`
5. Adds the observations to the messages

The interesting bit is how we handle error conditions and the finish condition:
This uses `InterruptAgentFlow` exceptions to control the loop.

- `FormatError` and `UserInterruption` add a new user message and continue the loop.
- `Submitted` and `LimitsExceeded` add a message and terminate the run.

The `DefaultAgent.run` method catches these exceptions and handles them accordingly.

```python
while True:
    try:
        self.step()
    except InterruptAgentFlow as e:
        self.add_message("user", str(e))
        if isinstance(e, (FormatError, UserInterruption)):
            continue
        return {"exit_status": type(e).__name__, "submission": str(e)}
```

Using exceptions for the control flow is a lot easier than passing around flags and states, especially when extending or subclassing the agent.

{% include-markdown "_footer.md" %}

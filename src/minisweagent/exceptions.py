"""Exceptions used to control agent flow in mini-swe-agent v2."""

from __future__ import annotations


class InterruptAgentFlow(Exception):
    """Base exception for agent control flow.

    These exceptions are used to interrupt the agent loop (e.g., format errors,
    limits exceeded, submission) while still allowing the agent to continue or
    exit gracefully.
    """

    def __init__(self, message: str = "", *, extra: dict | None = None):
        super().__init__(message)
        self.extra = extra or {}


class FormatError(InterruptAgentFlow):
    """Raised when the LM's output is not in the expected format."""


class LimitsExceeded(InterruptAgentFlow):
    """Raised when the agent has reached its cost or step limit."""


class Submitted(InterruptAgentFlow):
    """Raised when the LM declares that the agent has finished its task."""


class UserInterruption(InterruptAgentFlow):
    """Raised when a user manually interrupts the agent."""


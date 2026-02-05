from __future__ import annotations

import litellm


def abort_exceptions() -> tuple[type[BaseException], ...]:
    """Exceptions that should not be retried."""
    return (
        litellm.exceptions.UnsupportedParamsError,
        litellm.exceptions.NotFoundError,
        litellm.exceptions.PermissionDeniedError,
        litellm.exceptions.ContextWindowExceededError,
        litellm.exceptions.APIError,
        litellm.exceptions.AuthenticationError,
        KeyboardInterrupt,
    )


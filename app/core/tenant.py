"""Tenant context and resolution helpers for multi-tenancy."""

from __future__ import annotations

import contextvars

# Global context variable holding the current tenant_id for the execution context
_tenant_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tenant_context", default="default"
)

DEFAULT_TENANT_ID = "default"


def set_current_tenant_id(tenant_id: str) -> contextvars.Token[str]:
    """Set the tenant ID in the current async context."""
    return _tenant_context.set(tenant_id)


def reset_current_tenant_id(token: contextvars.Token[str]) -> None:
    """Reset the tenant ID context variable using the given token."""
    _tenant_context.reset(token)


def get_tenant_context() -> str:
    """Retrieve the tenant ID from the current async context."""
    return _tenant_context.get()

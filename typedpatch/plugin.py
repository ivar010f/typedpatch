"""Pytest plugin providing the `typedpatch` fixture."""

import pytest

from .typed_patch import TypedPatch


@pytest.fixture
def typedpatch(monkeypatch: pytest.MonkeyPatch) -> TypedPatch:
    """Get a `TypedPatch` over the `monkeypatch` fixture."""
    return TypedPatch(monkeypatch)

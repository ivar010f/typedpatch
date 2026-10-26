"""Typed patch targets for monkeypatch and unittest.mock."""

from .patch_target import PatchTarget
from .typed_patch import TypedPatch

__all__ = ["PatchTarget", "TypedPatch"]

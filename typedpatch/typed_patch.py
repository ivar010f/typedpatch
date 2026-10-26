"""`MonkeyPatch` wrapper taking `PatchTarget` targets without `str()`."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

import pytest

from .patch_target import PatchTarget

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass(frozen=True)
class TypedPatch:
    """Patch through a `MonkeyPatch` that only takes a `PatchTarget` as target.

    A target is typed as the union of the real object and `PatchTarget`,
    so the type checker sees `object` here,
    and a dotted path or an object and name pair raises `TypeError`.
    The wrapped `MonkeyPatch` undoes the patches.

    Patch only within a block with `context()`:

    >>> import time
    >>> from typedpatch import PatchTarget
    >>> with TypedPatch.context() as patch:
    ...     patch.setattr(PatchTarget(time).time, lambda: 42.0)
    ...     time.time()
    42.0
    >>> time.time() != 42.0
    True
    """

    monkey: pytest.MonkeyPatch

    @classmethod
    @contextmanager
    def context(cls) -> Generator[Self]:
        """Get a `TypedPatch` whose patches are undone when the block exits."""
        with pytest.MonkeyPatch.context() as monkey:
            yield cls(monkey)

    def setattr(self, target: object, value: object, *, raising: bool = True) -> None:
        """Set the target to `value` until the patches are undone."""
        self.monkey.setattr(str(require_target(target)), value, raising=raising)

    def delattr(self, target: object, *, raising: bool = True) -> None:
        """Delete the target until the patches are undone."""
        self.monkey.delattr(str(require_target(target)), raising=raising)


def require_target(target: object) -> PatchTarget:
    """Get `target` as a `PatchTarget`, or raise `TypeError`."""
    if not isinstance(target, PatchTarget):
        msg = f"Expected a PatchTarget, got {type(target).__name__}"
        raise TypeError(msg)
    return target

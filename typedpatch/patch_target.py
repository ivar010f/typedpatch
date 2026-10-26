"""Typed symbolic references for `monkeypatch` and `mock.patch`."""

from __future__ import annotations

import functools
import inspect
import sys
from types import FunctionType, MethodType, ModuleType
from typing import TYPE_CHECKING, Any, Self, cast
from unittest import mock

if TYPE_CHECKING:
    from collections.abc import Callable


class PatchTarget:
    """Typed symbolic references for `monkeypatch` and `mock.patch`.

    Get a dot-path reference to a static object.

    >>> target = PatchTarget(PatchTarget)
    >>> str(target)
    'typedpatch.patch_target.PatchTarget'

    Get a `mock.call()` invocation for comparing calls to mocked objects.

    >>> from unittest import mock
    >>> with mock.patch(str(target)) as mocked_target:
    ...     # <exercise some code interacting with mocked_target>
    ...     _ = mocked_target("mocked_call_arg")
    >>> assert mocked_target.mock_calls == [target("mocked_call_arg")]
    """

    __slots__ = ("_path",)
    _path: str

    def __new__[T](cls, target: T) -> T | Self:
        """Target a module, class or function.

        Returning `T | Self` types the target as the real object,
        so type checkers complete and check its attributes.
        """
        return cls._from_path(path_of(target))

    @classmethod
    def for_instance[T](cls, target: type[T]) -> T | Self:
        """Target a class, with attributes typed as on its instances."""
        return cls._from_path(path_of(target))

    @classmethod
    def unbind_method[**P, R](cls, method: Callable[P, R]) -> Callable[P, R]:
        """Unbind a method from a test stub class for patching a target method.

        A classmethod stays a classmethod,
        a staticmethod stays a staticmethod,
        and a method bound to an instance becomes its plain function.
        A method accessed on the class is already a plain function.

        Staticmethods are found through the stub class's qualified name,
        so a stub class defined inside a function patches them as methods.
        """
        match method:
            case MethodType(__self__=type()):
                return cast("Any", classmethod(method.__func__))
            case MethodType():
                return cast("Any", method.__func__)
            case FunctionType() if is_staticmethod(method):
                return cast("Any", staticmethod(method))
            case _:
                return method

    @classmethod
    def _from_path(cls, *attr_chain: str) -> Self:
        self = object.__new__(cls)
        self._path = ".".join(attr_chain)
        return self

    def __getattr__(self, attr: str) -> PatchTarget:
        # Keep protocol lookups such as `__deepcopy__` from becoming targets.
        if attr.startswith("__"):
            raise AttributeError(attr)
        return PatchTarget._from_path(self._path, attr)

    def __call__(self, *args: Any, **kwargs: Any) -> mock._Call:
        """Build the `mock.call` expected for calling the target."""
        return mock.call(*args, **kwargs)

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return f"PatchTarget({self._path!r})"


def path_of(target: object) -> str:
    """Get the dotted import path of a module, class or function."""
    if isinstance(target, ModuleType):
        return target.__name__
    return f"{target.__module__}.{getattr(target, '__qualname__')}"  # noqa: B009  # object lacks __qualname__


def is_staticmethod(function: FunctionType) -> bool:
    """Check if `function` is defined as a staticmethod of its class."""
    *owner_path, name = function.__qualname__.split(".")
    owner = functools.reduce(
        lambda owner, attr: getattr(owner, attr, None),
        owner_path,
        sys.modules.get(function.__module__),
    )
    return isinstance(inspect.getattr_static(owner, name, None), staticmethod)

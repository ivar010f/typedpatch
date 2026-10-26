"""Tests for `PatchTarget` with `mock` and the `typedpatch` fixture."""

import time
from dataclasses import dataclass
from typing import Self, override
from unittest import mock

import pytest

from typedpatch import PatchTarget, TypedPatch


def double(arg: float) -> float:
    """Double the argument; the patch target."""
    return arg * 2


def mocked_double(arg: float) -> float:
    """Replace `double` in tests."""
    return arg + 1


@dataclass(frozen=True)
class Multiplier:
    """Multiply by a wrapped factor; the class patch target."""

    factor: float

    def multiply(self, other: float) -> float:
        """Multiply `other` by the wrapped factor."""
        return self.factor * other

    @classmethod
    def unit(cls) -> Self:
        """Get the multiplier that keeps values unchanged."""
        return cls(1)

    @staticmethod
    def symbol() -> str:
        """Get the operator symbol."""
        return "*"


@dataclass(frozen=True)
class MultiplierStub(Multiplier):
    """Stub implementing patches for `Multiplier` in its class body."""

    @override
    def multiply(self, other: float) -> float:
        return self.factor + other

    @override
    @classmethod
    def unit(cls) -> Self:
        return cls(2)

    @override
    @staticmethod
    def symbol() -> str:
        return "+"


def mocked_multiply(self: Multiplier, other: float) -> float:
    """Replace `Multiplier.multiply` in tests."""
    return MultiplierStub(self.factor).multiply(other)


def test_patch_target_function():
    """Mocked calls of a function compare equal to target calls."""
    target = PatchTarget(double)
    with mock.patch(str(target)) as mocked_target:
        # <exercise some code interacting with mocked_target>
        _ = mocked_target(5)

    assert mocked_target.mock_calls == [target(5)]


def test_patch_target_class():
    """Mocked method calls compare equal to instance target calls."""
    target = PatchTarget.for_instance(Multiplier)
    with mock.patch(str(target)) as mocked_target:
        # <exercise some code interacting with mocked_target>
        _ = mocked_target.multiply(5)

    assert mocked_target.multiply.mock_calls == [target.multiply(5)]


def test_patch_target_module_attribute():
    """Mocked calls of a module attribute compare equal to target calls."""
    target = PatchTarget(time).time
    with mock.patch(str(target)) as mocked_target:
        # <exercise some code interacting with mocked_target>
        _ = time.time()

    assert mocked_target.mock_calls == [target()]


def test_typedpatch_function(typedpatch: TypedPatch):
    """A function target patches the function."""
    typedpatch.setattr(PatchTarget(double), mocked_double)

    assert double(5) == mocked_double(5)


def test_typedpatch_method(typedpatch: TypedPatch):
    """A method target patches the method."""
    typedpatch.setattr(PatchTarget(Multiplier).multiply, mocked_multiply)

    multiplier = Multiplier(2)

    assert multiplier.multiply(5) == mocked_multiply(multiplier, 5)


def test_typedpatch_mock_function(typedpatch: TypedPatch):
    """A mock set on a function target records target calls."""
    target = PatchTarget(double)
    mocked_target = mock.Mock(return_value=0.0)
    typedpatch.setattr(target, mocked_target)

    _ = double(5)
    _ = double(arg=5)

    assert mocked_target.mock_calls == [target(5), target(arg=5)]


def test_typedpatch_mock_method(typedpatch: TypedPatch):
    """A mock set on a method target records calls without `self`."""
    target = PatchTarget.for_instance(Multiplier).multiply
    mocked_target = mock.Mock(return_value=0.0)
    typedpatch.setattr(target, mocked_target)

    _ = Multiplier(2).multiply(5)

    assert mocked_target.call_args == target(5)


def test_typedpatch_stub_class(typedpatch: TypedPatch):
    """Methods of a stub class patch the target class methods."""
    typedpatch.setattr(
        PatchTarget(Multiplier).multiply,
        PatchTarget.unbind_method(MultiplierStub.multiply),
    )
    typedpatch.setattr(
        PatchTarget(Multiplier).unit,
        PatchTarget.unbind_method(MultiplierStub.unit),
    )
    typedpatch.setattr(
        PatchTarget(Multiplier).symbol,
        PatchTarget.unbind_method(MultiplierStub.symbol),
    )

    assert Multiplier(2).multiply(5) == 2 + 5
    assert Multiplier.unit() == Multiplier(2)
    assert Multiplier.symbol() == "+"


def test_typedpatch_module_attribute(typedpatch: TypedPatch):
    """A module attribute target patches the attribute."""
    typedpatch.setattr(PatchTarget(time).time, lambda: 42.0)

    assert time.time() == 42.0  # noqa: PLR2004


def test_typedpatch_delattr(typedpatch: TypedPatch):
    """A method target deletes the method."""
    typedpatch.delattr(PatchTarget(Multiplier).multiply)

    assert not hasattr(Multiplier, "multiply")


def test_typedpatch_undo(typedpatch: TypedPatch):
    """Undoing the wrapped `MonkeyPatch` restores the patched attribute."""
    typedpatch.setattr(PatchTarget(double), mocked_double)

    typedpatch.monkey.undo()

    assert double(5) == 10  # noqa: PLR2004


@pytest.mark.parametrize("target", ["tests.test_patch_target.double", double])
def test_typedpatch_rejects_other_targets(typedpatch: TypedPatch, target: object):
    """A dotted path or a plain object is rejected."""
    with pytest.raises(TypeError, match="Expected a PatchTarget"):
        typedpatch.setattr(target, mocked_double)

    with pytest.raises(TypeError, match="Expected a PatchTarget"):
        typedpatch.delattr(target)

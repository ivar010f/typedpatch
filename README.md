# typedpatch
Proper typing for `pytest` `monkeypatch` and `unittest.mock`

Patch targets in tests are usually dotted strings,
such as `monkeypatch.setattr("time.time", ...)`.
Type checkers and IDEs cannot follow them,
so a renamed or moved function breaks the test only when it runs.

`PatchTarget` builds that path from the real object instead.
The type checker then completes its attributes,
and flags typos and renames like any other attribute access.

## Installation

```bash
uv add --dev typedpatch
```

## Quick start

```python
import time

from typedpatch import PatchTarget, TypedPatch


def test_fixed_time(typedpatch: TypedPatch):
    typedpatch.setattr(PatchTarget(time).time, lambda: 42.0)

    assert time.time() == 42.0
```

A typo such as `PatchTarget(time).tme` fails type checking:

```text
Attribute `tme` is not defined on `<module 'time'>` in union `<module 'time'> | PatchTarget`
```

## Patch targets

Get a target from a module, class or function,
then follow attributes as on the real object:

- `PatchTarget(module).attr` targets a module attribute,
  such as `time.time`.
- `PatchTarget(function)` targets a function by its qualified name.
- `PatchTarget(cls).method` targets a class attribute,
  typed as accessed on the class.
- `PatchTarget.for_instance(cls).method` targets the same class attribute,
  typed as accessed on an instance,
  so methods are bound and properties have their value type.

`str(target)` is the dotted path, such as `"time.time"`.
Calling a target builds the `mock.call` expected for calling it.

A target is typed as the union of the real object and `PatchTarget`.
Python has no intersection type,
so APIs that require a `str` path need `str(target)`.

## typedpatch fixture

The `typedpatch` fixture wraps the `monkeypatch` fixture
in a `TypedPatch` that takes a `PatchTarget` without `str()`.
pytest loads it once `typedpatch` is installed,
and `monkeypatch` undoes the patches at teardown.

- `typedpatch.setattr(target, value)` sets the target.
- `typedpatch.delattr(target)` deletes the target.
- `TypedPatch.context()` patches only within a `with` block.
- `TypedPatch(monkeypatch)` wraps any other `MonkeyPatch`.

```python
with TypedPatch.context() as patch:
    patch.setattr(PatchTarget(time).time, lambda: 42.0)
```

Targets are typed as the real object,
so the type checker cannot reject a dotted path or a plain object here.
`TypedPatch` raises `TypeError` for anything but a `PatchTarget`.

## Stub classes

Implement patches in the body of a stub class,
then unbind its methods to patch the target class:

```python
from dataclasses import dataclass
from typing import Self, override

from typedpatch import PatchTarget, TypedPatch


@dataclass(frozen=True)
class Multiplier:
    factor: float

    def multiply(self, other: float) -> float:
        return self.factor * other

    @classmethod
    def unit(cls) -> Self:
        return cls(1)


@dataclass(frozen=True)
class MultiplierStub(Multiplier):
    @override
    def multiply(self, other: float) -> float:
        return self.factor + other

    @override
    @classmethod
    def unit(cls) -> Self:
        return cls(2)


def test_stub(typedpatch: TypedPatch):
    typedpatch.setattr(
        PatchTarget(Multiplier).multiply,
        PatchTarget.unbind_method(MultiplierStub.multiply),
    )
    typedpatch.setattr(
        PatchTarget(Multiplier).unit,
        PatchTarget.unbind_method(MultiplierStub.unit),
    )

    assert Multiplier(2).multiply(5) == 7
    assert Multiplier.unit() == Multiplier(2)
```

`PatchTarget.unbind_method` returns the value to set on the target class:
a `classmethod` stays a `classmethod`,
a `staticmethod` stays a `staticmethod`,
and a method bound to an instance becomes its plain function.
It finds `staticmethod`s through the stub class's qualified name,
so define stub classes with `staticmethod`s at module level.

## monkeypatch and unittest.mock

Pass `str(target)` to the dotted-path form of `monkeypatch`:

```python
monkeypatch.setattr(str(PatchTarget(time).time), lambda: 42.0)
monkeypatch.delattr(str(PatchTarget(Multiplier).multiply))
```

Pass `str(target)` to `mock.patch`,
and call the target to build the expected `mock.call`:

```python
from unittest import mock

target = PatchTarget.for_instance(Multiplier)
with mock.patch(str(target)) as mocked_target:
    mocked_target.multiply(5)

assert mocked_target.multiply.mock_calls == [target.multiply(5)]
```

Without `str()`, type checkers reject the target:

```text
Argument `(() -> float) | PatchTarget` is not assignable to parameter `target` with type `str`
```

Set a `mock.Mock` on a target with the `typedpatch` fixture,
and compare its calls the same way:

```python
def double(arg: float) -> float:
    return arg * 2


def test_mock_function(typedpatch: TypedPatch):
    target = PatchTarget(double)
    mocked_target = mock.Mock(return_value=0.0)
    typedpatch.setattr(target, mocked_target)

    double(5)
    double(arg=5)

    assert mocked_target.mock_calls == [target(5), target(arg=5)]
```

A `Mock` set on a class is not a descriptor,
so it records method calls without `self`:

```python
def test_mock_method(typedpatch: TypedPatch):
    target = PatchTarget.for_instance(Multiplier).multiply
    mocked_target = mock.Mock(return_value=0.0)
    typedpatch.setattr(target, mocked_target)

    Multiplier(2).multiply(5)

    assert mocked_target.call_args == target(5)
```

## Type checkers

The test suite checks that `pyrefly` and `ty` both flag typos in targets.
Attributes starting with `__` cannot be targets,
so protocol lookups such as `copy.deepcopy` keep working.

## Development

```bash
just deps   # install dependencies
just lint   # ruff, pyrefly and ty, with warnings as errors
just test   # unit tests and doctests
```

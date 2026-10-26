"""Tests that type checkers flag typos in `PatchTarget` attribute chains."""

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
BIN = Path(sys.executable).parent

# Lines ending in `# typo` must be reported, and no other line.
SNIPPET = """\
import time

from _pytest.monkeypatch import MonkeyPatch

from typedpatch import PatchTarget, TypedPatch


class Multiplier:
    def multiply(self, other: float) -> float:
        return other


def patch():
    PatchTarget(time).time
    PatchTarget(time).tme  # typo
    PatchTarget(Multiplier).multiply
    PatchTarget(Multiplier).multiplyy  # typo
    PatchTarget.for_instance(Multiplier).multiply
    PatchTarget.for_instance(Multiplier).multiplyy  # typo
"""

CHECKERS: dict[str, Callable[[Path], list[str]]] = {
    "pyrefly": lambda path: [
        str(BIN / "pyrefly"),
        "check",
        "--config",
        str(ROOT / "pyproject.toml"),
        "--output-format",
        "min-text",
        str(path),
    ],
    "ty": lambda path: [
        str(BIN / "ty"),
        "check",
        "--python",
        sys.prefix,
        "--output-format",
        "concise",
        str(path),
    ],
}


@pytest.mark.parametrize("checker", CHECKERS)
def test_typecheckers_flag_typos(checker: str, tmp_path: Path):
    """The checker reports exactly the lines marked as typos."""
    path = tmp_path / "snippet.py"
    path.write_text(SNIPPET)

    result = subprocess.run(  # noqa: S603  # trusted checker binaries
        CHECKERS[checker](path),
        capture_output=True,
        text=True,
        check=False,
    )

    assert error_lines(result.stdout, path) == typo_lines(SNIPPET), result.stdout


def error_lines(output: str, path: Path) -> set[int]:
    """Get the line numbers of diagnostics for `path`."""
    return {int(n) for n in re.findall(rf"{re.escape(path.name)}:(\d+):", output)}


def typo_lines(snippet: str) -> set[int]:
    """Get the line numbers marked `# typo`."""
    return {
        n
        for n, line in enumerate(snippet.splitlines(), start=1)
        if line.endswith("# typo")
    }

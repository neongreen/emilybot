"""Check a command's JavaScript before storing it, using the executor's own wrap and compile path."""

import asyncio
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from emilybot.execute.executor import kill_and_reap

VALIDATOR_SCRIPT = "js-executor/validate.ts"
VALIDATOR_TIMEOUT = 10.0


@dataclass(frozen=True)
class InvalidCode:
    """The code does not parse or compile."""

    error: str
    line: int | None = None
    column: int | None = None

    def describe(self) -> str:
        if self.line is not None and self.column is not None:
            return f"line {self.line}, column {self.column}: {self.error}"
        return self.error


class ValidatorFailed(Exception):
    """The validator itself failed; nothing is known about the code."""


async def validate_command_code(code: str) -> InvalidCode | None:
    """Return None if `code` can be stored as a command's `run`, or why it cannot.

    The code is parsed, wrapped and compiled exactly as when the command runs, but never
    executed. Imports are not resolved (the validator has no network access) and
    referenced commands need not exist.

    Raises:
        ValidatorFailed: if the validator could not give an answer.
    """
    deno = shutil.which("deno")
    if not deno:
        raise ValidatorFailed("Deno CLI not found in PATH")
    process = await asyncio.create_subprocess_exec(
        deno,
        "run",
        "--quiet",
        "--allow-read=js-executor/,node_modules",
        "--allow-env=QTS_DEBUG,LOG_LEVEL,DEBUG",
        VALIDATOR_SCRIPT,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=Path.cwd(),
        env={"NO_COLOR": "1"},
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(code.encode("utf-8")), timeout=VALIDATOR_TIMEOUT
        )
    except asyncio.TimeoutError:
        await kill_and_reap(process)
        raise ValidatorFailed("validator timed out") from None
    except BaseException:
        await asyncio.shield(kill_and_reap(process))
        raise

    try:
        result: object = json.loads(stdout)
    except json.JSONDecodeError:
        result = None
    if process.returncode != 0 or not isinstance(result, dict):
        raise ValidatorFailed(stderr.decode("utf-8", "replace").strip()[:500])
    result = cast(dict[str, object], result)
    if result.get("ok") is True:
        return None
    line, column = result.get("line"), result.get("column")
    return InvalidCode(
        error=str(result.get("error")),
        line=line if isinstance(line, int) else None,
        column=column if isinstance(column, int) else None,
    )

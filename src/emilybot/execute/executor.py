"""Core JavaScript executor using Deno CLI subprocess."""

import asyncio
import json
import logging
import shlex
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import time
from tempfile import TemporaryDirectory
from typing import Literal, Tuple, TypedDict, cast

from emilybot.execute.context import Context


class CommandData(TypedDict):
    """Data for a command in the global context. Has to match the TypeScript CommandData type."""

    name: str  # Command name
    content: str  # Command content
    run: str | None  # JavaScript code to execute when command is run


class ExecutionResult(TypedDict):
    """Result of JavaScript execution."""

    success: bool
    output: str  # Console.log output
    error: str | None  # Error message if failed (optional)


# Why execution failed. Must match `ErrorKind` in js-executor/types.ts.
ErrorType = Literal["timeout", "memory", "output", "syntax", "runtime"]


@dataclass
class JSExecutionError(Exception):
    """Exception raised when JavaScript execution fails."""

    error_type: ErrorType
    message: str


class _ExecutorOutput(TypedDict, total=False):
    """What js-executor/main.ts prints to stdout."""

    success: bool
    output: str
    value: str | None
    error: str
    kind: ErrorType
    timings: dict[str, float]


TIMEOUT_MESSAGE = "⏱️ JavaScript execution timed out ({limit}s limit)"
BACKSTOP_MESSAGE = "⏱️ The JavaScript executor did not respond in time"
OUTPUT_MESSAGE = "📜 JavaScript output exceeded the 1 MiB limit"
MEMORY_MESSAGE = "💾 JavaScript execution exceeded memory limits"


class JavaScriptExecutor:
    """Executes JavaScript code in a fresh Deno process per call.

    Concurrency is not limited here; callers that serve users go through
    `emilybot.execute.admission`.
    """

    def __init__(self, *, timeout: float = 5.0, startup_allowance: float = 10.0):
        """Initialize the JavaScript executor.

        Args:
            timeout: Elapsed-time budget for user code in seconds, enforced inside
                the sandbox. It covers nested commands and import fetches, and
                excludes process startup.
            startup_allowance: Extra wall-clock time on top of `timeout` before the
                Deno process is killed. This backstop catches a stuck process; it is
                a safety bound, not a guarantee that startup always fits.
        """
        self.timeout = timeout
        self.backstop = timeout + startup_allowance
        deno_path = shutil.which("deno")
        if not deno_path:
            raise FileNotFoundError("Deno CLI not found in PATH")
        self.deno_path = deno_path
        self.executor_script = "js-executor/main.ts"

    async def execute(
        self,
        code: str,
        context: Context,
        commands: list[CommandData] = [],
    ) -> Tuple[bool, str, str | None]:
        """Execute JavaScript code with context and available commands.

        Returns:
            Tuple of (success: bool, output: str, result: str)
            - If success=True, output contains console.log output
            - If success=False, output contains a user-facing error message
        """
        try:
            # XXX: ctx left for backwards compatibility, will remove later
            fields_json = json.dumps({**context.as_json(), "ctx": context.as_json()})
            commands_json = json.dumps(commands)

            DEBUG = os.getenv("DEBUG")
            with TemporaryDirectory(
                delete=DEBUG != "1" and DEBUG != "true"
            ) as temp_dir:
                logging.debug(f"Created temporary directory: {temp_dir}")
                temp_path = Path(temp_dir)
                fields_path = temp_path / "fields.json"
                commands_path = temp_path / "commands.json"
                fields_path.write_text(fields_json)
                commands_path.write_text(commands_json)

                cmd = [
                    self.deno_path,
                    "run",
                    "--quiet",
                    "--allow-env=QTS_DEBUG,LOG_LEVEL,DEBUG",  # 'LOG_LEVEL' enables logs in the executor, 'QTS_DEBUG' is used by the QuickJS runtime, 'DEBUG' is used by the executor
                    f"--allow-read=js-executor/,node_modules,{temp_path}",
                    # Must match the allowed hosts in js-executor/imports.ts
                    "--allow-net=esm.sh,jsr.io,registry.npmjs.org",
                    self.executor_script,
                    f"--fieldsFile={str(fields_path)}",
                    f"--commandsFile={str(commands_path)}",
                    f"--timeoutMs={int(self.timeout * 1000)}",
                    code,
                ]

                started = time.monotonic()
                ran = await self._run_deno(cmd)
                total_ms = (time.monotonic() - started) * 1000
                if ran is None:
                    logging.warning(f"Deno process hit the {self.backstop}s backstop")
                    return False, BACKSTOP_MESSAGE, None
                stdout, stderr, returncode = ran

            stdout_text = stdout.decode("utf-8").strip() if stdout else ""
            stderr_text = stderr.decode("utf-8").strip() if stderr else ""
            logging.debug(f"Deno stderr: {stderr_text}")
            logging.debug(f"Deno stdout: {stdout_text[:2000]}")

            try:
                parsed: object = json.loads(stdout_text)
            except json.JSONDecodeError:
                parsed = None
            if not isinstance(parsed, dict):
                # The executor failed before running user code (bad input, crash)
                return (
                    False,
                    f"❌ JavaScript execution failed: {stderr_text or 'Unknown execution error'}",
                    None,
                )

            result = cast(_ExecutorOutput, parsed)
            timings = result.get("timings") or {}
            logging.info(
                "JS execution: total %.0f ms, bootstrap %.0f ms, user code %.0f ms",
                total_ms,
                timings.get("bootstrapMs", -1),
                timings.get("userMs", -1),
            )

            if returncode == 0 and result.get("success"):
                return True, result.get("output", ""), result.get("value")
            return (
                False,
                self._error_message(result.get("kind"), result.get("error")),
                None,
            )

        except FileNotFoundError:
            return False, f"❌ Deno executable not found at: {self.deno_path}", None
        except (TypeError, ValueError) as e:
            return False, f"❌ Failed to encode context as JSON: {e}", None
        except Exception as e:
            logging.error(f"Unexpected error in JavaScript execution: {e}")
            return False, f"❌ Unexpected execution error: {e}", None

    def _error_message(self, kind: ErrorType | None, error: str | None) -> str:
        """User-facing message for a failed execution."""
        error = error or "Unknown execution error"
        if kind == "timeout":
            return TIMEOUT_MESSAGE.format(limit=self.timeout)
        elif kind == "output":
            return OUTPUT_MESSAGE
        elif kind == "memory":
            return MEMORY_MESSAGE
        elif kind == "syntax":
            return f"❌ JavaScript syntax error: {error}"
        else:
            return f"⚠️ JavaScript runtime error: {error}"

    async def _run_deno(self, cmd: list[str]) -> tuple[bytes, bytes, int | None] | None:
        """Run the executor process.

        Returns (stdout, stderr, returncode), or None if the backstop killed it.
        The process is killed and reaped on the backstop and on cancellation.
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path.cwd(),
            env={"NO_COLOR": "1"},
        )
        logging.debug(f"Deno command: {shlex.join(cmd)}")
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.backstop
            )
        except asyncio.TimeoutError:
            await kill_and_reap(process)
            return None
        except BaseException:
            # Cancellation (or anything else): never leave the child running
            await asyncio.shield(kill_and_reap(process))
            raise
        return stdout, stderr, process.returncode


async def kill_and_reap(process: asyncio.subprocess.Process) -> None:
    try:
        process.kill()
    except ProcessLookupError:
        pass  # Already exited
    await process.wait()

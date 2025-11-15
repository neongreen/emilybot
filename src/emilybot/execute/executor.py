"""Core JavaScript executor using Deno CLI subprocess."""

import asyncio
import json
import logging
import shlex
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from typing import Tuple, TypedDict, Literal

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


# Error type literal
ErrorType = Literal["memory", "syntax", "runtime"]


@dataclass
class JSExecutionError(Exception):
    """Exception raised when JavaScript execution fails."""

    error_type: ErrorType
    message: str


class JavaScriptExecutor:
    """Executes JavaScript code using Deno CLI subprocess with timeout and error handling."""

    def __init__(self, *, timeout: float = 5.0):
        """Initialize the JavaScript executor.

        Args:
            timeout: Maximum execution time in seconds
        """
        self.timeout = timeout
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
            - If success=False, output contains error message

        Raises:
            JSExecutionError: When execution fails with specific error types
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

                # Build command
                cmd = [
                    self.deno_path,
                    "run",
                    "--quiet",
                    "--allow-env=QTS_DEBUG,LOG_LEVEL,DEBUG",  # 'LOG_LEVEL' enables logs in the executor, 'QTS_DEBUG' is used by the QuickJS runtime, 'DEBUG' is used by the executor
                    f"--allow-read=js-executor/,node_modules,{temp_path}",
                    "--allow-net=esm.sh",
                    self.executor_script,
                    f"--fieldsFile={str(fields_path)}",
                    f"--commandsFile={str(commands_path)}",
                    code,
                ]

                # Execute with timeout
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=Path.cwd(),
                    env={"NO_COLOR": "1"},
                )

                try:
                    logging.info("Starting Deno process")
                    logging.debug(f"Deno command: {shlex.join(cmd)}")
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    # Kill the process if it's still running
                    logging.debug("Deno process timed out, killing it")
                    try:
                        process.kill()
                        await process.wait()
                    except ProcessLookupError:
                        pass  # Process already terminated
                    return (
                        False,
                        f"⏱️ JavaScript execution timed out ({self.timeout}s limit)",
                        None,
                    )

            # Decode output
            stdout_text = stdout.decode("utf-8").strip() if stdout else ""
            stderr_text = stderr.decode("utf-8").strip() if stderr else ""

            logging.debug(f"Deno stderr: {stderr_text}")
            logging.debug(f"Deno stdout: {stdout_text}")

            # Check exit code and classify errors
            if process.returncode == 0:
                parsed = json.loads(stdout_text)
                return True, parsed.get("output", ""), parsed.get("value", None)
            else:
                # Classify error based on stderr content
                error_type = self._classify_error(stderr_text)
                error_message = stderr_text or "Unknown execution error"

                # For user-facing errors, return a clean message
                if error_type == "memory":
                    return False, "💾 JavaScript execution exceeded memory limits", None
                elif error_type == "syntax":
                    return (
                        False,
                        f"❌ JavaScript syntax error: {stderr_text}",
                        None,
                    )
                elif error_type == "runtime":
                    return (
                        False,
                        f"⚠️ JavaScript runtime error: {stderr_text}",
                        None,
                    )
                else:
                    return (
                        False,
                        f"❌ JavaScript execution failed: {error_message}",
                        None,
                    )

        except FileNotFoundError:
            return False, f"❌ Deno executable not found at: {self.deno_path}", None
        except (TypeError, ValueError) as e:
            return False, f"❌ Failed to encode context as JSON: {e}", None
        except JSExecutionError:
            # Re-raise JSExecutionError as-is
            raise
        except Exception as e:
            logging.error(f"Unexpected error in JavaScript execution: {e}")
            return False, f"❌ Unexpected execution error: {e}", None

    def _classify_error(self, stderr: str) -> str:
        """Classify error type based on stderr content.

        Args:
            stderr: Standard error output from Deno process

        Returns:
            Error type: "timeout", "memory", "syntax", or "runtime"
        """
        stderr_lower = stderr.lower()

        if "memory" in stderr_lower or "out of memory" in stderr_lower:
            return "memory"
        elif "syntaxerror" in stderr_lower or "syntax error" in stderr_lower:
            return "syntax"
        else:
            return "runtime"

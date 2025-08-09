"""JavaScript execution service using Deno CLI subprocess."""

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from typing import Any, Tuple, TypedDict, Literal


# Type definitions matching TypeScript context types

# TODO: autogenerate?


@dataclass
class CtxUser:
    id: str  # instead of 'int' because in JS it overflows 'number'
    name: str


@dataclass
class CtxServer:
    id: str


@dataclass
class CtxMessage:
    text: str


@dataclass
class Context:
    message: CtxMessage
    user: CtxUser
    server: CtxServer | None

    def as_json(self) -> dict[str, Any]:
        """Serialize Context to JSON string."""
        return {
            "message": self.message.__dict__,
            "user": self.user.__dict__,
            "server": self.server.__dict__ if self.server else None,
        }


def run_code_context(code: str) -> Context:
    return Context(
        message=CtxMessage(text=f".run {code}"),
        user=CtxUser(id="1", name="Test user"),
        server=None,
    )


class CommandData(TypedDict):
    """Data for a command in the global context."""

    name: str  # Command name
    content: str  # Command content
    run: str | None  # JavaScript code to execute when command is run


class ExecutionResult(TypedDict):
    """Result of JavaScript execution."""

    success: bool
    output: str  # Console.log output
    error: str | None  # Error message if failed (optional)


# Error type literal
ErrorType = Literal["timeout", "memory", "syntax", "runtime"]


@dataclass
class JSExecutionError(Exception):
    """Exception raised when JavaScript execution fails."""

    error_type: ErrorType
    message: str


class JavaScriptExecutor:
    """Executes JavaScript code using Deno CLI subprocess with timeout and error handling."""

    def __init__(self, timeout: float = 1.0):
        """Initialize the JavaScript executor.

        Args:
            timeout: Maximum execution time in seconds (default: 1.0)
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

            with TemporaryDirectory() as temp_dir:
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
                    "--allow-env=QTS_DEBUG",
                    f"--allow-read=js-executor/,{temp_path}",
                    self.executor_script,
                    code,
                    str(fields_path),
                    str(commands_path),
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
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.timeout
                        + 0.5,  # Add small buffer to Deno's internal timeout
                    )
                except asyncio.TimeoutError:
                    # Kill the process if it's still running
                    try:
                        process.kill()
                        await process.wait()
                    except ProcessLookupError:
                        pass  # Process already terminated
                    return (
                        False,
                        "⏱️ JavaScript execution timed out (1 second limit)",
                        None,
                    )

            # Decode output
            stdout_text = stdout.decode("utf-8").strip() if stdout else ""
            stderr_text = stderr.decode("utf-8").strip() if stderr else ""

            # Check exit code and classify errors
            if process.returncode == 0:
                parsed = json.loads(stdout_text)
                return True, parsed.get("output", ""), parsed.get("value", None)
            else:
                # Classify error based on stderr content
                error_type = self._classify_error(stderr_text)
                error_message = stderr_text or "Unknown execution error"

                # For user-facing errors, return a clean message
                if error_type == "timeout":
                    return (
                        False,
                        "⏱️ JavaScript execution timed out (1 second limit)",
                        None,
                    )
                elif error_type == "memory":
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

        if "timed out" in stderr_lower or "timeout" in stderr_lower:
            return "timeout"
        elif "memory" in stderr_lower or "out of memory" in stderr_lower:
            return "memory"
        elif "syntaxerror" in stderr_lower or "syntax error" in stderr_lower:
            return "syntax"
        else:
            return "runtime"


def extract_js_code(raw_code: str) -> str:
    """Parse and clean JavaScript code by stripping triple backticks.

    Handles various backtick formats (markdown):
    - Plain triple backticks:
      ```
      code
      ```

    - With a language identifier (for now we accept anything):
      ```js|javascript|...
      code
      ```

    - With additional text after language identifier:
      ```js foo bar
      code
      ```

    Args:
        raw_code: Raw JavaScript code that may contain triple backticks

    Returns:
        Cleaned JavaScript code with backticks and language identifiers removed

    Examples:
        >>> extract_js_code('```js\\nfoo\\n```')
        'foo'
        >>> extract_js_code('```js foo ```')
        'js foo'
        >>> extract_js_code('```\\nfoo\\n```')
        'foo'
        >>> extract_js_code('```foo```')
        'foo'
        >>> extract_js_code('foo(abc)')
        'foo(abc)'
    """
    code = raw_code.strip()

    # Handle empty or whitespace-only input
    if not code:
        return ""

    # Handle single-line case (no newlines)
    if "\n" not in code:
        # Strip backticks from start and end
        if code.startswith("```") and code.endswith("```"):
            return code[3:-3].strip()
        return code

    lines = code.splitlines()

    # Remove opening backticks line (first line that is exactly ```<identifier>)
    if lines and _is_code_block_opener(lines[0]):
        lines.pop(0)

    # Remove closing backticks line (last line that is exactly ```)
    if lines and lines[-1].strip() == "```":
        lines.pop()

    # Handle edge case where we removed all lines
    if not lines:
        return ""

    return "\n".join(lines).strip()


def _is_code_block_opener(line: str) -> bool:
    """Check if a line is a code block opener (```<identifier> with no extra content).

    Args:
        line: Line to check

    Returns:
        True if the line is exactly ``` followed by optional identifier and whitespace
    """
    stripped = line.strip()
    if not stripped.startswith("```"):
        return False

    # Remove the opening ```
    content = stripped[3:].strip()

    # If there's no content after ```, it's a valid opener
    if not content:
        return True

    # If there's content, it should be just an identifier (no spaces or extra text)
    # This allows ```js, ```javascript, etc. but not ```js foo bar
    return " " not in content

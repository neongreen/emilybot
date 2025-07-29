"""JavaScript execution service using Deno CLI subprocess."""

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Tuple
from emilybot.database import Entry


@dataclass
class JSExecutionError(Exception):
    """Exception raised when JavaScript execution fails."""

    error_type: str  # "timeout", "memory", "syntax", "runtime"
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
        self, code: str, context: dict[str, str | int]
    ) -> Tuple[bool, str]:
        """Execute JavaScript code with context.

        Args:
            code: JavaScript code to execute
            context: Context object to inject into JavaScript environment

        Returns:
            Tuple of (success: bool, output: str)
            - If success=True, output contains console.log output
            - If success=False, output contains error message

        Raises:
            JSExecutionError: When execution fails with specific error types
        """
        try:
            # Prepare context JSON
            context_json = json.dumps(context)

            # Build command
            cmd = [
                self.deno_path,
                "run",
                "--allow-env=QTS_DEBUG",
                f"--allow-read={Path('js-executor/deno.lock').resolve()}",
                self.executor_script,
                code,
                context_json,
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
                return False, "⏱️ JavaScript execution timed out (1 second limit)"

            # Decode output
            stdout_text = stdout.decode("utf-8").strip() if stdout else ""
            stderr_text = stderr.decode("utf-8").strip() if stderr else ""

            # Check exit code and classify errors
            if process.returncode == 0:
                return True, stdout_text
            else:
                # Classify error based on stderr content
                error_type = self._classify_error(stderr_text)
                error_message = stderr_text or "Unknown execution error"

                # For user-facing errors, return a clean message
                if error_type == "timeout":
                    return False, "⏱️ JavaScript execution timed out (1 second limit)"
                elif error_type == "memory":
                    return False, "💾 JavaScript execution exceeded memory limits"
                elif error_type == "syntax":
                    return (
                        False,
                        f"❌ JavaScript syntax error: {self._extract_syntax_error(stderr_text)}",
                    )
                elif error_type == "runtime":
                    return (
                        False,
                        f"⚠️ JavaScript runtime error: {self._extract_runtime_error(stderr_text)}",
                    )
                else:
                    return False, f"❌ JavaScript execution failed: {error_message}"

        except FileNotFoundError:
            return False, f"❌ Deno executable not found at: {self.deno_path}"
        except (TypeError, ValueError) as e:
            return False, f"❌ Failed to encode context as JSON: {e}"
        except JSExecutionError:
            # Re-raise JSExecutionError as-is
            raise
        except Exception as e:
            logging.error(f"Unexpected error in JavaScript execution: {e}")
            return False, f"❌ Unexpected execution error: {e}"

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

    def _extract_syntax_error(self, stderr: str) -> str:
        """Extract meaningful syntax error message from stderr.

        Args:
            stderr: Standard error output containing syntax error

        Returns:
            Cleaned syntax error message
        """
        # Try to extract the actual syntax error message
        lines = stderr.split("\n")
        for line in lines:
            if "SyntaxError" in line:
                # Remove "SyntaxError: " prefix if present
                return line.replace("SyntaxError: ", "").strip()

        # Fallback to first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()

        return "Invalid JavaScript syntax"

    def _extract_runtime_error(self, stderr: str) -> str:
        """Extract meaningful runtime error message from stderr.

        Args:
            stderr: Standard error output containing runtime error

        Returns:
            Cleaned runtime error message
        """
        # Try to extract the actual error message
        lines = stderr.split("\n")
        for line in lines:
            # Look for common error patterns
            if any(
                error_type in line
                for error_type in [
                    "Error:",
                    "TypeError:",
                    "ReferenceError:",
                    "RangeError:",
                ]
            ):
                return line.strip()

        # Fallback to first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()

        return "JavaScript runtime error"


def create_context_from_entry(entry: Entry) -> dict[str, str | int]:
    """Create JavaScript execution context from Entry object.

    Args:
        entry: Database entry to create context from

    Returns:
        Context dictionary for JavaScript execution
    """
    return {
        "content": entry.content,
        "name": entry.name,
        "created_at": entry.created_at,
        "user_id": entry.user_id,
    }


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

    Args:
        raw_code: Raw JavaScript code that may contain triple backticks

    Returns:
        Cleaned JavaScript code with backticks and language identifiers removed
    """
    code = raw_code.strip()

    lines = code.splitlines()
    if lines[0].strip().startswith("```"):
        lines.pop(0)  # Remove first line
    if lines[-1].strip().startswith("```"):
        lines.pop()  # Remove last line

    return "\n".join(lines).strip()

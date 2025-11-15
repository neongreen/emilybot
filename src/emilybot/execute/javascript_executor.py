"""JavaScript execution service using Deno CLI subprocess.

DEPRECATED: This module is a compatibility layer. Import from the following modules instead:
- emilybot.execute.context: Context data classes
- emilybot.execute.code_extraction: Code extraction utilities
- emilybot.execute.executor: JavaScriptExecutor and types
"""

# Re-export everything from the new modules for backward compatibility
from emilybot.execute.context import (
    CtxUser,
    CtxServer,
    CtxReplyTo,
    CtxMessage,
    Context,
    create_test_user,
    run_code_context,
)
from emilybot.execute.code_extraction import extract_js_code
from emilybot.execute.executor import (
    CommandData,
    ExecutionResult,
    ErrorType,
    JSExecutionError,
    JavaScriptExecutor,
)

__all__ = [
    # Context data classes
    "CtxUser",
    "CtxServer",
    "CtxReplyTo",
    "CtxMessage",
    "Context",
    "create_test_user",
    "run_code_context",
    # Code extraction
    "extract_js_code",
    # Executor and types
    "CommandData",
    "ExecutionResult",
    "ErrorType",
    "JSExecutionError",
    "JavaScriptExecutor",
]

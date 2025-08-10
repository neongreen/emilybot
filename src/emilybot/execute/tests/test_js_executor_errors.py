"""Test script for JavaScript executor error handling."""

import pytest

from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    Context,
    CtxMessage,
    create_test_user,
    CtxServer,
)


@pytest.fixture
def executor():
    """Create a JavaScript executor for testing."""
    return JavaScriptExecutor(timeout=1.0)


@pytest.fixture
def test_context():
    """Create a test context for testing."""
    return Context(
        message=CtxMessage(text="test message"),
        reply_to=None,
        user=create_test_user(id="123", name="TestUser"),
        server=CtxServer(id="12345"),
    )


@pytest.mark.asyncio
async def test_syntax_error(executor: JavaScriptExecutor, test_context: Context):
    """Test syntax error handling."""
    syntax_error_code = "console.log('missing quote);"
    success, output, _value = await executor.execute(
        syntax_error_code, test_context, []
    )
    assert not success
    assert "SyntaxError" in output or "error" in output.lower()


@pytest.mark.asyncio
async def test_runtime_error(executor: JavaScriptExecutor, test_context: Context):
    """Test runtime error handling."""
    runtime_error_code = "console.log(undefinedVariable);"
    success, output, _value = await executor.execute(
        runtime_error_code, test_context, []
    )
    assert not success
    assert "ReferenceError" in output or "error" in output.lower()


@pytest.mark.asyncio
async def test_timeout(executor: JavaScriptExecutor, test_context: Context):
    """Test timeout handling."""
    timeout_code = "while(true) { /* infinite loop */ }"
    success, _output, _value = await executor.execute(timeout_code, test_context, [])
    assert not success
    # Timeout should result in failure, but the exact error message may vary


@pytest.mark.asyncio
async def test_multiple_console_log_calls(
    executor: JavaScriptExecutor, test_context: Context
):
    """Test successful execution with multiple console.log calls."""
    multi_log_code = """
    console.log('Line 1');
    console.log('Line 2');
    console.log('User name: ' + user.name);
    """
    success, output, _value = await executor.execute(multi_log_code, test_context, [])
    assert success
    assert "Line 1" in output
    assert "Line 2" in output
    assert "User name: TestUser" in output

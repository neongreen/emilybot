"""Test that the utility library meets all requirements from the specification."""

import pytest
from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    run_code_context,
)


@pytest.mark.asyncio
async def test_requirement_4_2_convenient_utility_wrappers():
    """Test requirement 4.2: WHEN a user calls utility functions like $.lib.random(min, max) THEN the system SHALL provide convenient wrappers for common operations"""
    executor = JavaScriptExecutor()

    code = """
    // Test $.lib.random function
    const randomNum = $.lib.random(10, 20);
    console.log("Random function works:", typeof randomNum === 'number');
    console.log("Random in range:", randomNum >= 10 && randomNum <= 20);
    """

    context = run_code_context(code)
    success, output, _value = await executor.execute(code, context)

    assert success, f"Execution failed: {output}"
    assert "Random function works: true" in output
    assert "Random in range: true" in output


@pytest.mark.asyncio
async def test_requirement_dollar_inspection_shows_functions():
    executor = JavaScriptExecutor()

    code = """
    console.log("$ object:", $);
    """

    context = run_code_context(code)
    success, output, _value = await executor.execute(code, context)

    assert success, f"Execution failed: {output}"
    assert "random" in output


@pytest.mark.asyncio
async def test_requirement_4_3_lib_inspection_shows_functions():
    """Test requirement 4.3: WHEN a user inspects $.lib THEN the system SHALL show all available utility functions"""
    executor = JavaScriptExecutor()

    code = """
    console.log("$.lib object:", $.lib);
    """

    context = run_code_context(code)
    success, output, _value = await executor.execute(code, context)

    assert success, f"Execution failed: {output}"
    assert "random" in output

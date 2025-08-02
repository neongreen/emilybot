"""Test the utility library functionality in the JavaScript execution environment."""

import pytest
from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    run_code_context,
)


@pytest.mark.asyncio
async def test_utility_lib_random():
    """Test that $.lib.random function works correctly."""
    executor = JavaScriptExecutor()

    code = """
    // Test random function
    const num1 = $.lib.random(1, 10);
    const num2 = $.lib.random(50, 100);
    
    console.log("Random 1-10:", num1);
    console.log("Random 50-100:", num2);
    
    // Verify ranges
    if (num1 >= 1 && num1 <= 10) {
        console.log("✅ First random number in range");
    } else {
        console.log("❌ First random number out of range:", num1);
    }
    
    if (num2 >= 50 && num2 <= 100) {
        console.log("✅ Second random number in range");
    } else {
        console.log("❌ Second random number out of range:", num2);
    }
    """

    context = run_code_context(code)
    success, output, _value = await executor.execute(code, context)

    assert success, f"Execution failed: {output}"
    assert "Random 1-10:" in output
    assert "Random 50-100:" in output
    assert "✅ First random number in range" in output
    assert "✅ Second random number in range" in output

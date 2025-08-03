#!/usr/bin/env python3

import asyncio
from emilybot.execute.javascript_executor import (
    CommandData,
    JavaScriptExecutor,
    Context,
    CtxMessage,
    CtxUser,
    CtxServer,
)


async def test_what_works():
    # Create executor
    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(text="test message content"),
        user=CtxUser(id="12345", name="TestUser"),
        server=CtxServer(id="67890"),
    )

    # Create some test commands
    commands = [
        CommandData(
            name="hello",
            content="Hello World!",
            run=None,
        ),
        CommandData(
            name="test-command",
            content="This is a test command with dashes",
            run=None,
        ),
    ]

    # Test what actually works
    code = """
    console.log("=== Testing Basic Access ===");
    console.log("typeof $:", typeof $);
    console.log("$ object:", $);
    
    console.log("\\n=== Testing Commands ===");
    console.log("$.commands:", $.commands);
    console.log("Object.keys($.commands):", Object.keys($.commands));
    
    console.log("\\n=== Testing cmd function ===");
    try {
        console.log("$.cmd('hello'):", $.cmd('hello'));
    } catch (e) {
        console.log("Error calling $.cmd('hello'):", e.message);
    }
    
    console.log("\\n=== Testing Direct Access ===");
    try {
        console.log("$.hello:", $.hello);
    } catch (e) {
        console.log("Error accessing $.hello:", e.message);
    }
    
    console.log("\\n=== Testing Bracket Access ===");
    try {
        console.log("$['hello']:", $['hello']);
    } catch (e) {
        console.log("Error accessing $['hello']:", e.message);
    }
    """

    success, output, value = await executor.execute(code, context, commands)

    print(f"Success: {success}")
    print(f"Output: {output}")
    print(f"Value: {value}")


if __name__ == "__main__":
    asyncio.run(test_what_works())

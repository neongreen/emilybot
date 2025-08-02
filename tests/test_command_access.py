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


async def test_command_access():
    # Create executor
    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(content="test message content"),
        user=CtxUser(id=12345, name="TestUser"),
        server=CtxServer(id=67890),
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
        CommandData(
            name="math",
            content="console.log(2 + 2)",
            run="console.log(2 + 2)",
        ),
        CommandData(
            name="validIdentifier",
            content="Valid JS identifier",
            run=None,
        ),
        CommandData(
            name="invalid-identifier",
            content="Invalid JS identifier with dash",
            run=None,
        ),
    ]

    # Test command access patterns
    code = """
    console.log("=== Command Access Test ===");
    console.log("Available commands:", Object.keys($).filter(k => !["ctx", "lib"].includes(k)));
    
    console.log("\\n=== Property Access (valid identifiers) ===");
    console.log("$.hello:", $.hello);
    console.log("$.validIdentifier:", $.validIdentifier);
    
    console.log("\\n=== Bracket Access ===");
    console.log("$['hello']:", $['hello']);
    console.log("$['test-command']:", $['test-command']);
    console.log("$['invalid-identifier']:", $['invalid-identifier']);
    
    console.log("\\n=== Function Call Access ===");
    console.log("$('hello'):", $('hello'));
    console.log("$('test-command'):", $('test-command'));
    console.log("$('invalid-identifier'):", $('invalid-identifier'));
    
    console.log("\\n=== Non-existent Command ===");
    console.log("$('nonexistent'):", $('nonexistent'));
    """

    success, output, value = await executor.execute(code, context, commands)

    print(f"Success: {success}")
    print(f"Output: {output}")
    print(f"Value: {value}")


if __name__ == "__main__":
    asyncio.run(test_command_access())

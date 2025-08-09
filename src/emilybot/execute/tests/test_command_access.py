import asyncio
from emilybot.execute.javascript_executor import (
    CommandData,
    JavaScriptExecutor,
    Context,
    CtxMessage,
    CtxServer,
    create_test_user,
)


async def test_command_access():
    """Golden test: Verify the actual behavior of Emily's JavaScript API.

    This test documents what actually works vs what doesn't work in the
    JavaScript execution environment. It serves as both a test and documentation
    of the real API behavior.
    """
    # Create executor
    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(text="test message content"),
        user=create_test_user(id="12345", name="TestUser"),
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

    # Test command access patterns - both what works and what doesn't
    code = """
    console.log("=== Golden Test: Emily JavaScript API Reality Check ===");
    
    console.log("\\n=== What WORKS: $.commands access ===");
    console.log("Available commands:", Object.keys($.commands));
    console.log("$.commands.hello:", $.commands.hello);
    console.log("$.commands.hello.content:", $.commands.hello.content);
    console.log("$.commands['test-command']:", $.commands['test-command']);
    console.log("$.commands['test-command'].content:", $.commands['test-command'].content);
    
    console.log("\\n=== What WORKS: $.cmd() function ===");
    console.log("Calling $.cmd('hello'):");
    $.cmd('hello');
    console.log("Calling $.cmd('test-command'):");
    $.cmd('test-command');
    
    console.log("\\n=== What WORKS: Context and utilities ===");
    console.log("$.ctx.user.name:", $.ctx.user.name);
    console.log("$.lib.random(1,3):", $.lib.random(1,3));
    
    console.log("\\n=== What DOESN'T WORK: Direct property access ===");
    console.log("$.hello (should be undefined):", $.hello);
    console.log("$['hello'] (should be undefined):", $['hello']);
    
    console.log("\\n=== What DOESN'T WORK: $ as function ===");
    try {
        $('hello');
        console.log("ERROR: $('hello') should have failed!");
    } catch (e) {
        console.log("✅ $('hello') correctly failed:", e.message);
    }
    
    console.log("\\n=== Error handling for $.cmd() ===");
    try {
        $.cmd('nonexistent');
        console.log("ERROR: $.cmd('nonexistent') should have failed!");
    } catch (e) {
        console.log("✅ $.cmd('nonexistent') correctly failed:", e.message);
    }
    
    console.log("\\n=== Full $ object structure ===");
    console.log("Object.keys($):", Object.keys($));
    """

    success, output, value = await executor.execute(code, context, commands)

    print(f"Success: {success}")
    print(f"Output: {output}")
    print(f"Value: {value}")


if __name__ == "__main__":
    asyncio.run(test_command_access())

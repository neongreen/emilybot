"""Test dollar prefix functionality"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from emilybot.discord import EmilyContext
from emilybot.execute.run_code import run_code


@pytest.mark.asyncio
async def test_dollar_prefix_javascript_execution():
    """Test that $unknown executes as JavaScript"""

    # Create a mock context
    ctx = MagicMock(spec=EmilyContext)
    ctx.bot = MagicMock()
    ctx.bot.db = MagicMock()
    ctx.guild = None  # DM context
    ctx.author.id = 12345
    ctx.author.display_name = "TestUser"
    ctx.message = MagicMock()
    ctx.message.content = "$console.log('Hello from JavaScript!')"
    ctx.send = AsyncMock()

    # Test JavaScript execution
    success, output, _value = await run_code(
        ctx, code="console.log('Hello from JavaScript!')"
    )

    assert success
    assert "Hello from JavaScript!" in output


@pytest.mark.asyncio
async def test_dollar_prefix_global_commands():
    """Test that commands become available as global variables"""

    # Create executor
    from emilybot.execute.javascript_executor import (
        JavaScriptExecutor,
        CommandData,
        Context,
        CtxMessage,
        CtxUser,
        CtxServer,
    )

    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(text="test message content"),
        user=CtxUser(id="12345", name="TestUser"),
        server=CtxServer(id="67890"),
    )

    # Create test commands
    commands = [
        CommandData(
            name="weather",
            content="Sunny, 75°F",
            run=None,
        ),
        CommandData(
            name="user-settings",
            content="theme: dark",
            run=None,
        ),
        CommandData(
            name="docs/api",
            content="API documentation",
            run=None,
        ),
        CommandData(
            name="docs/install",
            content="Installation guide",
            run=None,
        ),
    ]

    # Test global command objects
    success, output, _value = await executor.execute(
        """
        console.log("Testing global command objects");
        console.log("$weather._name:", $weather._name);
        console.log("$weather._content:", $weather._content);
        console.log("$user_settings._name:", $user_settings._name);
        console.log("$user_settings._content:", $user_settings._content);
        console.log("$docs.api._name:", $docs.api._name);
        console.log("$docs.api._content:", $docs.api._content);
        console.log("$docs.install._name:", $docs.install._name);
        console.log("$docs.install._content:", $docs.install._content);
    """,
        context,
        commands,
    )

    assert success
    assert "$weather._name: weather" in output
    assert "$weather._content: Sunny, 75°F" in output
    assert "$user_settings._name: user-settings" in output
    assert "$user_settings._content: theme: dark" in output
    assert "$docs.api._name: docs/api" in output
    assert "$docs.api._content: API documentation" in output
    assert "$docs.install._name: docs/install" in output
    assert "$docs.install._content: Installation guide" in output


@pytest.mark.asyncio
async def test_dollar_prefix_command_execution():
    """Test that global command objects are callable"""

    # Create executor
    from emilybot.execute.javascript_executor import (
        JavaScriptExecutor,
        CommandData,
        Context,
        CtxMessage,
        CtxUser,
        CtxServer,
    )

    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(text="test message content"),
        user=CtxUser(id="12345", name="TestUser"),
        server=CtxServer(id="67890"),
    )

    # Create test commands
    commands = [
        CommandData(
            name="weather",
            content="Sunny, 75°F",
            run=None,
        ),
        CommandData(
            name="greeting",
            content="Hello, world!",
            run="console.log('🌤️ ' + this.content)",
        ),
    ]

    # Test calling commands
    success, output, value = await executor.execute(
        """
        console.log("Calling weather command:");
        $weather();
        console.log("Calling greeting command:");
        $greeting();
        console.log("Testing $greeting._run():");
        $greeting._run();
    """,
        context,
        commands,
    )

    print(f"Success: {success}")
    print(f"Output: {output}")
    print(f"Value: {value}")
    assert success
    assert "Sunny, 75°F" in output
    # The greeting command should show its content when called directly
    assert "Hello, world!" in output


@pytest.mark.asyncio
async def test_dollar_prefix_nested_commands():
    """Test that nested commands work correctly"""

    # Create executor
    from emilybot.execute.javascript_executor import (
        JavaScriptExecutor,
        CommandData,
        Context,
        CtxMessage,
        CtxUser,
        CtxServer,
    )

    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(text="test message content"),
        user=CtxUser(id="12345", name="TestUser"),
        server=CtxServer(id="67890"),
    )

    # Create test commands
    commands = [
        CommandData(
            name="api/v1/users",
            content="User endpoints",
            run=None,
        ),
        CommandData(
            name="api/v1/orders",
            content="Order endpoints",
            run=None,
        ),
        CommandData(
            name="docs/getting-started",
            content="Getting started guide",
            run=None,
        ),
    ]

    # Test nested command access
    success, output, _value = await executor.execute(
        """
        console.log("Testing nested commands:");
        console.log("$api.v1.users._name:", $api.v1.users._name);
        console.log("$api.v1.users._content:", $api.v1.users._content);
        console.log("$api.v1.orders._name:", $api.v1.orders._name);
        console.log("$api.v1.orders._content:", $api.v1.orders._content);
        console.log("$docs.getting_started._name:", $docs.getting_started._name);
        console.log("$docs.getting_started._content:", $docs.getting_started._content);
    """,
        context,
        commands,
    )

    assert success
    assert "$api.v1.users._name: api/v1/users" in output
    assert "$api.v1.users._content: User endpoints" in output
    assert "$api.v1.orders._name: api/v1/orders" in output
    assert "$api.v1.orders._content: Order endpoints" in output
    assert "$docs.getting_started._name: docs/getting-started" in output
    assert "$docs.getting_started._content: Getting started guide" in output


@pytest.mark.asyncio
async def test_dollar_prefix_legacy_compatibility():
    """Test that legacy $.commands access still works"""

    # Create executor
    from emilybot.execute.javascript_executor import (
        JavaScriptExecutor,
        CommandData,
        Context,
        CtxMessage,
        CtxUser,
        CtxServer,
    )

    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(text="test message content"),
        user=CtxUser(id="12345", name="TestUser"),
        server=CtxServer(id="67890"),
    )

    # Create test commands
    commands = [
        CommandData(
            name="weather",
            content="Sunny, 75°F",
            run=None,
        ),
    ]

    # Test legacy access
    success, output, _value = await executor.execute(
        """
        console.log("Testing legacy access:");
        console.log("$.commands.weather.name:", $.commands.weather.name);
        console.log("$.commands.weather.content:", $.commands.weather.content);
        console.log("$.cmd('weather'):");
        $.cmd('weather');
    """,
        context,
        commands,
    )

    assert success
    assert "$.commands.weather.name: weather" in output
    assert "$.commands.weather.content: Sunny, 75°F" in output
    assert "Sunny, 75°F" in output  # From $.cmd call


@pytest.mark.asyncio
async def test_dollar_prefix_command_arguments():
    """Test that commands can accept arguments when called with $ prefix"""

    # Create executor
    from emilybot.execute.javascript_executor import (
        JavaScriptExecutor,
        CommandData,
        Context,
        CtxMessage,
        CtxUser,
        CtxServer,
    )

    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(text="test message content"),
        user=CtxUser(id="12345", name="TestUser"),
        server=CtxServer(id="67890"),
    )

    # Create test commands with argument handling
    commands = [
        CommandData(
            name="greeting",
            content="Hello, world!",
            run="console.log('Hello ' + args[0] + ' and ' + args[1] + '!')",
        ),
        CommandData(
            name="echo",
            content="Echo command",
            run="console.log('Args:', args); console.log('Args length:', args.length)",
        ),
        CommandData(
            name="welcome",
            content="Welcome message",
            run="let name = args[0] || 'Guest'; console.log('Welcome ' + name + '!')",
        ),
    ]

    # Test calling commands with arguments
    success, output, value = await executor.execute(
        """
        console.log("Testing command arguments:");
        $greeting("Alice", "Bob");
        $echo("Hello", "World", "Test");
        $welcome("Charlie");
        $welcome();
    """,
        context,
        commands,
    )

    print(f"Success: {success}")
    print(f"Output: {output}")
    print(f"Value: {value}")
    assert success
    assert "Hello Alice and Bob!" in output
    assert 'Args: [ "Hello", "World", "Test" ]' in output
    assert "Args length: 3" in output
    assert "Welcome Charlie!" in output
    assert "Welcome Guest!" in output


@pytest.mark.asyncio
async def test_dollar_prefix_arguments_via_cmd():
    """Test that $.cmd() function can pass arguments to commands"""

    # Create executor
    from emilybot.execute.javascript_executor import (
        JavaScriptExecutor,
        CommandData,
        Context,
        CtxMessage,
        CtxUser,
        CtxServer,
    )

    executor = JavaScriptExecutor()

    # Create context
    context = Context(
        message=CtxMessage(text="test message content"),
        user=CtxUser(id="12345", name="TestUser"),
        server=CtxServer(id="67890"),
    )

    # Create test command
    commands = [
        CommandData(
            name="test-args",
            content="Test arguments",
            run="console.log('Received args:', args); console.log('First arg:', args[0])",
        ),
    ]

    # Test calling command with arguments via $.cmd()
    success, output, value = await executor.execute(
        """
        console.log("Testing $.cmd() with arguments:");
        $.cmd("test-args", "first", "second", "third");
    """,
        context,
        commands,
    )

    print(f"Success: {success}")
    print(f"Output: {output}")
    print(f"Value: {value}")
    assert success
    assert 'Received args: [ "first", "second", "third" ]' in output
    assert "First arg: first" in output

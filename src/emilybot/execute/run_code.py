"""Command for executing JavaScript code directly."""

from emilybot.discord import EmilyContext
from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    Context,
    CtxMessage,
    CtxUser,
    CtxServer,
)
from emilybot.command_query_service import CommandQueryService


async def run_code(
    ctx: EmilyContext,
    *,
    code: str,
) -> tuple[bool, str, str | None]:
    """Run JavaScript code directly and return the result."""

    # Create JavaScript executor
    js_executor = JavaScriptExecutor()

    # Get available commands using command query service
    command_query_service = CommandQueryService(ctx.bot.db)
    available_commands = command_query_service.get_available_commands(
        user_id=ctx.author.id, server_id=ctx.guild.id if ctx.guild else None
    )

    # Create Context for direct execution.
    # When changing this, also change `make_ctx` in conftest.py
    context = Context(
        message=CtxMessage(text=ctx.message.content),
        user=CtxUser(
            id=str(ctx.author.id),
            handle=ctx.author.name,
            name=ctx.author.display_name,
            global_name=ctx.author.global_name,
            avatar_url=ctx.author.display_avatar.url,
        ),
        server=CtxServer(id=str(ctx.guild.id)) if ctx.guild else None,
    )

    # Execute JavaScript code with available commands
    success, output, value = await js_executor.execute(
        code, context, available_commands
    )

    return success, output, value

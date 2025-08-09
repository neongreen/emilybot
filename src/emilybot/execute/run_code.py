"""Command for executing JavaScript code directly."""

from discord import Message
from emilybot.discord import EmilyContext
from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    Context,
    CtxMessage,
    CtxReplyTo,
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

    # Extract reply information if available
    reply_to = None
    if (
        ctx.message.reference
        and ctx.message.reference.resolved
        and not hasattr(ctx.message.reference.resolved, "_deleted")
    ):
        try:
            resolved_message = ctx.message.reference.resolved
            if isinstance(resolved_message, Message):
                reply_to = CtxReplyTo(
                    text=str(resolved_message.content),
                    user=CtxUser(
                        id=str(resolved_message.author.id),
                        handle=str(resolved_message.author.name),
                        name=str(resolved_message.author.display_name),
                        global_name=resolved_message.author.global_name,
                        avatar_url=str(resolved_message.author.display_avatar.url),
                    ),
                )
        except (AttributeError, TypeError):
            # Handle cases where the resolved message doesn't have expected attributes
            pass

    context = Context(
        message=CtxMessage(
            text=ctx.message.content,
        ),
        reply_to=reply_to,
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

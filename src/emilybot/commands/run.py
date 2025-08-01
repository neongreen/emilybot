"""Command for executing JavaScript code directly."""

from discord.ext import commands
from emilybot.discord import EmilyContext
from emilybot.javascript_executor import (
    JavaScriptExecutor,
    extract_js_code,
    create_run_command_context,
)


def format_show_content(content: str) -> str:
    """Format content for display, applying length and line limits."""
    # trim if >2000char, *then* trim if >100 lines
    if len(content) > 2000:
        content = content[:2000] + "..."
    if content.count("\n") > 100:
        content = "\n".join(content.split("\n")[:100]) + "..."
    return content


@commands.command(name="run")
async def cmd_run(
    ctx: EmilyContext,
    *,  # treat the rest as a single string
    code: str,
) -> None:
    """`.run [JS code]`: Execute JavaScript code directly."""

    try:
        # Parse and clean JavaScript code
        cleaned_code = extract_js_code(code)

        # Create JavaScript executor
        js_executor = JavaScriptExecutor()

        # Create RunCommandContext for direct execution
        context = create_run_command_context(
            user_id=ctx.author.id, server_id=ctx.guild.id if ctx.guild else None
        )

        # Execute JavaScript code
        success, output = await js_executor.execute(cleaned_code, context)

        if success:
            if output.strip():
                await ctx.send(format_show_content(output))
            else:
                await ctx.send("🔧 **JavaScript executed successfully** *(no output)*")
        else:
            await ctx.send(output)  # Error message is already formatted

    except Exception as e:
        # Handle unexpected errors gracefully
        await ctx.send(f"❌ **JavaScript error:**\nUnexpected error: {str(e)}")

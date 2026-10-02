"""Help, input-error replies and not-found suggestions, through the real bot.

Every test sends fake messages through the production `on_message` handler
(see `BotHarness`). Nothing connects to Discord.
"""

import copy
from typing import Any

import pytest

from emilybot.commands.help import QUICK_START, TOPICS, Topic
from emilybot.database import DB
from emilybot.test_utils.bot_harness import BotHarness, make_bot_harness

SERVER = 12345
OTHER_SERVER = 55555
USER = 67890
OTHER_USER = 11111


@pytest.fixture
async def harness(db: DB, monkeypatch: pytest.MonkeyPatch) -> BotHarness:
    return await make_bot_harness(db, monkeypatch)


def snapshot(db: DB) -> tuple[list[Any], list[Any]]:
    return copy.deepcopy(db.remember.all()), copy.deepcopy(db.log.all())


# --- documented examples -------------------------------------------------


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "topic",
    [QUICK_START, *TOPICS.values()],
    ids=["quick-start", *TOPICS.keys()],
)
async def test_documented_examples_work(harness: BotHarness, topic: Topic):
    """Each example shown in help gives the reply help claims, using the
    real parser, command dispatch and JavaScript executor."""
    for example in topic.examples:
        reactions_before = len(harness.sent.reactions)
        replies = await harness.say(example.message)
        if example.reply is None:
            assert replies == [], example.message
            assert len(harness.sent.reactions) == reactions_before + 1
        else:
            assert len(replies) == 1, example.message
            assert example.reply in replies[0], (example.message, replies[0])


async def test_help_starts_with_quick_start(harness: BotHarness):
    await harness.say(".add zebra Stripes")
    await harness.say(".promote zebra")
    [reply] = await harness.say(".help")
    assert reply.startswith("__Quick start__")
    assert reply.index(".add greet Hello") < reply.index("`.zebra`: Stripes")
    for name in TOPICS:
        assert f"`.help {name}`" in reply


@pytest.mark.parametrize("name", ["set", "add", "edit", "show"])
async def test_help_topic(harness: BotHarness, name: str):
    [reply] = await harness.say(f".help {name}")
    assert reply.startswith(f"`.{name} ")
    assert TOPICS[name].explanation in reply
    for example in TOPICS[name].examples:
        assert example.message in reply


async def test_help_topic_accepts_prefix(harness: BotHarness):
    assert await harness.say(".help .set") == await harness.say(".help set")


async def test_help_topic_without_details_uses_usage(harness: BotHarness):
    [reply] = await harness.say(".help rm")
    assert reply == "`.rm [alias]`: Delete an alias."


async def test_help_topic_for_alias_points_to_show(harness: BotHarness):
    await harness.say(".add jokes Knock knock")
    [reply] = await harness.say(".help jokes")
    assert "`jokes` is an alias" in reply
    assert "`.show jokes`" in reply


async def test_help_unknown_topic(harness: BotHarness):
    [reply] = await harness.say(".help nothing-here")
    assert "No help for 'nothing-here'" in reply
    assert "`set`" in reply


# --- input errors -------------------------------------------------------


@pytest.mark.parametrize(
    ("message", "usage"),
    [
        (".add", "`.add [alias] [text]`"),
        (".add foo", "`.add [alias] [text]`"),
        (".edit", "`.edit [alias] [text]`"),
        (".edit foo", "`.edit [alias] [text]`"),
        (".set", "`.set [alias].run [JS code]`"),
        (".set foo.run", "`.set [alias].run [JS code]`"),
        (".show", "`.show [alias][/]`"),
        (".rm", "`.rm [alias]`"),
        (".random", "`.random [alias]`"),
        ("$add", "`.add [alias] [text]`"),
    ],
)
async def test_missing_argument_gives_usage(
    harness: BotHarness, db: DB, message: str, usage: str
):
    before = snapshot(db)
    [reply] = await harness.say(message)
    assert reply.startswith("❌ Missing `[")
    assert f"Usage: {usage}" in reply
    assert snapshot(db) == before


async def test_set_without_run_explains(harness: BotHarness, db: DB):
    await harness.say(".add foo text")
    before = snapshot(db)
    [reply] = await harness.say(".set foo print(1)")
    assert "`.set foo.run [JS code]`" in reply
    assert snapshot(db) == before


async def test_internal_error_is_not_called_input_error(
    harness: BotHarness, db: DB, monkeypatch: pytest.MonkeyPatch
):
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("database exploded")

    monkeypatch.setattr(db, "find_alias", broken)
    assert await harness.say(".show foo") == []


@pytest.mark.parametrize(
    "message",
    [".", "..", "...", ". hi", "$", "$$$", "$1", ".1", "$13.2", "$.12", "hello"],
)
async def test_ignored_input_stays_silent(harness: BotHarness, db: DB, message: str):
    before = snapshot(db)
    assert await harness.say(message) == []
    assert harness.sent.reactions == []
    assert snapshot(db) == before


# --- suggestions --------------------------------------------------------


@pytest.mark.parametrize("message", [".jokse", "$jokse", ".show jokse", ".jkes"])
async def test_close_alias_is_suggested(harness: BotHarness, db: DB, message: str):
    await harness.say(".add jokes Knock knock")
    before = snapshot(db)
    [reply] = await harness.say(message)
    assert "not found" in reply
    assert "Did you mean `.jokes`?" in reply
    assert "Knock knock" not in reply  # never runs the suggested alias
    assert snapshot(db) == before  # never creates anything


@pytest.mark.parametrize("message", [".edit jokse x", ".set jokse.run 1", ".rm jokse"])
async def test_suggestions_on_other_not_found_paths(
    harness: BotHarness, db: DB, message: str
):
    await harness.say(".add jokes Knock knock")
    before = snapshot(db)
    [reply] = await harness.say(message)
    assert "Did you mean `.jokes`?" in reply
    assert snapshot(db) == before


async def test_builtin_is_suggested(harness: BotHarness):
    [reply] = await harness.say(".hepl")
    assert "Did you mean `.help`?" in reply


async def test_unrelated_name_gets_no_suggestion(harness: BotHarness):
    await harness.say(".add jokes Knock knock")
    [reply] = await harness.say(".weather")
    assert "not found" in reply
    assert "Did you mean" not in reply


async def test_suggestions_stay_in_scope(harness: BotHarness):
    await harness.say(".add jokes Knock knock", guild_id=SERVER)
    await harness.say(".add mysecret hidden", guild_id=None, author_id=USER)

    [other_server] = await harness.say(".jokse", guild_id=OTHER_SERVER)
    [dm] = await harness.say(".jokse", guild_id=None)
    assert "Did you mean" not in other_server
    assert "Did you mean" not in dm

    [own_dm] = await harness.say(".mysecrte", guild_id=None, author_id=USER)
    [other_dm] = await harness.say(".mysecrte", guild_id=None, author_id=OTHER_USER)
    [server] = await harness.say(".mysecrte", guild_id=SERVER)
    assert "Did you mean `.mysecret`?" in own_dm
    assert "Did you mean" not in other_dm
    assert "Did you mean" not in server


async def test_source_view_guess_points_to_show(harness: BotHarness, db: DB):
    await harness.say(".add jokes Knock knock")
    before = snapshot(db)
    [reply] = await harness.say(".view jokes")
    assert "`.show [alias]`" in reply
    assert snapshot(db) == before


async def test_alias_named_like_a_guess_still_runs(harness: BotHarness):
    await harness.say(".add code Community alias")
    [reply] = await harness.say(".code")
    assert reply == "Community alias"

"""Compile definitions without dispatching commands or running their code."""

from dataclasses import dataclass, replace
from datetime import datetime
import difflib
import uuid

from markdown_it import MarkdownIt

from emilybot.database import DB, Entry, Action, ActionInstall
from emilybot.commands.install_source import InstallError, MAX_BYTES
from emilybot.execute.code_extraction import extract_js_code
from emilybot.execute.code_validation import validate_command_code, ValidatorFailed
from emilybot.parser.string_view import StringView, ArgumentParsingError
from emilybot.validation import validate_path, ValidationError


@dataclass(frozen=True)
class Change:
    name: str
    before: Entry | None
    after: Entry

    @property
    def fields(self) -> tuple[str, ...]:
        return tuple(
            field
            for field in ("content", "run")
            if self.before is None
            or getattr(self.before, field) != getattr(self.after, field)
        )


@dataclass(frozen=True)
class InstallPlan:
    source: bytes
    server_id: int | None
    user_id: int
    changes: tuple[Change, ...]
    skipped: tuple[str, ...]

    @property
    def changed(self) -> tuple[Change, ...]:
        return tuple(c for c in self.changes if c.before != c.after)


def definition_blocks(source: bytes) -> list[str]:
    if len(source) > MAX_BYTES:
        raise InstallError("The file exceeds 256 KiB.")
    try:
        text = source.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise InstallError("The file must contain valid UTF-8 text.") from e
    return [
        t.content.rstrip("\n")
        for t in MarkdownIt("commonmark").parse(text)
        if t.type == "fence" and t.level == 0
    ]


async def compile_plan(
    db: DB, source: bytes, server_id: int | None, user_id: int
) -> InstallPlan:
    original: dict[str, Entry | None] = {}
    planned: dict[str, Entry] = {}
    skipped: list[str] = []
    count = 0
    for block in definition_blocks(source):
        view = StringView(block.strip())
        command = view.get_word()
        if command not in (".add", ".edit", ".set"):
            if command.startswith((".", "$")):
                skipped.append(command)
            continue
        count += 1
        if count > 50:
            raise InstallError("A file can contain at most 50 definitions.")
        try:
            view.skip_ws()
            place = view.get_quoted_word()
            if not place:
                raise InstallError(f"{command} needs an alias.")
            view.skip_ws()
            value = view.read_rest().strip()
            if command == ".set":
                if not place.endswith(".run"):
                    raise InstallError(
                        "Only .set NAME.run is supported in definitions."
                    )
                place = place[:-4]
            name = validate_path(
                place,
                normalize_dashes=False,
                normalize_dots=True,
                check_component_length=True,
                allow_trailing_slash=False,
            ).lower()
            if name not in original:
                matches = db.find_alias(name, server_id=server_id, user_id=user_id)
                if len(matches) > 1:
                    raise InstallError(
                        f"Alias {name} has duplicate saved entries; resolve them first."
                    )
                original[name] = matches[0] if matches else None
                if matches:
                    planned[name] = matches[0]
            current = planned.get(name)
            if command != ".add" and current is None:
                raise InstallError(f"Alias {name} must exist before {command}.")
            if command in (".add", ".edit"):
                if not value:
                    raise InstallError(f"Text for {name} cannot be empty.")
                if current is None:
                    planned[name] = Entry(
                        uuid.uuid4(),
                        server_id,
                        user_id,
                        datetime.now().isoformat(),
                        name,
                        value,
                        False,
                    )
                else:
                    planned[name] = replace(current, content=value)
            else:
                assert current is not None
                code = extract_js_code(value)
                if code.strip():
                    invalid = await validate_command_code(code)
                    if invalid:
                        raise InstallError(
                            f"Invalid JavaScript for {name}: {invalid.describe()}"
                        )
                planned[name] = replace(current, run=code)
        except (ValidationError, ArgumentParsingError, ValidatorFailed) as e:
            raise InstallError(f"Invalid definition: {e}") from e
    if not count:
        raise InstallError(
            "The file has no top-level fenced .add, .edit or .set definitions."
        )
    return InstallPlan(
        source,
        server_id,
        user_id,
        tuple(Change(name, original[name], entry) for name, entry in planned.items()),
        tuple(skipped),
    )


def apply_plan(db: DB, plan: InstallPlan) -> None:
    if not plan.changed:
        return

    def transform(rows: list[Entry]) -> list[Entry]:
        for change in plan.changes:
            current = [
                row
                for row in rows
                if row.name == change.name
                and (
                    row.server_id == plan.server_id
                    if plan.server_id is not None
                    else row.server_id is None and row.user_id == plan.user_id
                )
            ]
            if current != ([] if change.before is None else [change.before]):
                raise InstallError(
                    f"Alias {change.name} changed since the preview. Run .install again."
                )
        by_id = {c.after.id: c.after for c in plan.changed}
        result = [by_id.pop(row.id, row) for row in rows]
        return [*result, *by_id.values()]

    # The callback and commit share the lock used by ordinary alias writes.
    db.remember.batch(transform)
    actions = [
        Action(
            datetime.now(), plan.user_id, ActionInstall("install", c.before, c.after)
        )
        for c in plan.changed
    ]
    db.log.batch(lambda rows: [*rows, *actions])


def review_text(plan: InstallPlan) -> str:
    lines = [
        "Definitions are processed in order without running their code.",
        "Inside install, .add creates an alias or replaces its content; existing code stays.",
        "",
        "Definitions:",
    ]
    for change in plan.changes:
        fields = ", ".join(
            "content replacement" if f == "content" else "code replacement"
            for f in change.fields
        )
        lines.append(
            f"{change.name}: {'new' if change.before is None else fields or 'unchanged'}"
        )
        for field in change.fields:
            before = str(getattr(change.before, field) or "") if change.before else ""
            after = str(getattr(change.after, field) or "")
            lines.extend(
                difflib.unified_diff(
                    before.splitlines(keepends=True),
                    after.splitlines(keepends=True),
                    fromfile=f"old/{change.name}/{field}",
                    tofile=f"new/{change.name}/{field}",
                )
            )
            # The complete repr also preserves trailing newlines and None versus empty code.
            lines.append(
                f"Full old {field}: {getattr(change.before, field)!r}"
                if change.before
                else f"Full old {field}: <absent>"
            )
            lines.append(f"Full new {field}: {getattr(change.after, field)!r}")
    lines.extend(["", "Skipped examples (not executed):", *plan.skipped])
    return "\n".join(lines)

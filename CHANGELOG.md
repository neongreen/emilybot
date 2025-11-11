# Changelog

## 2025-11-11

**Internal improvements:**

- Refactored command parser to eliminate discord.py dependency for pure parsing logic
  - Extracted StringView implementation to standalone module
  - Added comprehensive unit tests for argument parsing
  - Improved error handling with explicit exception types
  
**JS execution:**

- JavaScript imports now support additional registries:
  - `jsr.io` (for JSR packages)
  - `registry.npmjs.org` (for npm packages)
  - Previously only `esm.sh` was supported

## 2025-08-24

- New functions are available in the global JS scope:
  - `print()` -- equivalent to `console.log()`
  - `random([x,y,z,...])` -- picks a random element from the given array
  - `random(min, max)` -- picks a random integer between `min` and `max` inclusive
  - `min()` and `max()` -- equivalent to `Math.min()` and `Math.max()`
  - `shuffle()` -- returns a shuffled copy of the given array
  - `tail()` and `init()` -- return the array without the first / last element
  - `drop()` and `dropLast()` -- return the array without the first / last N elements

## 2025-08-12

- On success, commands now react with a checkmark.

## 2025-08-10

**JS execution:**

- JavaScript `import` statements are now supported, but only from `esm.sh` URLs.
  For example, you can use `import { camelCase } from 'https://esm.sh/change-case@5.4.0'`.

- Timeout is bumped to 5s.

- Memory limit is bumped to 10 MB.

## 2025-08-09

**JS execution:**

- `$foo("a", "b")` and other messages starting with `$` are now treated as JavaScript code to execute.
- Also, `$ <arbitrary code>` is treated as JavaScript code to execute.
- All commands are now available in JS as `$foo` objects.
  - For nested commands, `foo/bar` is available as `$foo.bar`.
    The old `$.cmd("foo/bar")` is still supported but deprecated.
  - For commands with dashes, `foo-bar` is available as `$foo_bar`.
  - Arguments are passed in `args`, e.g. when running `$foo a b`, `args` will be `["a", "b"]`.
- Message, user, and server info are now available as `message`, `user`, and `server` objects.
- Reply info is now available as `reply_to` object.

**`$` prefix:**

- When a message looks like a command and not like JS, e.g. `$hello` or `$rand 1 2`, it's treated as a command invocation.

**Listing children:**

- `$foo/`, `$foo.`, `$foo..` now list children of `$foo`.

**Command names:**

- Command names, including all path components, can no longer start with `_`.
  For example, `_foo` or `foo/_bar` are no longer valid.

- Command names can no longer contain e.g. double slashes, `foo//bar` is no longer valid.

**Dev:**

- Added more debug logging.
- `#$` is now the debug prefix.

**Other:**

- The message is now truncated to 2000 characters.

## 2025-08-02

- BREAKING: Commands can access info about their own invocation via `this` instead of `context`.
- BREAKING: `.show` shows command structure instead of running it.
- Commands now have access to `$.message`, `$.user`, and `$.server`.
- Commands can access other commands' content using `$.commands[name]`.
- Commands can be called from JS using `$.cmd(name)`.

## 2025-08-01

- Added `.run [code]` command to execute JavaScript code directly without creating an alias.

## 2025-07-31

- Added docs, see [docs/README.md](docs/README.md).
- Demoted aliases now don't show up in help at all.

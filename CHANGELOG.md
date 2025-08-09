# Changelog

## 2025-08-09

- `$foo("a", "b")` and other messages starting with `$` are now treated as JavaScript code to execute.
- ...except for stuff like `$foo a b c` which is treated as a command invocation.
- `$foo` can now be used in JS instead of `$.cmd("foo")`.

## 2025-08-02

- Added support for `$` prefix as an alternative to `.` for accessing aliases (e.g., `$weather` works the same as `.weather`).
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

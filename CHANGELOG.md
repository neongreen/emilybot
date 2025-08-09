# Changelog

## 2025-08-09

**JS execution:**

- `$foo("a", "b")` and other messages starting with `$` are now treated as JavaScript code to execute.
- Also, `$ <arbitrary code>` is treated as JavaScript code to execute.
- All commands are now available in JS as `$foo` objects.
  - For nested commands, `foo/bar` is available as `$foo.bar`.
    The old `$.cmd("foo/bar")` is still supported but deprecated.
  - For commands with dashes, `foo-bar` is available as `$foo_bar`.
  - Arguments are passed in `args`, e.g. when running `$foo a b`, `args` will be `["a", "b"]`.

**`$` prefix:**

- When a message looks like a command and not as JS, e.g. `$hello` or `$rand 1 2`, it's treated as a command invocation.

**Listing children:**

- `$foo/`, `$foo.`, `$foo..` now list children of `$foo`.

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

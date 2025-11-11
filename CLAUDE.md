# Guidelines for Claude

## Pre-Push Checklist

**ALWAYS run these commands before pushing code:**

```bash
# 1. Run type checking
mise run check:pyright

# 2. Run Python tests
mise run test:python

# 3. Run JavaScript tests
mise run test:js

# 4. Check linting
mise run check:ruff
mise run check:deno
```

Or run all checks at once:

```bash
mise run check
mise run test
```

## Code Formatting

Code formatting and unused imports are **automatically fixed** on the main branch via GitHub Actions.

- **Don't worry about formatting or unused imports** - they're auto-fixed on main
- If you want to format manually: `mise run fmt`
- Formatting checks are **not** part of CI - they're auto-fixed instead
- Unused imports are **automatically removed** (not checked by pyright)

## Common Commands

```bash
# Run the bot in dev mode
mise run dev

# Format code locally (optional)
mise run fmt

# Run all checks
mise run check

# Run all tests
mise run test

# Type check only
mise run check:pyright

# Lint Python code
mise run check:ruff

# Type check JavaScript
mise run check:deno
```

## Test Coverage

When refactoring or adding features:

1. **Run existing tests** to ensure nothing breaks
2. **Add new tests** for new functionality
3. **Update tests** when changing test fixtures or utilities

## Technical Debt Notes

See the technical debt analysis for known issues and TODOs in the codebase.
Key areas documented:

- TODOs in code (see search results for locations)
- Test fixture duplication (✅ **FIXED** - see test_utils module)
- Deprecated code marked for removal
- Security concerns (prototype pollution in js-executor/lib.ts)

## Import Conventions

**Python:**
- `cast` is from `typing`, not `unittest.mock`
- Always import from absolute paths (enforced by ruff TID252)

**Test Fixtures:**
- Use `make_ctx` from `conftest.py` for all context creation
- Use `ReplyConfig` for message replies
- Use `AuthorConfig` and `GuildConfig` for custom configurations
- See `conftest.py` docstring for examples

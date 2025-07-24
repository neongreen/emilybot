---
inclusion: always
---

# Python Development Guidelines

## Code Architecture

### Class Usage
- Only create classes when there is instance state AND private methods that need to be hidden
- Use classes for stateful components like database connections with specific operations
- Avoid classes for simple utility functions or message formatting - use plain functions instead

### Package Management
- This is a `uv`-only project - never use `pip` for any operations
- All dependency management should be done through `uv` commands

### Import Conventions
- Use absolute imports only: `import emilybot.main` (not `import src.emilybot.main`)
- Never use relative imports
- The `emilybot` package should be directly importable from the project root

## Testing Guidelines

### Mocking Strategy
- Never use `MagicMock` or `patch` for testing
- For components that need mocking, create injectable classes with clear interfaces
- Example: Create a `Discord` class for message operations that can be swapped with a test implementation
- Test implementations should use simple data structures (arrays, dictionaries) for state

### Discord Integration Testing
- For Discord-specific integration tests, use [dpytest](https://github.com/CraftSpider/dpytest)
- Do not create custom `Discord` wrapper classes for integration testing
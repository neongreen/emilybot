# Refactoring Task: Move Remember Logic to Cog

## Overview

Refactor the `.remember`, `.learn`, and `.find` command logic from `main.py` into a dedicated Cog (`remember_cog.py`) using Discord.py's extension system.

## Subtasks

1. **[Completed]**
   - Analyze existing code structure in `main.py`
   - Identify all logic related to remember/learn/find commands
   - Confirm existence of `remember_cog.py` and its current contents

2. **[In Progress]**
   - Create SEARCH/REPLACE blocks to extract:
     - `RememberEntry` dataclass definition
     - `remember_find_for_server()` method
     - `remember_find_for_user()` method
     - `remember_add_for_server()` method
     - `remember_add_for_user()` method
     - `remember_find()` and `remember_add()` wrapper methods
   - Fix indentation errors in current implementation (lines 69, 146)

3. **[Not Started]**
   - Create Cog class structure in `remember_cog.py`
   - Move command implementation functions to Cog
   - Update bot initialization to load Cog via `bot.add_cog()`
   - Add proper type annotations for all parameters
   - Fix type resolution issues for `RememberEntry` and DB methods

4. **[Not Started]**
   - Update command registration to use Cog-based commands
   - Add error handling for Cog initialization
   - Verify all imports are properly maintained
   - Add docstrings for new Cog methods

5. **[Not Started]**
   - Create test cases for Cog functionality
   - Update existing tests in `tests/test_commands.py`
   - Add type checking for Cog methods
   - Verify command functionality after refactoring

## Current Status

- 40% of code extraction complete (indentation errors remain)
- Type annotations need updating in multiple locations
- Command registration still needs to be moved to Cog
- No test updates have been implemented yet

## Next Steps

1. Fix indentation errors in current implementation
2. Create proper Cog class structure in `remember_cog.py`
3. Move command implementation functions to Cog
4. Update bot initialization to load Cog
5. Implement test updates

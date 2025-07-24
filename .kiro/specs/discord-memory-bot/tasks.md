# Implementation Plan

- [x] **1. Create validation utilities for aliases and content**
  - Implement `AliasValidator` class with static methods for alias format and length validation
  - Add content validation for length and emptiness checks
  - Write unit tests in `tests/test_validation.py` using pytest for all validation scenarios including edge cases
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] **2. Enhance database operations for case-insensitive matching**
  - Modify database query methods to store aliases in lowercase
  - Update `remember_find_for_server` and `remember_find_for_user` to use case-insensitive matching
  - Add helper method to normalize alias case before storage and retrieval
  - Write unit tests in `tests/test_database.py` using pytest for case-insensitive alias matching
  - _Requirements: 1.5, 2.4_

- [x] **3. Create response formatting utilities**
  - Use `escape_mentions` from the discord library to escape messages
  - Add method to format "alias not found" error messages with usage instructions
  - Add method to format validation error messages
  - Add an integration test showing that if an entry is remembered and the entry has a mention inside and the output has the mention escaped.
  - _Requirements: 2.2, 2.3, 5.2, 5.4_

- [x] **4. Handle existing command conflicts and cleanup**
  - Rename the existing `where` command (currently shows bot info) to `info` to avoid naming conflicts
  - Remove `list` and `forget` commands from the current implementation
  - _Requirements: 2.1, 5.4_

- [x] **5. Update remember command and create learn alias with validation**
  - Replace existing `remember` command with new implementation that uses validation
  - Create `learn` command as an alias that calls the same functionality as `remember`
  - Add comprehensive input validation before storing data
  - Implement proper error responses for validation failures
  - Ensure aliases are stored with their original case
  - Write integration tests in `tests/test_commands.py` using pytest for both remember and learn commands
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 5.1, 5.2_

- [ ] **6. Update find command and create where alias for content retrieval**
  - Update existing `find` command with new implementation that uses case-insensitive lookup
  - Create `where` command as an alias that calls the same functionality as `find`
  - Implement case-insensitive alias lookup
  - Add mention escaping to retrieved content before sending response
  - Handle "alias not found" scenarios with helpful error messages
  - Write integration tests in `tests/test_commands.py` using pytest for both find and where commands
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 5.3, 5.4_

- [x] **7. Ensure proper namespace isolation for servers and DMs**
  - Server-specific alias storage works correctly with existing database methods
  - User-specific DM alias storage works correctly with existing database methods
  - Basic namespace isolation is already implemented in current code
  - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3_

- [ ] **8. Add comprehensive error handling and logging**
  - Implement try-catch blocks around database operations
  - Add logging for validation failures and database errors
  - Ensure all error scenarios provide user-friendly feedback
  - Add error handling for edge cases like database corruption
  - Write tests in `tests/test_commands.py` using pytest for error handling scenarios
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] **9. Implement dpytest for Discord integration testing**
  - Add dpytest dependency to dev dependencies in pyproject.toml
  - Create `tests/test_discord_integration.py` using dpytest for Discord-specific integration tests
  - Configure dpytest properly with the bot instance following dpytest documentation
  - Test actual Discord command execution flow (help, info, remember, learn, find commands)
  - Test Discord-specific features like mention escaping in real Discord context
  - Test error handling for unknown commands and missing arguments
  - Test case-insensitive alias lookup through Discord commands
  - Test namespace isolation between different Discord contexts
  - Follow Python guidelines: no MagicMock/patch usage, use dpytest's built-in testing capabilities
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3_

- [ ] **10. Write comprehensive integration tests**
  - Create test scenarios in `tests/test_integration.py` using pytest that verify complete remember/where workflows
  - Test complete learn/find workflows
  - Test server namespace isolation with multiple servers
  - Test user DM namespace isolation with multiple users
  - Test data persistence scenarios
  - Verify command aliases work identically
  - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 6.1, 6.2, 6.3_

- [ ] **11. Update documentation and help system**
  - Update the help command to document the new remember/learn and find/where functionality
  - Add usage examples for all four commands (remember, learn, find, where)
  - Document the namespace behavior (server vs DM isolation)
  - Add command descriptions that explain the aliases work identically
  - _Requirements: 5.4_

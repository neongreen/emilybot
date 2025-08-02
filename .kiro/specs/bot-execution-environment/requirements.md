# Requirements Document

## Introduction

This feature defines a JavaScript execution environment for a Discord bot that provides users with access to stored commands, execution context (user, message, server info), and utility functions through a global `$` object. The environment must be discoverable since users interact through Discord messages without autocomplete, making it essential that the entire API can be explored by typing commands like `console.log($)`.

## Requirements

### Requirement 1

**User Story:** As a Discord user, I want to access stored commands from my JavaScript code, so that I can reuse and build upon existing functionality.

#### Acceptance Criteria

1. WHEN a user executes JavaScript code THEN the system SHALL provide access to all defined commands through a global `$` object
2. WHEN a user accesses `$.commandName` THEN the system SHALL return the stored command function or content for valid JavaScript identifiers
3. WHEN a user accesses `$['command-name']` THEN the system SHALL return the stored command function or content for names with special characters
4. WHEN a user calls `$('command-name')` THEN the system SHALL return the stored command function or content for any command name
5. WHEN a user accesses a non-existent command THEN the system SHALL throw a clear error message

### Requirement 2

**User Story:** As a Discord user, I want to access execution context information (who ran the command, message content, server, timestamp), so that my JavaScript code can respond appropriately to the current situation.

#### Acceptance Criteria

1. WHEN a user executes JavaScript code THEN the system SHALL provide access to execution context through `$.ctx`
2. WHEN a user accesses `$.ctx.userId` THEN the system SHALL return the Discord user ID of the command executor
3. WHEN a user accesses `$.ctx.messageContent` THEN the system SHALL return the exact contents of the triggering message
4. WHEN a user accesses `$.ctx.serverId` THEN the system SHALL return the Discord server ID where the command was executed
5. WHEN a user accesses `$.ctx.timestamp` THEN the system SHALL return the current execution timestamp
6. WHEN a user accesses `$.ctx.user` THEN the system SHALL provide an object containing user information including id and name

### Requirement 3

**User Story:** As a Discord user, I want to discover all available functionality by inspecting the global object, so that I can learn what's available without external documentation.

#### Acceptance Criteria

1. WHEN a user executes `console.log($)` THEN the system SHALL display all available commands, context, and utility categories
2. WHEN a user inspects the global object THEN the system SHALL show command properties, context object, and utility object
3. WHEN a user explores the API THEN the system SHALL provide clear, discoverable names for all functionality
4. WHEN the global object is serialized THEN the system SHALL present the information in a readable format for Discord messages

### Requirement 4

**User Story:** As a Discord user, I want access to common utility functions without cluttering the main command namespace, so that I can perform common operations efficiently while maintaining API clarity.

#### Acceptance Criteria

1. WHEN a user needs utility functions THEN the system SHALL provide them through `$.lib`
2. WHEN a user calls utility functions like `$.lib.random(min, max)` THEN the system SHALL provide convenient wrappers for common operations
3. WHEN a user inspects `$.lib` THEN the system SHALL show all available utility functions
4. WHEN utility functions are added THEN the system SHALL maintain discoverability through object inspection

### Requirement 5

**User Story:** As a Discord bot administrator, I want the execution environment to be extensible for future categories of functionality, so that new features can be added without breaking existing code.

#### Acceptance Criteria

1. WHEN new functionality categories are needed THEN the system SHALL support adding them as new properties on the `$` object
2. WHEN the system is extended THEN the system SHALL maintain the discoverability principle for all new functionality
3. WHEN new categories are added THEN the system SHALL follow consistent naming and access patterns
4. WHEN the execution environment evolves THEN the system SHALL preserve backward compatibility for existing commands and context access

### Requirement 6

**User Story:** As a Discord user, I want short, convenient property names for frequently used context information, so that my code is concise and easy to type on mobile devices.

#### Acceptance Criteria

1. WHEN accessing user information THEN the system SHALL provide `$.ctx.user.id` and `$.ctx.user.name` as convenient access to user details
2. WHEN accessing message content THEN the system SHALL provide reasonably short property names
3. WHEN accessing server information THEN the system SHALL balance brevity with clarity
4. WHEN property names are chosen THEN the system SHALL prioritize typing convenience for Discord message context
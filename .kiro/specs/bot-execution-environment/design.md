# Design Document

## Overview

This design implements a comprehensive JavaScript execution environment for a Discord bot that provides users with access to stored commands, execution context, and utility functions through a global `$` object. The design builds upon the existing JavaScript execution infrastructure using Deno and QuickJS, extending it to provide a discoverable and user-friendly API.

The core principle is discoverability - users can type `console.log($)` in their JavaScript code to see all available functionality, making the environment self-documenting for Discord users who don't have access to traditional IDE features like autocomplete.

## Architecture

### Current System Overview

The existing system consists of:
- **Python Layer**: Discord bot commands (`run.py`, `show.py`) that handle user input
- **JavaScript Executor**: Python service (`javascript_executor.py`) that manages Deno subprocess execution
- **Deno Runtime**: TypeScript execution environment (`js-executor/`) using QuickJS for sandboxed execution
- **Database**: JSON-based storage for user-created aliases/commands

### QuickJS Emscripten Integration

The system uses QuickJS Emscripten for JavaScript execution, which provides:
- **Sandboxed Execution**: Each QuickJSContext has its own isolated environment
- **Memory Management**: Manual handle disposal required for all QuickJS objects
- **API Exposure**: Host functions exposed via `vm.newFunction()` and `vm.setProp()`
- **Resource Limits**: Runtime-level memory and CPU limits

### New Architecture Components

The new design adds a **Global Context Provider** that properly injects the `$` object using QuickJS Emscripten APIs:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Discord Bot   │───▶│ JavaScript       │───▶│ Deno Runtime    │
│   Commands      │    │ Executor         │    │ + QuickJS       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Global Context   │    │ QuickJS Handle  │
                       │ Provider         │    │ Management      │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Database Query   │    │ User JavaScript │
                       │ Service          │    │ Code Execution  │
                       └──────────────────┘    └─────────────────┘
```

## Components and Interfaces

### 1. Global Context Provider

**Location**: `js-executor/global-context.ts`

**Responsibilities**:
- Create and populate the `$` global object
- Query database for available commands
- Inject execution context
- Provide utility functions

**Interface**:
```typescript
interface GlobalContextProvider {
  createGlobalContext(
    executionContext: ExecutionContext,
    commandsData: Map<string, string>
  ): GlobalContext;
}

interface GlobalContext {
  // Command access
  [commandName: string]: string | Function;
  (commandName: string): string;
  
  // Execution context
  ctx: {
    userId: number;
    messageContent?: string;
    serverId?: number;
    timestamp: string;
    user: {
      id: number;
      name: string;
    };
  };
  
  // Utility functions
  lib: {
    random(min: number, max: number): number;
    // Additional utilities as needed
  };
}
```

### 2. Command Query Service

**Location**: `src/emilybot/command_query_service.py`

**Responsibilities**:
- Query database for all available commands for a user/server
- Format command data for JavaScript consumption
- Handle command name normalization

**Interface**:
```python
class CommandQueryService:
    def __init__(self, db: DB):
        self.db = db
    
    def get_available_commands(
        self, 
        user_id: int, 
        server_id: Optional[int]
    ) -> Dict[str, str]:
        """Return mapping of command names to their content."""
        pass
```

### 3. Enhanced JavaScript Executor

**Location**: Extend existing `js-executor/executor.ts`

**Responsibilities**:
- Inject the `$` global object using QuickJS Emscripten APIs
- Handle proper memory management for all QuickJS handles
- Provide error handling for command access
- Manage QuickJS context lifecycle

**Key Changes**:
- Use `vm.newObject()` and `vm.setProp()` to create the `$` object structure
- Implement proper handle disposal using `Scope.withScope()` or `.consume()`
- Add command callable function using `vm.newFunction()`
- Use QuickJS property descriptors for immutability
- Follow QuickJS Emscripten best practices for memory management

**QuickJS Integration Details**:
```typescript
// Example of proper $ object injection
const dollarHandle = vm.newObject();

// Add context properties
const ctxHandle = vm.newObject();
vm.setProp(ctxHandle, "userId", vm.newNumber(context.userId));
vm.setProp(dollarHandle, "ctx", ctxHandle);

// Add command function
const commandFnHandle = vm.newFunction("$", (nameHandle) => {
  const commandName = vm.getString(nameHandle);
  // Command resolution logic
  return vm.newString(commandContent);
});
vm.setProp(vm.global, "$", commandFnHandle);

// Proper cleanup
ctxHandle.dispose();
dollarHandle.dispose();
commandFnHandle.dispose();
```

### 4. Context Enhancement

**Location**: Extend existing `js-executor/context.ts`

**Responsibilities**:
- Add user name resolution to execution context
- Extend context types to include message content and timestamp
- Support both existing and new context formats

## Data Models

### Enhanced Execution Context

```typescript
// Extend existing context types
interface EnhancedAliasRunContext extends AliasRunContext {
  messageContent: string;
  timestamp: string;
  userName: string;
}

interface EnhancedRunCommandContext extends RunCommandContext {
  messageContent: string;
  timestamp: string;
  userName: string;
}
```

### Global Object Structure

```typescript
interface DollarGlobal {
  // Dynamic command properties
  [key: string]: string | Function;
  
  // Function call interface
  (commandName: string): string;
  
  // Execution context
  ctx: {
    userId: number;
    messageContent: string;
    serverId: number | null;
    timestamp: string;
    user: {
      id: number;
      name: string;
    };
  };
  
  // Utility library
  lib: {
    random(min: number, max: number): number;
    print(...args: any[]): void;
  };
}
```

### Command Storage Format

Commands are stored in the existing `Entry` database structure:
- `name`: Command identifier (normalized to lowercase)
- `content`: Command content/code
- `run`: Optional JavaScript code for dynamic commands
- `user_id`: Owner of the command
- `server_id`: Server context (null for DM commands)

## Error Handling

### Command Access Errors

1. **Non-existent Command**: Throw `ReferenceError` with helpful message using QuickJS error handling
2. **Permission Errors**: Commands are scoped to user/server context
3. **Execution Errors**: Existing error handling for JavaScript execution

### Context Access Errors

1. **Missing Context**: Graceful fallback to null/undefined values
2. **Type Errors**: Proper TypeScript typing prevents most issues

### Discovery Errors

1. **Serialization Issues**: Ensure `$` object can be safely serialized for `console.log()`
2. **Circular References**: Ensure the `$` object structure doesn't reference itself or create infinite loops that would break `console.log()` output

### QuickJS Memory Management Errors

1. **Handle Leaks**: All QuickJS handles must be properly disposed to prevent memory leaks
2. **Runtime Errors**: QuickJSContext.dispose() will throw RuntimeError if handles are not disposed
3. **Resource Cleanup**: Use `Scope.withScope()` or `.consume()` patterns for automatic cleanup

### Security and Isolation

1. **Immutable Global Object**: Use QuickJS property descriptors to make `$` object read-only
2. **Command Isolation**: Each execution gets a fresh QuickJS context to prevent interference
3. **Property Protection**: QuickJS handles provide natural isolation between executions
4. **Memory Limits**: Runtime-level memory limits prevent resource exhaustion

## Testing Strategy

### Unit Tests

1. **Global Context Provider Tests**
   - Test `$` object creation with various command sets
   - Test context injection with different execution contexts
   - Test utility function availability
   - Test proper QuickJS handle disposal

2. **Command Query Service Tests**
   - Test database querying with different user/server combinations
   - Test command name normalization
   - Test empty result handling

3. **Enhanced Executor Tests**
   - Test command access via property notation
   - Test command access via bracket notation
   - Test command access via function call
   - Test error handling for non-existent commands
   - Test `$` object immutability (cannot be overwritten or modified)
   - Test command isolation (commands cannot interfere with each other's `$` object)
   - Test QuickJS handle cleanup

### QuickJS-Specific Tests

1. **Handle Lifecycle Tests**
   - Test proper disposal of object handles, function handles, and string handles
   - Test `Scope.withScope()` usage for automatic cleanup
   - Test `.consume()` pattern for immediate disposal

### Integration Tests

1. **End-to-End Command Execution**
   - Test full flow from Discord command to JavaScript execution
   - Test command discovery via `console.log($)`
   - Test context access in real execution environment

2. **Database Integration**
   - Test with real database entries
   - Test command scoping (user/server isolation)
   - Test command updates and cache invalidation

### Discovery Tests

1. **API Exploration**
   - Test `console.log($)` output format
   - Test `console.log($.ctx)` context display
   - Test `console.log($.lib)` utility display

2. **User Experience**
   - Test command access patterns users will actually use
   - Test command scoping (user/server isolation works correctly)

## Implementation Phases

### Phase 1: Core Infrastructure
- Implement Global Context Provider using QuickJS Emscripten APIs
- Extend execution context types
- Add basic command querying
- Set up proper memory management patterns

### Phase 2: QuickJS Integration
- Implement `$` object injection using `vm.newObject()` and `vm.setProp()`
- Add proper handle disposal using `Scope.withScope()` or `.consume()`
- Implement command callable function using `vm.newFunction()`
- Add QuickJS-specific error handling

### Phase 3: Context Enhancement
- Add user name resolution
- Add message content and timestamp
- Implement `$.ctx` object using QuickJS object handles
- Ensure proper cleanup of context handles

### Phase 4: Utilities and Polish
- Implement `$.lib` utility functions using QuickJS function handles
- Optimize discovery output formatting
- Add comprehensive error messages
- Implement property descriptors for immutability

### Phase 5: Testing and Documentation
- Handle lifecycle testing for proper cleanup
- Complete user-facing documentation explaining all `$` object behavior
- Examples showing common usage patterns and proper cleanup
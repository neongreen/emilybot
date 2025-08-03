# Emily JavaScript API Reference

Emily provides a sandboxed JavaScript execution environment for dynamic commands and data processing.
All JavaScript code runs with strict security limits and can only produce output through `console.log()`.

> **Note**: This documentation includes source code references. The actual implementation may be found in the linked files.

## Global Object: `$`

The `$` object is the primary interface for accessing commands, context, and utilities within JavaScript code.

### Command Access

Access stored commands through the `$.commands` object:

```javascript
// Access command objects through $.commands
$.commands.hello // For valid JavaScript identifiers
$.commands["hello"] // Also works with bracket notation
$.commands["api/auth"] // Required for names with special characters
$.commands["user-settings"]

// Each command object has properties:
$.commands.hello.name // "hello"
$.commands.hello.content // The stored text content
$.commands.hello.code // JavaScript code (if set with .set alias.run)
$.commands.hello.run() // Function to execute the command
```

> **Implementation source**:
> Commands are stored in `$commandsMap__` and exposed via `$.commands` in [`js-executor/executor.ts:49-75`](../js-executor/executor.ts#L49-L75)

#### Calling Commands

Use `$.cmd(name)` to execute another command:

```javascript
// Execute the 'weather' command
$.cmd("weather")

// Execute commands with special characters
$.cmd("api/auth")
```

> **Implementation source**: The `$.cmd()` function is defined in [`js-executor/executor.ts:52-57`](../js-executor/executor.ts#L52-L57)

### Context Information: `$.ctx`

Access execution context through `$.ctx`:

```javascript
$.ctx.user.id // Discord user ID (string)
$.ctx.user.name // User's display name
$.ctx.server.id // Discord server ID (string, null in DMs)
$.ctx.message.text // The original message content
```

> **Implementation source**:
> Context is passed as `fields` and duplicated as `ctx` in [`src/emilybot/execute/javascript_executor.py:119`](../src/emilybot/execute/javascript_executor.py#L119) and injected via `$[key] = $init__.fields[key]` in [`js-executor/executor.ts:59-61`](../js-executor/executor.ts#L59-L61)

### Utility Functions: `$.lib`

Built-in utility functions for common operations:

```javascript
// Generate random integer (inclusive)
$.lib.random(1, 10) // Returns 1-10
$.lib.random(0, 100) // Returns 0-100
```

> **Implementation source**:
> Library functions are defined in [`js-executor/lib.ts`](../js-executor/lib.ts) and added to context in [`js-executor/main.ts:46`](../js-executor/main.ts#L46)

## Legacy Context Object

> [!WARNING]
> **Deprecated**: The `context` global variable is deprecated and will be removed in a future version.
> Use the `$` global object instead.

For commands with `.run` attribute, a `context` object provides backwards compatibility:

```javascript
context.content // Original entry content
context.name // Entry/command name
```

## Usage Examples

### Basic Command Execution

```javascript
// Execute a weather command using $.cmd()
$.cmd("weather")

// Access command content directly
console.log("Weather info:", $.commands.weather.content)

// Execute command's run function if it has JavaScript code
$.commands.weather.run()
```

### Dynamic Content Generation

```javascript
// Count lines in a todo list (using specific command)
let items = $.commands.todo.content.split("\n").filter(Boolean)
console.log(`📝 ${items.length} tasks remaining`)

// Random quote selector
let quotes = $.commands.quotes.content.split("\n").filter(Boolean)
let randomQuote = quotes[$.lib.random(0, quotes.length - 1)]
console.log(randomQuote)
```

### Context-Aware Responses

```javascript
// Personalized greeting
console.log(`Hello ${$.ctx.user.name}!`)

// Server-specific behavior
if ($.ctx.server.id) {
  console.log("Running in server:", $.ctx.server.id)
} else {
  console.log("Running in DM")
}
```

### Command Discovery

```javascript
// List all available commands
console.log($.commands)

// Show available command names
console.log(Object.keys($.commands))

// Show utility functions
console.log($.lib)

// Display context information
console.log($.ctx)

// Show entire $ object structure
console.log($)
```

### Advanced Examples

**Weather with emoji enhancement:**

```javascript
// Access weather command content directly
console.log("🌤️ " + $.commands.weather.content)
// Output: 🌤️ Sunny, 72°F
```

**Task counter with progress:**

```javascript
// Count tasks from todo command
let items = $.commands.todo.content.split("\n").filter(Boolean)
let completed = items.filter(item => item.startsWith("✅")).length
console.log(`📝 ${items.length} tasks (${completed} completed)`)
```

**Command chaining:**

```javascript
// Use one command's content in another
let apiBase = $.commands.apiUrl.content
let endpoint = $.commands.currentEndpoint.content
console.log(`Full URL: ${apiBase}${endpoint}`)
```

## Execution Environment

### Limits

- **Timeout**: 1 second maximum execution time
- **Memory**: 1MB memory limit
- **Network**: No network access
- **File System**: No file system access
- **Output**: Only `console.log()` produces visible output

### Security

- Sandboxed execution using QuickJS WASM
- No access to host system or other processes
- Each execution runs in isolated context
- Commands scoped to user/server permissions

### Error Handling

```javascript
// Commands that don't exist throw errors when accessed via $.cmd()
try {
  $.cmd("nonexistentCommand")
} catch (e) {
  console.log("Command not found:", e.message)
}

// Accessing non-existent commands via $.commands returns undefined
console.log($.commands.nonexistent) // undefined
```

> **Implementation source**:
> Error handling for `$.cmd()` is in [`js-executor/executor.ts:53-55`](../js-executor/executor.ts#L53-L55)

## Code Formats

JavaScript code can be provided in several formats:

```
.set weather.run console.log("🌤️ " + $.commands.weather.content)
```

````
.set weather.run
```
console.log("🌤️ " + $.commands.weather.content)
```
````

````
.set weather.run
```javascript
console.log("🌤️ " + $.commands.weather.content)  
```
````

## Common Patterns

### Conditional Logic

```javascript
// Access command content directly for conditional logic
let weatherContent = $.commands.weather.content
if (weatherContent.includes("rain")) {
  console.log("🌧️ Don't forget your umbrella!")
} else {
  console.log("☀️ Have a great day!")
}
```

### Data Processing

```javascript
// Parse CSV-like data from a specific command
let lines = $.commands.dataTable.content.split("\n")
let total = lines
  .map(line => parseFloat(line.split(",")[1]))
  .filter(num => !isNaN(num))
  .reduce((sum, num) => sum + num, 0)
console.log("Total:", total)
```

### Random Selection

```javascript
// Random item from a command's content
let options = $.commands.quotes.content.split("\n").filter(Boolean)
let choice = options[$.lib.random(0, options.length - 1)]
console.log("Random choice:", choice)
```

## What Doesn't Work

To avoid confusion, here are common patterns that do NOT work:

### Direct Command Property Access

```javascript
// ❌ These DON'T work - commands are not direct properties of $
$.weather
$.apiDocs
$["weather"]

// ✅ Use this instead
$.commands.weather
$.commands["weather"]
```

### Function Call Syntax for $

```javascript
// ❌ This doesn't work - $ is not a function
$("weather")

// ✅ Use this instead
$.cmd("weather")
```

> **Implementation note**:
> Commands are stored in `$.commands` object, not as direct properties of `$`.
> The `$` object itself is not callable as a function. See the executor implementation in [`js-executor/executor.ts`](../js-executor/executor.ts) for details.

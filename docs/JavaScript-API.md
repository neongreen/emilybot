# Emily JavaScript API Reference

Emily provides a sandboxed JavaScript execution environment for dynamic commands and data processing.
All JavaScript code runs with strict security limits and can only produce output through `console.log()`.

> **Note**: This documentation includes source code references. The actual implementation may be found in the linked files.

## Import System

Emily supports importing external JavaScript modules from [esm.sh](https://esm.sh), a CDN that provides ES modules for npm packages.

### Supported Import Sources

Only modules from `https://esm.sh` are allowed for security reasons. Attempts to import from other sources will result in an error.

### Import Syntax

Both static and dynamic import syntaxes are supported:

```javascript
// Static imports (automatically transformed to dynamic imports)
import { camelCase } from 'https://esm.sh/change-case@5.4.0'
console.log(camelCase("hello world")) // Outputs: helloWorld

// Dynamic imports
const { camelCase } = await import('https://esm.sh/change-case@5.4.0')
console.log(camelCase("hello world")) // Outputs: helloWorld

// Default imports
import lodash from 'https://esm.sh/lodash-es@4.17.21'
console.log(lodash.sum([1, 2, 3])) // Outputs: 6

// Namespace imports
import * as utils from 'https://esm.sh/date-fns@2.30.0'
console.log(utils.format(new Date(), 'yyyy-MM-dd'))
```

### Import Transformation

Static imports are automatically transformed into dynamic imports to work within the execution context:

```javascript
// This static import:
import { camelCase } from 'https://esm.sh/change-case@5.4.0'

// Is automatically transformed to:
const { camelCase } = await import('https://esm.sh/change-case@5.4.0')
```

### Error Handling

Import errors are handled gracefully:

```javascript
try {
  const module = await import('https://esm.sh/nonexistent-package@1.0.0')
} catch (error) {
  console.log("Import failed:", error.message)
}

// Attempting to import from non-esm.sh sources will throw an error:
// const module = await import('https://esm.run/some-package') // Error: Only esm.sh urls are supported
```

### Common Use Cases

**Text Processing:**
```javascript
import { camelCase, kebabCase, snakeCase } from 'https://esm.sh/change-case@5.4.0'

console.log(camelCase("hello world"))     // helloWorld
console.log(kebabCase("hello world"))     // hello-world
console.log(snakeCase("hello world"))     // hello_world
```

**Date Manipulation:**
```javascript
import { format, addDays, differenceInDays } from 'https://esm.sh/date-fns@2.30.0'

const today = new Date()
const tomorrow = addDays(today, 1)
console.log("Tomorrow:", format(tomorrow, 'yyyy-MM-dd'))
```

**Utility Functions:**
```javascript
import { debounce, throttle } from 'https://esm.sh/lodash-es@4.17.21'

const debouncedLog = debounce(console.log, 1000)
debouncedLog("This will only log once per second")
```

> **Implementation source**: Import functionality is implemented in [`js-executor/imports.ts`](../js-executor/imports.ts) and integrated via the module loader in [`js-executor/executor.ts:25`](../js-executor/executor.ts#L25). Import transformation is handled in [`js-executor/parse.ts`](../js-executor/parse.ts).

---

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

#### Command Arguments

Commands can accept arguments when called:

```javascript
// Call a command with arguments
$.cmd("greeting", "Alice", "Bob") // Pass arguments to the greeting command
$.commands.greeting.run("Alice", "Bob") // Same as above

// Inside a command's JavaScript code, arguments are available:
// - `args` - Array of arguments passed to the command

// Example command that uses arguments:
// .set greeting.run console.log("Hello " + args[0] + " and " + args[1] + "!")
// $greeting Alice Bob  // Outputs: Hello Alice and Bob!
```

> **Implementation source**:
> Commands are stored in `$commandsMap__` and exposed via `$.commands` in [`js-executor/executor.ts:49-75`](../js-executor/executor.ts#L49-L75)

### Global Command Objects

Every command is also available as a global variable:

```javascript
// Direct access to commands as global variables
$weather // The weather command object
$weather() // Call the weather command
$weather._name // "weather"
$weather._content // The command's content
$weather._code // JavaScript code (if set)
$weather._run() // Execute the command's code

// Commands with dashes become underscores
$user_settings // The user-settings command
$user_settings() // Call the user-settings command

// Nested commands are accessible as properties
$docs.api // The docs/api command
$docs.api() // Call the docs/api command
$docs.install // The docs/install command

// Commands can accept arguments
$greeting("Alice", "Bob") // Call greeting with arguments
$greeting._run("Alice", "Bob") // Same as above
```

> **Note**: Command names with dashes (`-`) are converted to underscores (`_`) for global variable access. For example, `user-settings` becomes `$user_settings`.

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

## Dollar Prefix Behavior

When you use the `$` prefix in Discord messages, Emily has special behavior:

1. **If the command exists (built-in or alias)**: Works like the `.` prefix
   ```
   $weather  // Same as .weather (if weather is an alias)
   $help     // Same as .help (built-in command)
   $add test Hello  // Same as .add test Hello (built-in command)
   ```

2. **If the command doesn't exist**: Executes the entire message as JavaScript
   ```
   $console.log("Hello!")  // Executes JavaScript
   $2 + 2                  // Shows: 4
   $new Date().getHours()  // Shows current hour
   ```

3. **All aliases are available as global variables**:
   ```
   $weather()              // Call the weather alias
   $weather._content       // Access weather content
   $docs.api()             // Call nested alias
   ```

4. **Commands can accept arguments**:
   ```
   $greeting Alice Bob     // Equivalent to $greeting("Alice", "Bob")
   $echo Hello World       // Equivalent to $echo("Hello", "World")
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

// Use global command objects
$weather() // Call weather command
$weather._content // Get weather content
```

### Advanced Command Chaining

```javascript
// Chain multiple commands
$console.log("Weather: " + $weather._content + " | Time: " + new Date().toLocaleTimeString())

// Use nested commands
$docs.api() // Call docs/api command
$docs.install() // Call docs/install command

// Conditional execution
if ($weather._content.includes("sunny")) {
    $console.log("It's a beautiful day!")
}
```

### Command Arguments

```javascript
// Create a greeting command that uses arguments
// .set greeting.run console.log("Hello " + args[0] + "! Welcome to " + args[1] + "!")

// Call the command with arguments
$greeting Alice Discord  // Outputs: Hello Alice! Welcome to Discord!

// Access arguments in different ways
// .set echo.run 
// console.log("First arg:", args[0])
// console.log("All args:", args)
// console.log("Args length:", arguments.length)

$echo Hello World Test  // Outputs the arguments in different formats

// Use arguments for dynamic content
// .set welcome.run 
// let name = args[0] || "Guest"
// let role = args[1] || "User"
// console.log("Welcome " + name + "! You are a " + role + ".")

$welcome Alice Admin  // Outputs: Welcome Alice! You are a Admin.
$welcome Bob         // Outputs: Welcome Bob! You are a User.
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

**Using external libraries for text processing:**

```javascript
import { camelCase, kebabCase } from 'https://esm.sh/change-case@5.4.0'

// Process command names
let commandName = $.commands.weather.name
console.log("Camel case:", camelCase(commandName))     // weather
console.log("Kebab case:", kebabCase(commandName))     // weather

// Process user input from context
let userName = $.ctx.user.name
console.log("Formatted name:", camelCase(userName))
```

**Date formatting with external library:**

```javascript
import { format, addDays } from 'https://esm.sh/date-fns@2.30.0'

// Format current date
let today = new Date()
console.log("Today:", format(today, 'EEEE, MMMM do, yyyy'))

// Calculate future dates
let nextWeek = addDays(today, 7)
console.log("Next week:", format(nextWeek, 'MMM do'))
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

- **Timeout**: 5s maximum execution time
- **Memory**: 1MB memory limit
- **Network**: Limited network access for importing modules from `https://esm.sh` only
- **File System**: No file system access
- **Output**: Only `console.log()` produces visible output
- **Imports**: Only ES modules from `https://esm.sh` are supported

### Security

- Sandboxed execution using QuickJS WASM
- No access to host system or other processes
- Each execution runs in isolated context
- Commands scoped to user/server permissions
- **Import restrictions**: Only modules from `https://esm.sh` are allowed for security
- External modules are fetched and executed within the same sandboxed environment

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
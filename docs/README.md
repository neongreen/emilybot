# Emily documentation

Emily stores text snippets under short names called "aliases". You can retrieve them later by typing the alias name.

## Quick start

```
You:    .add jokes Why did the chicken cross the road?
```

```
You:    .jokes
Emily:  Why did the chicken cross the road?
```

You can also use `$` as a prefix instead of `.`:

```
You:    $jokes
Emily:  Why did the chicken cross the road?
```

The `$` prefix has special behavior - if the command doesn't exist, it executes the entire message as JavaScript:

```
You:    $console.log("Hello from JavaScript!")
Emily:  Hello from JavaScript!

You:    $new Date().toLocaleTimeString()
Emily:  2:30:45 PM
```

## Commands

### Storing text

| Command               | What it does            | Example                            |
| --------------------- | ----------------------- | ---------------------------------- |
| `.add [name] [text]` or `$add [name] [text]`  | Store text under a name | `.add manual https://docs.com` or `$add manual https://docs.com`     |
| `.edit [name] [text]` or `$edit [name] [text]` | Replace existing text   | `.edit manual https://newdocs.com` or `$edit manual https://newdocs.com` |
| `.rm [name]` or `$rm [name]`          | Delete an alias         | `.rm manual` or `$rm manual`                       |

### Getting text back

| Command          | What it does                   | Example         |
| ---------------- | ------------------------------ | --------------- |
| `.[name]` or `$[name]` | Show the text                  | `.manual` or `$manual`       |
| `.[name]/` or `$[name]/` | List all children of the alias | `.docs/` or `$docs/`        |
| `.show [name]`   | Same as above                  | `.show manual`  |
| `.random [name]` | Show a random line             | `.random jokes` |
| `.list`          | Show all aliases               | `.list`         |

### JavaScript execution with `$`

| Command          | What it does                   | Example         |
| ---------------- | ------------------------------ | --------------- |
| `$[javascript]`  | Execute JavaScript directly   | `$console.log("Hello!")`     |
| `$[expression]`  | Evaluate and show result      | `$2 + 2`                     |
| `$[function]()`  | Call functions                 | `$new Date().getHours()`     |

### JavaScript

| Command                  | What it does                | Example                                                     |
| ------------------------ | --------------------------- | ----------------------------------------------------------- |
| `.set [name].run [code]` or `$set [name].run [code]` | Add JavaScript to an alias  | `.set weather.run console.log("Today: " + context.content)` or `$set weather.run console.log("Today: " + context.content)` |
| `.run [code]` or `$run [code]`            | Execute JavaScript directly | `.run console.log("Hello, world!")` or `$run console.log("Hello, world!")`                         |

When you use an alias that has attribute `run`, instead of showing the text it will execute the code.
Everything printed with `console.log` will be shown in the chat.

See [JavaScript execution](#javascript-execution) for more details, or see the comprehensive [JavaScript API Reference](JavaScript-API.md) for complete documentation.

### Organization

| Command           | What it does                              | Example             |
| ----------------- | ----------------------------------------- | ------------------- |
| `.promote [name]` or `$promote [name]` | Show the alias and its first line in help | `.promote docs` or `$promote docs`     |
| `.demote [name]` or `$demote [name]`  | Don't list in help, only in `.list`       | `.demote old-stuff` or `$demote old-stuff` |
| `.demote_all` or `$demote_all`     | Demote all aliases                        | `.demote_all` or `$demote_all`       |
| `.help` or `$help`           | Show all commands and promoted aliases    | `.help` or `$help`             |

## Anatomy of an alias

Each alias stores:

| Field          | What it is                 | Example                               |
| -------------- | -------------------------- | ------------------------------------- |
| **name**       | The alias name (lowercase) | `weather`                             |
| **content**    | The text you stored        | `Sunny, 75°F`                         |
| **run**        | JavaScript code (optional) | `console.log("🌤️ " + context.content)` |
| **promoted**   | Show in help prominently?  | `true` or `false`                     |
| **created_at** | When you made it           | `2025-01-29T12:00:00Z`                |
| **user_id**    | Your Discord ID            | `123456789`                           |
| **server_id**  | Which server (or DM)       | `987654321` or `null`                 |

## Paths and fake folders

You can organize aliases with `/` like folders:

```
.add docs Main documentation
.add docs/api API reference  
.add docs/install How to install
.add docs/troubleshoot Common problems
```

### Listing "folders"

```
.show docs/
# Shows:
# Found 3 entries for 'docs/':
# - docs/api: API reference
# - docs/install: How to install  
# - docs/troubleshoot: Common problems
```

### How promotion works

Only top-level aliases (no `/`) can be promoted:

| Alias      | Can promote? | Why             |
| ---------- | ------------ | --------------- |
| `docs`     | ✅ Yes       | No `/` in name  |
| `docs/api` | ❌ No        | Has `/` in name |
| `weather`  | ✅ Yes       | No `/` in name  |

When you promote `docs`, all `docs/*` aliases follow its promotion status.

Currently, if an alias doesn't exist but its children do -- e.g. you have `.foo/bar` but don't have `.foo` --
you can't demote it and it will always show up in help.

#### .demote_all

Clean the help to not show any top-level aliases.
Folders will still show up.

#### .help

Display all available commands, promoted aliases, and alias folders.

## JavaScript execution

Add JavaScript to make aliases dynamic:

```
.add weather Sunny, 75°F
.set weather.run console.log("🌤️ Weather: " + context.content)
.weather
# Shows: 🌤️ Weather: Sunny, 75°F
```

> **📖 For complete JavaScript API documentation**: See [JavaScript API Reference](JavaScript-API.md)

### Context and Global Objects

Your JavaScript code has access to two main interfaces:

**Legacy `context` object** (for `.alias.run` commands):

| Property          | What it contains | Example         |
| ----------------- | ---------------- | --------------- |
| `context.content` | The alias text   | `"Sunny, 75°F"` |
| `context.name`    | The alias name   | `"weather"`     |

**Modern `$` global object** (available everywhere):

| Property             | What it contains                   | Example                 |
| -------------------- | ---------------------------------- | ----------------------- |
| `$.ctx.user.name`    | User's display name                | `"JohnDoe"`             |
| `$.ctx.user.id`      | Discord user ID                    | `"123456789"`           |
| `$.ctx.server.id`    | Discord server ID (null in DMs)    | `"987654321"` or `null` |
| `$.ctx.message.text` | The original message content       | `".weather"`            |
| `$.commands`         | All available commands             | `{weather: {...}, ...}` |
| `$.cmd(name)`        | Function to execute other commands | `$.cmd('weather')`      |
| `$.lib.random(a,b)`  | Random integer between a and b     | `$.lib.random(1, 10)`   |

**Command objects** (available as global variables):

Every command is available as a global variable. For example, if you have a command called `weather`, you can access it as `$weather`:

| Property/Method     | What it contains                   | Example                 |
| ------------------- | ---------------------------------- | ----------------------- |
| `$weather`          | Call the command                   | `$weather()`            |
| `$weather._name`    | Command name                       | `"weather"`             |
| `$weather._content` | Command content                    | `"Sunny, 75°F"`         |
| `$weather._code`    | JavaScript code (if set)           | `"console.log(...)"`    |
| `$weather._run()`   | Execute the command's code         | `$weather._run()`       |

**Special characters**:
- Commands with dashes (`-`) become underscores (`_`): `user-settings` → `$user_settings`
- Commands with slashes (`/`) become nested properties: `docs/api` → `$docs.api`

**Nested commands** are accessible as properties:

If you have `docs/api` and `docs/install`, you can access them as:
- `$docs.api` - calls the `docs/api` command
- `$docs.install` - calls the `docs/install` command

### Code formats

All of these work:

```
.set weather.run console.log(context.content)
```

````
.set weather.run
```
console.log(context.content)
```
````

````
.set weather.run
```js
console.log(context.content)
```
````

## Examples

### Basic storage

| Step | Command                                | Result                                                 |
| ---- | -------------------------------------- | ------------------------------------------------------ |
| 1    | `.add manual https://docs.example.com` | ✅ Alias 'manual' stored successfully                  |
| 2    | `.manual`                              | `https://docs.example.com`                             |
| 3    | `.add manual Also check the FAQ`       | ✅ Alias 'manual' updated successfully                 |
| 4    | `.manual`                              | `https://docs.example.com`<br><br>`Also check the FAQ` |

### JavaScript enhancement

**Task counter:**

```
.add todo Buy milk
Walk dog
Finish project
.set todo.run let items = context.content.split('\n'); console.log("📝 " + items.length + " tasks");
.todo
# Shows: 📝 3 tasks
```

**Weather with emoji:**

```
.add weather Sunny, 72°F
.set weather.run console.log("🌤️ " + context.content)
.weather
# Shows: 🌤️ Sunny, 72°F
```

**Random quote picker:**

```
.add quotes The best time to plant a tree was 20 years ago. The second best time is now.
Life is what happens to you while you're busy making other plans.
Be yourself; everyone else is already taken.
.set quotes.run let lines = context.content.split('\n').filter(Boolean); console.log(lines[$.lib.random(0, lines.length - 1)]);
.quotes
# Shows: Be yourself; everyone else is already taken.
# (or one of the other quotes, randomly chosen)
```

**Direct JavaScript execution:**

```
.run console.log("Current time: " + new Date().toLocaleTimeString())
# Shows: Current time: 2:30:45 PM

.run let nums = [1,2,3,4,5]; console.log("Sum:", nums.reduce((a,b) => a+b))
# Shows: Sum: 15

.run console.log("User:", $.ctx.user.name)
# Shows: User: JohnDoe
```

**Using the `$` prefix for JavaScript:**

```
$console.log("Current time: " + new Date().toLocaleTimeString())
# Shows: Current time: 2:30:45 PM

$2 + 2
# Shows: 4

$new Date().getHours()
# Shows: 14
```

**Using command objects:**

```
.add weather Sunny, 75°F
.add quotes Be yourself; everyone else is already taken.

# Access command properties
$weather._content
# Shows: Sunny, 75°F

$quotes._name
# Shows: quotes

# Call commands from JavaScript
$weather()
# Shows: Sunny, 75°F

# Chain commands
$console.log("Weather: " + $weather._content + " | Quote: " + $quotes._content)
# Shows: Weather: Sunny, 75°F | Quote: Be yourself; everyone else is already taken.
```

### Organization example

```
.add api Main API documentation
.add api/auth How to authenticate
.add api/users User endpoints
.add api/orders Order endpoints
.promote api
```

In `.help`, you'll see:

- **Promoted section**: `.api: Main API documentation` with children listed below
- **Commands section**: All the built-in commands

## Rules

### Alias names

- 2-100 characters
- Letters, numbers, `_`, `-`, `/` only
- Must start and end with letter, number, or `_`
- Case doesn't matter (stored lowercase)

### Permission system

- Server aliases stay in that server
- Everyone can do anything (change each other's aliases, etc)
- Aliases you create in DMs stay in your DMs

### Command priority

1. Built-in commands (`.add`, `.help`, etc.) always work first
2. If not a built-in command, bot looks for your alias
3. For `$` prefix: if no command or alias exists, executes the entire message as JavaScript
4. Patterns like `..`, `...`, `$1`, or `.1` are ignored

### Prefix support

Emily supports two prefixes for accessing commands:
- **`.` (dot prefix)**: Traditional prefix, works for all commands
- **`$` (dollar prefix)**: Alternative prefix with special behavior:
  - If the command exists (built-in or alias): works like `.` prefix
  - If the command doesn't exist: executes the entire message as JavaScript
  - All aliases are available as global variables in JavaScript (e.g., `$weather`, `$docs.api`)

Both prefixes work identically for all commands (`.add` = `$add`, `.help` = `$help`, etc.).

## Further Reading

- **[JavaScript API Reference](JavaScript-API.md)** - Complete documentation of the JavaScript execution environment, including the `$` global object, context access, command manipulation, and error handling.

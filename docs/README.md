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

## Commands

### Storing text

| Command               | What it does            | Example                            |
| --------------------- | ----------------------- | ---------------------------------- |
| `.add [name] [text]`  | Store text under a name | `.add manual https://docs.com`     |
| `.edit [name] [text]` | Replace existing text   | `.edit manual https://newdocs.com` |
| `.rm [name]`          | Delete an alias         | `.rm manual`                       |

### Getting text back

| Command          | What it does                   | Example         |
| ---------------- | ------------------------------ | --------------- |
| `.[name]`        | Show the text                  | `.manual`       |
| `.[name]/`       | List all children of the alias | `.docs/`        |
| `.show [name]`   | Same as above                  | `.show manual`  |
| `.random [name]` | Show a random line             | `.random jokes` |
| `.list`          | Show all aliases               | `.list`         |

### JavaScript

| Command                  | What it does                | Example                                                     |
| ------------------------ | --------------------------- | ----------------------------------------------------------- |
| `.set [name].run [code]` | Add JavaScript to an alias  | `.set weather.run console.log("Today: " + context.content)` |
| `.run [code]`            | Execute JavaScript directly | `.run console.log("Hello, world!")`                         |

When you use an alias that has attribute `run`, instead of showing the text it will execute the code.
Everything printed with `console.log` will be shown in the chat.

See [JavaScript execution](#javascript-execution) for more details, or see the comprehensive [JavaScript API Reference](JavaScript-API.md) for complete documentation.

### Organization

| Command           | What it does                              | Example             |
| ----------------- | ----------------------------------------- | ------------------- |
| `.promote [name]` | Show the alias and its first line in help | `.promote docs`     |
| `.demote [name]`  | Don't list in help, only in `.list`       | `.demote old-stuff` |
| `.demote_all`     | Demote all aliases                        | `.demote_all`       |
| `.help`           | Show all commands and promoted aliases    | `.help`             |

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

### Limits

- 1 second timeout
- Only `console.log()` shows output
- No network access
- No file access
- Generally no access to almost anything

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
3. Patterns like `..` or `.1` are ignored

## Further Reading

- **[JavaScript API Reference](JavaScript-API.md)** - Complete documentation of the JavaScript execution environment, including the `$` global object, context access, command manipulation, and error handling.

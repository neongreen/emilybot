# Guess the CRC Member: command text

These are ordinary member commands. They need the `this.store` and `channel` support from emilybot PR #24.

The game is split into five aliases, so that every message fits in Discord's 2,000-character limit:

- `gcm` dispatches the commands.
- `gcm/add`, `gcm/start`, `gcm/round` and `gcm/score` are helpers.

All game state lives in `gcm`'s store. `gcm`'s code passes its own `this.store` to the helpers as an argument, for example `$gcm.round(store, "clue", "", channel.id)`. Each alias has its own store, so the helpers never use theirs.

## How to play

- **Host:** add puzzles in a channel the players can't see (any private channel in the server):
  `.gcm add Name/OtherName | Is a mod? yes | Has posted art? no | Joined before 2024? yes`
  The first name is the one the bot reveals. List every name people might reasonably guess. Each puzzle needs 3 to 12 clues, and each clue is a question ending in `yes` or `no`. The bot replies only with the puzzle number.
- **Players:** in any channel or thread:
  - `.gcm start` starts a round with a puzzle not yet played in this channel and shows clue 1.
  - `.gcm clue` shows the next clue.
  - `.gcm guess <name>` guesses. Case, spaces and punctuation are ignored, and letters from any script work.
  - `.gcm giveup` reveals the answer and ends the round.
  - `.gcm reset` ends the round without revealing it.
  - `.gcm score` shows the server leaderboard.
  - `.gcm` alone shows the how-to text.
- **Points:** a right guess earns the clues still hidden + 1. The round ends at the first right guess, so a repeated guess does not score again.
- **Honor system:** the answers live in `gcm`'s saved data, not in alias text. Anyone who edits these aliases could still print them.
- **Busy replies:** each channel or thread has its own round, but all rounds share one saved store. If two game commands run at the same moment, even in different channels, one of them gets "the bot is busy… try again" and changes nothing.

## Installing

Send each block below as one message, in this order, in any channel of the server. The helpers must exist (blocks 2–5) before their code can be set. Each message should get the bot's success reaction (✔️). Character counts include the whole message.

### 1. Content of .gcm (the how-to text) (726 characters)

````
.add gcm 🕵️ **Guess the CRC Member**: someone describes a member with yes/no clues, everyone else guesses who it is.
**Host:** in a channel the players can't see, add a puzzle: `.gcm add Name/OtherName | Is a mod? yes | Has posted art? no | Joined before 2024? yes` (3 to 12 clues, each ending in yes or no; list every name people might guess).
**Play:** `.gcm start` shows the first clue · `.gcm clue` shows the next · `.gcm guess <name>` · `.gcm giveup` reveals the answer · `.gcm reset` ends the round without revealing · `.gcm score` shows the leaderboard.
Fewer clues = more points. Each channel or thread has its own round. Honor system: the answers are in this alias's saved data, so please don't edit the code to peek.
````

### 2. Create gcm/add (82 characters)

````
.add gcm/add Part of the .gcm game: adds a puzzle. Use `.gcm add ...`; see `.gcm`.
````

### 3. Create gcm/start (83 characters)

````
.add gcm/start Part of the .gcm game: starts a round. Use `.gcm start`; see `.gcm`.
````

### 4. Create gcm/round (83 characters)

````
.add gcm/round Part of the .gcm game: clues, guesses, giveup and reset. See `.gcm`.
````

### 5. Create gcm/score (72 characters)

````
.add gcm/score Part of the .gcm game: the leaderboard. Use `.gcm score`.
````

### 6. Code of gcm (934 characters)

````
.set gcm.run ```js
// Guess the CRC Member: a party game. Type `.gcm` for how to play.
// All game state lives in THIS alias's store (this.store). The helper aliases
// gcm/add, gcm/start, gcm/round and gcm/score get it passed in, because each alias has its own store.
// Honor system: anyone who edits these aliases could print the answers. Please don't.

const store = this.store
if (!store) return print("Play this in a server channel.")

// Everything after ".gcm"
const text = message.text.replace(/^\S+\s*/, "")
const sub = (text.split(/\s+/)[0] || "").toLowerCase()
const rest = text.slice(sub.length).trim()

if (sub === "add") return $gcm.add(store, rest)
// A thread counts as its own channel
if (sub === "start") return $gcm.start(store, channel.id)
if (["clue", "guess", "giveup", "reset"].includes(sub)) return $gcm.round(store, sub, rest, channel.id)
if (sub === "score") return $gcm.score(store)
print(this.content)
```
````

### 7. Code of gcm/add (1232 characters)

````
.set gcm/add.run ```js
// Part of .gcm: adds a puzzle. Called as $gcm.add(store, text).
// text: "Name1/Name2 | Question? yes | Question? no | ..."
const [store, text] = args
if (!store || typeof store.get !== "function") return print("Use `.gcm add ...` instead.")

const norm = (s) => s.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "")
const parts = text.split("|").map((p) => p.trim()).filter(Boolean)
const names = (parts.shift() || "").split("/").map((n) => n.trim()).filter(Boolean)
const clues = []
for (const p of parts) {
  const m = p.match(/^(.*\S)\s+(yes|no)$/i)
  if (!m) return print(`This clue must end with yes or no: "${p}"`)
  clues.push({ q: m[1], a: m[2].toLowerCase() })
}
if (names.length === 0 || names.some((n) => !norm(n))) {
  return print("Start with the member's name(s), like `.gcm add Alex/alexthegreat | Is a mod? yes | ...`")
}
if (clues.length < 3 || clues.length > 12) return print(`A puzzle needs 3 to 12 clues; this one has ${clues.length}.`)

const puzzles = store.get("puzzles", [])
const id = puzzles.reduce((max, p) => Math.max(max, p.id), 0) + 1
puzzles.push({ id, names, clues })
store.set("puzzles", puzzles)
print(`Added puzzle #${id} with ${clues.length} clues.`) // never echo the names
```
````

### 8. Code of gcm/start (1024 characters)

````
.set gcm/start.run ```js
// Part of .gcm: starts a round in one channel. Called as $gcm.start(store, channelId).
const [store, here] = args
if (!store || typeof store.get !== "function") return print("Use `.gcm start` instead.")

const round = store.get("round:" + here)
if (round) return print("A round is already going here. " + $gcm.round(store, "show", "", here))

const played = store.get("played:" + here, [])
const fresh = store.get("puzzles", []).filter((p) => !played.includes(p.id))
if (fresh.length === 0) {
  return print("No new puzzles for this channel. Add some with `.gcm add` (in a channel the players can't see).")
}
const puzzle = random(fresh)
// Snapshot the puzzle, so editing the puzzle list can't change this round's answer
store.set("round:" + here, { names: puzzle.names, clues: puzzle.clues, shown: 1 })
store.set("played:" + here, [...played, puzzle.id])
print("🕵️ Guess the CRC member! Guess with `.gcm guess <name>`, more clues with `.gcm clue`.")
print($gcm.round(store, "show", "", here))
```
````

### 9. Code of gcm/round (1841 characters)

````
.set gcm/round.run ```js
// Part of .gcm: the current round in one channel. Called as $gcm.round(store, sub, text, channelId)
// with sub = clue, guess, giveup, reset, or show (returns the current clue as text).
const [store, sub, text, here] = args
if (!store || typeof store.get !== "function") return print("Use `.gcm clue` instead.")

const key = "round:" + here
const round = store.get(key)
const show = () => `Clue ${round.shown}/${round.clues.length}: ${round.clues[round.shown - 1].q} **${round.clues[round.shown - 1].a}**`
if (sub === "show") return show()
if (!round) return print(sub === "reset" ? "No round here." : "No round here. Start one with `.gcm start`.")

if (sub === "clue") {
  if (round.shown >= round.clues.length) return print("All clues are out! Guess, or `.gcm giveup`.")
  round.shown++
  store.set(key, round)
  return print(show())
}
if (sub === "giveup") {
  store.delete(key)
  return print(`It was **${round.names[0]}**. Start another with \`.gcm start\`.`)
}
if (sub === "reset") {
  store.delete(key)
  return print("Round ended. The answer stays secret.")
}

// guess
const norm = (s) => s.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "")
if (!norm(text)) return print("Guess like `.gcm guess Alex`.")
if (!round.names.some((n) => norm(n) === norm(text))) {
  return print(`❌ Not ${text}. (${round.shown}/${round.clues.length} clues shown)`)
}
const points = round.clues.length - round.shown + 1
const scores = store.get("scores", {})
const before = scores[user.id] ? scores[user.id].points : 0
scores[user.id] = { name: user.name, points: before + points }
store.set("scores", scores)
store.delete(key) // round over: a repeated guess can't score again
print(`🎉 ${user.name} got it: **${round.names[0]}**, after ${round.shown} of ${round.clues.length} clues. +${points} point${points === 1 ? "" : "s"}!`)
```
````

### 10. Code of gcm/score (452 characters)

````
.set gcm/score.run ```js
// Part of .gcm: prints the leaderboard. Called as $gcm.score(store).
const [store] = args
if (!store || typeof store.get !== "function") return print("Use `.gcm score` instead.")

const rows = Object.values(store.get("scores", {})).sort((a, b) => b.points - a.points).slice(0, 10)
if (rows.length === 0) return print("No scores yet.")
print("🏆 Scores\n" + rows.map((r, i) => `${i + 1}. ${r.name}: ${r.points}`).join("\n"))
```
````

## Placeholder puzzles (testing only, not about real members)

```
.gcm add Placeholder Ada/Ada | Is a placeholder? yes | Likes chess? yes | Is a mod? no | Posts art? yes
.gcm add Placeholder Ziggy/Ziggy Stardust | Is a placeholder? yes | Likes chess? no | Is a mod? yes
.gcm add Placeholder Ömer/Ömer | Is a placeholder? yes | Plays piano? yes | Is a mod? no
```

To remove the placeholders before real play, delete `gcm` and send blocks 1 and 6 again. That clears its saved data; the helpers can stay.

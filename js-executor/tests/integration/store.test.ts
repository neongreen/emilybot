import { assertEquals, assertStringIncludes } from "@std/assert"
import { execute } from "../../executor.ts"
import type { CommandData, StoreSnapshot } from "../../types.ts"

// A loader over fixed snapshots that records which stores were loaded.
function loader(stores: Record<string, StoreSnapshot> = {}) {
  const calls: string[] = []
  const load = (id: string) => {
    calls.push(id)
    return stores[id] ?? { version: 0, data: {} }
  }
  return { load, calls }
}

const alias = (run: string, id = "a1", name = "game"): CommandData => ({ id, name, content: "", run })

Deno.test("get, set, delete and keys, with reads and buffered writes", async () => {
  const { load, calls } = loader({ a1: { version: 7, data: { n: 1, gone: true } } })
  const code = `
    const n = this.store.get("n")
    this.store.set("n", n + 1)
    this.store.delete("gone")
    return [this.store.get("n"), this.store.get("gone", "fallback"), this.store.keys()]`
  const result = await execute({}, [alias(code)], "$game()", { loadStore: load })
  assertEquals(result, {
    success: true,
    output: "",
    value: `[ 2, "fallback", [ "n" ] ]`,
    store: { reads: { a1: 7 }, writes: { a1: { n: { v: 2 }, gone: { d: true } } } },
  })
  assertEquals(calls, ["a1"]) // loaded once
})

Deno.test("reading a missing key or listing keys records the version", async () => {
  const { load } = loader()
  for (const code of [`this.store.get("missing")`, `this.store.keys()`]) {
    const result = await execute({}, [alias(code)], "$game()", { loadStore: load })
    assertEquals(result.store, { reads: { a1: 0 }, writes: { a1: {} } })
  }
})

Deno.test("a blind write records the version too", async () => {
  const { load } = loader({ a1: { version: 3, data: {} } })
  const result = await execute({}, [alias(`this.store.set("k", 1)`)], "$game()", { loadStore: load })
  assertEquals(result.store, { reads: { a1: 3 }, writes: { a1: { k: { v: 1 } } } })
})

Deno.test("stores load lazily: an alias that never touches its store loads nothing", async () => {
  const { load, calls } = loader()
  const result = await execute({}, [alias(`return typeof this.store`)], "$game()", { loadStore: load })
  assertEquals([result.value, result.store, calls], [`"object"`, undefined, []])
})

Deno.test("values are copied in and out", async () => {
  const { load } = loader({ a1: { version: 1, data: { o: { list: [1] } } } })
  const code = `
    const o = this.store.get("o"); o.list.push(2)
    const fresh = { list: [3] }; this.store.set("p", fresh); fresh.list.push(4)
    return [this.store.get("o"), this.store.get("p")]`
  const result = await execute({}, [alias(code)], "$game()", { loadStore: load })
  assertEquals(result.value, `[ { list: [ 1 ] }, { list: [ 3 ] } ]`)
  assertEquals(result.store!.writes, { a1: { p: { v: { list: [3] } } } })
})

Deno.test("non-JSON values are rejected with an explicit error", async () => {
  const { load } = loader()
  const cases: [string, string][] = [
    ["undefined", "value is undefined"],
    ["NaN", "value is NaN"],
    ["Infinity", "value is Infinity"],
    ["new Date()", "value is a Date"],
    ["new Map()", "value is a Map"],
    ["() => 1", "value is a function"],
    ["1n", "value is a bigint"],
    ["{ a: { b: undefined } }", "value.a.b is undefined"],
    ["[1, , 3]", "an empty slot at index 1"],
    ["(() => { const o = {}; o.self = o; return o })()", "value.self is a circular reference"],
    ["new (class Point {})()", "value is a Point"],
  ]
  for (const [value, message] of cases) {
    const result = await execute({}, [alias(`this.store.set("k", ${value})`)], "$game()", { loadStore: load })
    assertEquals(result.success, false, value)
    assertStringIncludes(result.error!, message)
    assertStringIncludes(result.error!, "cannot be stored")
    assertEquals(result.store, undefined)
  }
})

Deno.test("keys must be non-empty strings of at most 100 characters", async () => {
  const { load } = loader()
  for (const key of [`""`, `"${"k".repeat(101)}"`, `5`]) {
    const result = await execute({}, [alias(`this.store.get(${key})`)], "$game()", { loadStore: load })
    assertStringIncludes(result.error!, "keys must be non-empty strings of at most 100 characters")
  }
  const ok = await execute({}, [alias(`this.store.set("${"k".repeat(100)}", 1)`)], "$game()", { loadStore: load })
  assertEquals(ok.success, true)
})

Deno.test("a failed run returns no store writes", async () => {
  const { load } = loader()
  for (const code of [`this.store.set("k", 1); throw new Error("x")`, `this.store.set("k", 1); while (true) {}`]) {
    const result = await execute({}, [alias(code)], "$game()", { loadStore: load, timeoutMs: 300 })
    assertEquals(result.success, false)
    assertEquals(result.store, undefined)
  }
})

Deno.test("this.store is undefined without a loader, for inline code, and for reassigned code", async () => {
  const { load, calls } = loader()
  const commands = [alias(`return typeof this.store`)]
  assertEquals((await execute({}, commands, "$game()")).value, `"undefined"`) // DMs: no loader
  assertEquals((await execute({}, commands, "typeof $.commands.game.store", { loadStore: load })).value, `"undefined"`)
  assertEquals((await execute({}, commands, "typeof $game.store", { loadStore: load })).value, `"undefined"`)
  const reassigned = `$.commands.game.code = "return typeof this.store // edited"; $.cmd("game")`
  assertEquals((await execute({}, commands, reassigned, { loadStore: load })).value, `"undefined"`)
  // Aliases without an id (not stored in the database) get none either
  const noId = [{ name: "game", content: "", run: "return typeof this.store" }]
  assertEquals((await execute({}, noId, "$game()", { loadStore: load })).value, `"undefined"`)
  assertEquals(calls, [])
})

Deno.test("$.cmd and $.commands run the stored code with its store", async () => {
  const { load } = loader({ a1: { version: 1, data: { n: 5 } } })
  const commands = [alias(`return this.store.get("n")`)]
  assertEquals((await execute({}, commands, `$.cmd("game")`, { loadStore: load })).value, "5")
  assertEquals((await execute({}, commands, `$.commands.game.run()`, { loadStore: load })).value, "5")
})

Deno.test("each alias has its own store; a caller cannot use the callee's", async () => {
  const { load } = loader({ a1: { version: 1, data: { who: "a" } }, b2: { version: 1, data: { who: "b" } } })
  const commands = [
    alias(`return [this.store.get("who"), $other()]`),
    alias(`return this.store.get("who")`, "b2", "other"),
  ]
  const result = await execute({}, commands, "$game()", { loadStore: load })
  assertEquals(result.value, `[ "a", "b" ]`)
  assertEquals(result.store!.reads, { a1: 1, b2: 1 })
})

Deno.test("an unreadable store fails with a clear message", async () => {
  const load = () => ({ error: "the bot could not read its stored data" })
  const result = await execute({}, [alias(`this.store.get("k")`)], "$game()", { loadStore: load })
  assertEquals(result.success, false)
  assertStringIncludes(result.error!, "this.store is unavailable: the bot could not read its stored data")
  const unrelated = await execute({}, [alias(`return 1`)], "$game()", { loadStore: load })
  assertEquals(unrelated.value, "1")
})

Deno.test("channel is available as a global and on ctx", async () => {
  const channel = { id: "5", name: "general", parent_id: null }
  const result = await execute({ channel, ctx: { channel } }, [], "[channel.name, ctx.channel.id, $.channel.parent_id]")
  assertEquals(result.value, `[ "general", "5", null ]`)
})

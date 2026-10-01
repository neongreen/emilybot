import { assert, assertEquals, assertStringIncludes } from "@std/assert"
import { execute, TIMEOUT_ERROR } from "../../executor.ts"
import type { CommandData } from "../../types.ts"

// A corpus shaped like production: ~1000 aliases, some with code, one with a 400 KB content blob.
function makeCorpus(): CommandData[] {
  const commands: CommandData[] = []
  for (let i = 0; i < 1000; i++) {
    commands.push({
      name: i % 10 === 0 ? `group${i % 7}/cmd${i}` : `cmd${i}`,
      content: `Content of command ${i}. `.repeat(30),
      run: i % 3 === 0 ? `const xs = [${i}, ${i + 1}, ${i + 2}]\nprint(xs.map(x => x * 2).join(", "))` : null,
    })
  }
  commands.push({ name: "huge", content: "x".repeat(99).concat("\n").repeat(4000), run: null })
  return commands
}

Deno.test("20 prints with a 1000-command corpus finish well under a second", async () => {
  const commands = makeCorpus()
  const code = `for (let i = 0; i < 20; i++) print("line", i)\n$.cmd("cmd3")`
  const start = performance.now()
  const result = await execute({ message: { text: ".x" } }, commands, code)
  const elapsed = performance.now() - start
  console.log(`executor time: ${elapsed.toFixed(0)} ms`)
  assertEquals(result.success, true)
  assertEquals(result.output.split("\n").length, 21)
  assert(elapsed < 1000, `took ${elapsed.toFixed(0)} ms`)
})

Deno.test("runaway loops are interrupted with a timeout error", async () => {
  const start = performance.now()
  const result = await execute({}, [], "while (true) {}", { timeoutMs: 300 })
  assertEquals(result, { success: false, output: "", value: undefined, error: TIMEOUT_ERROR(300) })
  assert(performance.now() - start < 2000)
})

Deno.test("invalid commands only fail when invoked", async () => {
  const commands: CommandData[] = [
    { name: "bad", content: "", run: "let let = (" },
    { name: "good", content: "", run: "return 'ok'" },
  ]
  assertEquals(await execute({}, commands, "$good()"), { success: true, output: "", value: `"ok"` })
  const result = await execute({}, commands, "$bad()")
  assertEquals(result.success, false)
  assertStringIncludes(result.error!, "Command 'bad' has invalid JavaScript and cannot be executed")
})

Deno.test("print formats objects like Deno.inspect", async () => {
  const result = await execute(
    {},
    [],
    `print({ a: 1, b: [1, 2, { c: "x" }] }, "str", 3, null, undefined, [1, , 3], new Map([[1, 2]]))`,
  )
  assertEquals(
    result.output,
    `{ a: 1, b: [ 1, 2, { c: "x" } ] } str 3 null undefined [ 1, <1 empty item>, 3 ] Map(1) { 1 => 2 }`,
  )
})

Deno.test("lib helpers, fields, and command objects", async () => {
  const commands: CommandData[] = [
    { name: "foo", content: "FOO", run: "return [this.name, this.content, args]" },
    { name: "foo/bar", content: "BAR", run: null },
  ]
  const fields = { message: { text: "hi" }, user: { name: "U" } }
  const check = async (code: string, value: string, output = "") =>
    assertEquals(await execute(fields, commands, code), { success: true, output, value })

  await check(
    "[tail([1, 2, 3]), init([1, 2, 3]), drop([1, 2, 3], 2), dropLast([1, 2, 3], 2)]",
    "[ [ 2, 3 ], [ 1, 2 ], [ 3 ], [ 1 ] ]",
  )
  await check(
    "[reverse([1, 2]), min(3, 1), max(3, 1), shuffle([7]), random([5]), lib.random(2, 2), $.random(4, 4)]",
    "[ [ 2, 1 ], 1, 3, [ 7 ], 5, 2, 4 ]",
  )
  await check("[message.text, $.message.text, user.name]", `[ "hi", "hi", "U" ]`)
  await check(`$.cmd("foo", 1)`, `[ "foo", "FOO", [ 1 ] ]`)
  await check(`$foo(2)`, `[ "foo", "FOO", [ 2 ] ]`)
  // `$foo` is a container for `$foo.bar`, so its own command lives on `_self`
  await check(
    `[$foo._self._name, $foo._self._content, $foo.bar._name, typeof $.commands["foo/bar"].run]`,
    `[ "foo", "FOO", "foo/bar", "function" ]`,
  )
  assertEquals(await execute(fields, commands, "$foo.bar()"), { success: true, output: "BAR", value: undefined })

  const bad = await execute({}, [], "random(1)")
  assertEquals(bad.success, false)
  assertStringIncludes(bad.error!, "random(x) expects x to be an array, got number")
})

Deno.test("result values are unwrapped and inspected", async () => {
  assertEquals(await execute({}, [], "Promise.resolve(3)"), { success: true, output: "", value: "3" })
  assertEquals(await execute({}, [], "({ f() {}, d: new Date(0) })"), {
    success: true,
    output: "",
    value: "{ f: [Function: f], d: 1970-01-01T00:00:00.000Z }",
  })
  assertEquals(await execute({}, [], "throw new TypeError('t')"), {
    success: false,
    output: "",
    value: undefined,
    error: "t",
  })
})

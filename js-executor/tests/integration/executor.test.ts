import { assert, assertEquals, assertStringIncludes } from "@std/assert"
import { execute, OUTPUT_LIMIT_BYTES, OUTPUT_LIMIT_ERROR, TIMEOUT_ERROR } from "../../executor.ts"
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
  let timings
  const result = await execute({ message: { text: ".x" } }, commands, code, { onTimings: (t) => timings = t })
  const elapsed = performance.now() - start
  console.log(`executor time: ${elapsed.toFixed(0)} ms`, timings)
  assertEquals(result.success, true)
  assertEquals(result.output.split("\n").length, 21)
  assert(elapsed < 1000, `took ${elapsed.toFixed(0)} ms`)
})

// --- Deadline ---

Deno.test("runaway loops are interrupted with a timeout error", async () => {
  const start = performance.now()
  const result = await execute({}, [], "while (true) {}", { timeoutMs: 300 })
  assertEquals(result, { success: false, output: "", value: undefined, error: TIMEOUT_ERROR(300), kind: "timeout" })
  assert(performance.now() - start < 2000)
})

Deno.test("a two-second busy loop finishes within the default budget", async () => {
  const result = await execute({}, [], "const end = Date.now() + 2000; while (Date.now() < end) {}; 'done'")
  assertEquals(result, { success: true, output: "", value: `"done"` })
})

Deno.test("the deadline is shared by nested commands, not reset per command", async () => {
  const commands: CommandData[] = [{
    name: "spin",
    content: "",
    run: "const end = Date.now() + 300; while (Date.now() < end) {}",
  }]
  const result = await execute({}, commands, "for (let i = 0; i < 5; i++) $spin()", { timeoutMs: 1000 })
  assertEquals(result.kind, "timeout")
})

Deno.test("timeouts cannot be caught by user code", async () => {
  const result = await execute({}, [], "try { while (true) {} } catch (e) {}; 'escaped'", { timeoutMs: 200 })
  assertEquals(result.kind, "timeout")
})

Deno.test("import fetches count against the same deadline", async () => {
  const result = await execute(
    {},
    [],
    `
    const { camelCase } = await import('https://esm.sh/change-case@5.4.0?deadline-test=' + Math.random())
    camelCase("a b")
  `,
    { timeoutMs: 1 },
  )
  assertEquals(result, { success: false, output: "", value: undefined, error: TIMEOUT_ERROR(1), kind: "timeout" })
})

// --- Output budget ---

Deno.test("a print flood of one reused string stops with an output error", async () => {
  const result = await execute({}, [], `const s = "x".repeat(10000); while (true) print(s)`)
  assertEquals(result, { success: false, output: "", value: undefined, error: OUTPUT_LIMIT_ERROR, kind: "output" })
})

Deno.test("printing a huge shared-reference object stops with an output error", async () => {
  // Deno.inspect expands shared references: 2^40 leaves if formatted naively
  const start = performance.now()
  const result = await execute({}, [], `let x = ["leaf"]; for (let i = 0; i < 40; i++) x = [x, x]; print(x)`)
  assertEquals(result.kind, "output")
  assert(performance.now() - start < 3000)
})

Deno.test("a large returned value stops with an output error", async () => {
  const result = await execute({}, [], `Object.fromEntries(Array.from({ length: 200000 }, (_, i) => ["key" + i, i]))`)
  assertEquals(result.kind, "output")
})

Deno.test("output just under the budget is kept", async () => {
  const lines = Math.floor(OUTPUT_LIMIT_BYTES / 1001) - 1
  const result = await execute({}, [], `for (let i = 0; i < ${lines}; i++) print("x".repeat(1000))`)
  assertEquals(result.success, true)
  assertEquals(result.output.split("\n").length, lines)
})

Deno.test("cyclic and deeply nested objects print", async () => {
  const result = await execute(
    {},
    [],
    `const o = { a: 1 }; o.self = o; print(o); let d = {}; for (let i = 0; i < 500; i++) d = { d }; print(d)`,
  )
  assertEquals(result.success, true)
  assertStringIncludes(result.output, "<ref *1> { a: 1, self: [Circular *1] }")
  assertStringIncludes(result.output, "[Object]")
})

// --- Errors ---

Deno.test("error kinds", async () => {
  assertEquals((await execute({}, [], "let let = (")).kind, "syntax")
  assertEquals((await execute({}, [], "eval('let let = (')")).kind, "syntax")
  assertEquals((await execute({}, [], "undefinedVar")).kind, "runtime")
  assertEquals(
    (await execute({}, [], "const a = []; while (true) a.push('xxxxxxxxxxxxxxxxxxxxxxxxxx' + a.length)")).kind,
    "memory",
  )
})

Deno.test("invalid commands only fail when invoked", async () => {
  const commands: CommandData[] = [
    { name: "bad", content: "", run: "let let = (" },
    { name: "good", content: "", run: "return 'ok'" },
  ]
  assertEquals(await execute({}, commands, "$good()"), { success: true, output: "", value: `"ok"` })
  const result = await execute({}, commands, "$bad()")
  assertEquals(result.kind, "syntax")
  assertStringIncludes(result.error!, "Command 'bad' has invalid JavaScript and cannot be executed")
})

// --- Formatting ---

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
    kind: "runtime",
  })
})

// --- Command semantics ---

Deno.test("lib helpers, fields, and command objects", async () => {
  const commands: CommandData[] = [
    { name: "foo", content: "FOO", run: "return [this.name, this.content, args]" },
    { name: "foo/bar", content: "BAR", run: null },
    { name: "with-dash", content: "DASH", run: null },
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
  await check(`$with_dash._content`, `"DASH"`)
  assertEquals(await execute(fields, commands, "$foo.bar()"), { success: true, output: "BAR", value: undefined })

  const bad = await execute({}, [], "random(1)")
  assertEquals(bad.success, false)
  assertStringIncludes(bad.error!, "random(x) expects x to be an array, got number")
})

// Patterns from community aliases (rma, util, random-command, sudokudaily)
Deno.test("community alias patterns", async () => {
  const commands: CommandData[] = [
    // rma rewrites the message before delegating
    {
      name: "rma",
      content: "",
      run: "$.message.text = $.message.text.replace(/^.rma\\b/, '.randmemberalt')\n$randmemberalt()",
    },
    { name: "randmemberalt", content: "", run: "print($.message.text)" },
    // util defines globals used by later calls
    {
      name: "util",
      content: "-",
      run:
        "$user = $.ctx.user.name\n$msg = $.message.text.slice(($.message.text.search(/\\s/) + 1) || $.message.text.length)",
    },
    { name: "greet", content: "", run: "$util()\nprint('hi ' + $user + ': ' + $msg)" },
    // random-command enumerates $.commands and returns the callee's result
    {
      name: "random-command",
      content: "",
      run:
        "const name = random(Object.keys($.commands).filter(n => n === 'dep'))\nconst result = $.cmd(name)\nprint(`-# .${name}`)\nreturn result",
    },
    // sudokudaily-style use of a dependency's return value
    { name: "dep", content: "", run: "return args.length ? Number(args[0]) * 2 : 21" },
    { name: "uses-dep", content: "", run: "print($dep('4') + $.cmd('dep'))" },
    { name: "broken-unused", content: "", run: "let let = (" },
  ]
  const fields = () => ({ message: { text: ".rma 3 users" }, ctx: { user: { name: "U" } } })
  assertEquals((await execute(fields(), commands, "$rma()")).output, ".randmemberalt 3 users")
  assertEquals((await execute(fields(), commands, "$greet()")).output, "hi U: 3 users")
  assertEquals(await execute(fields(), commands, "$.cmd('random-command')"), {
    success: true,
    output: "-# .dep",
    value: "21",
  })
  assertEquals((await execute(fields(), commands, "$.cmd('uses-dep')")).output, "29")
})

Deno.test("reassigning a command's code changes what runs", async () => {
  const commands: CommandData[] = [{ name: "c", content: "", run: "return 1" }]
  const result = await execute({}, commands, "const a = $.cmd('c'); $.commands.c.code = 'return 2'; [a, $.cmd('c')]")
  assertEquals(result.value, "[ 1, 2 ]")
})

Deno.test("state does not survive into the next invocation", async () => {
  await execute({}, [], "globalThis.leak = 1; $.leak = 1")
  assertEquals((await execute({}, [], "[typeof leak, typeof $.leak]")).value, `[ "undefined", "undefined" ]`)
})

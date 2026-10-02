import { assertEquals, assertStringIncludes } from "@std/assert"
import { execute } from "../../executor.ts"
import { storeLoaderFromFile } from "../../stores.ts"

const fixture = (name: string) => new URL(`../fixtures/stores/${name}`, import.meta.url).pathname

Deno.test("reads this server's stores from store.json", () => {
  const load = storeLoaderFromFile(fixture("valid.json"), "7")
  assertEquals(load("a1"), { version: 4, data: { n: 1 } })
  assertEquals(load("missing"), { version: 0, data: {} })
  assertEquals(load("b2"), { version: 0, data: {} }) // another server's store
})

Deno.test("a missing or empty file means no stores yet", () => {
  assertEquals(storeLoaderFromFile(fixture("does-not-exist.json"), "7")("a1"), { version: 0, data: {} })
  assertEquals(storeLoaderFromFile(fixture("empty.json"), "7")("a1"), { version: 0, data: {} })
})

Deno.test("a half-written file makes the run busy, never a crash", () => {
  assertEquals(storeLoaderFromFile(fixture("torn.json"), "7")("a1"), { busy: true })
  assertEquals(storeLoaderFromFile(fixture("tail.json"), "7")("a1"), { busy: true })
})

Deno.test("a busy store ends the run as busy even if user code catches the error", async () => {
  const commands = [{
    id: "a1",
    name: "game",
    content: "",
    run: "try { this.store.get('n') } catch {}\nprint('after')",
  }]
  const result = await execute({}, commands, "$game()", { loadStore: storeLoaderFromFile(fixture("torn.json"), "7") })
  assertEquals(result.success, false)
  assertEquals(result.kind, "busy")
  assertStringIncludes(result.error!, "try again")
})

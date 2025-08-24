import { assertEquals } from "@std/assert"
import { execute } from "../../executor.ts"

Deno.test("Basic arithmetic", async () => {
  const result = await execute((_env) => ({}), [], "2 + 2")
  assertEquals(result, { success: true, output: "", value: "4" })
})

Deno.test("Console.log output", async () => {
  const result = await execute((_env) => ({}), [], "console.log('Hello World')")
  assertEquals(result, { success: true, output: "Hello World", value: undefined })
})

Deno.test("Error handling", async () => {
  const result = await execute((_env) => ({}), [], "undefined.property")
  assertEquals(result, {
    success: false,
    output: "",
    value: undefined,
    error: "cannot read property 'property' of undefined",
  })
})

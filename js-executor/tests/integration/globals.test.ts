import { assertEquals } from "@std/assert"
import { execute } from "../../executor.ts"
import type { CommandData } from "../../types.ts"

// Users can say `foo = bar` and it will be available in the global scope
Deno.test("Global assignment across commands", async () => {
  const commands: CommandData[] = [
    {
      name: "util",
      content: "",
      run: "global1 = 'xxx'; global2 = 'yyy';",
    },
  ]
  const result = await execute({}, commands, "$util(); return global1 + global2")
  assertEquals(result, { success: true, output: "", value: `"xxxyyy"` })
})

// Exporting functions
Deno.test("Exporting functions via globalThis", async () => {
  const commands: CommandData[] = [
    {
      name: "lib/foo",
      content: "",
      run: `
      function foo() { return 'bar' }
      globalThis.foo = foo
      `,
    },
  ]
  const result = await execute({}, commands, "$lib.foo(); return foo()")
  assertEquals(result, { success: true, output: "", value: `"bar"` })
})

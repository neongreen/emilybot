import { assertEquals } from "@std/assert"
import { execute } from "../../executor.ts"

Deno.test("statement imports", async () => {
  const result = await execute(
    (_env) => ({}),
    [],
    `
    import { camelCase } from 'https://esm.sh/change-case@5.4.0'
    camelCase("hello world")
  `,
  )
  assertEquals(result, { success: true, output: "", value: `"helloWorld"` })
})

Deno.test("expression imports", async () => {
  const result = await execute(
    (_env) => ({}),
    [],
    `
    const { camelCase } = await import('https://esm.sh/change-case@5.4.0')
    camelCase("hello world")
  `,
  )
  assertEquals(result, { success: true, output: "", value: `"helloWorld"` })
})

Deno.test("imports from other urls (esm.run) are forbidden", async () => {
  const result = await execute(
    (_env) => ({}),
    [],
    `
    const { camelCase } = await import('https://esm.run/change-case@5.4.0')
    camelCase("hello world")
  `,
  )
  assertEquals(result, { success: false, output: "", error: "Only esm.sh urls are supported", value: undefined })
})

/**
 * Checks that a command's code can be stored: it must parse, wrap, and compile exactly as the executor does when the
 * command runs (`wrapUserCode(code, "functionBody")`, then `new Function("args", wrapped)` inside QuickJS).
 *
 * The code is never called, imports are never resolved, and referenced commands do not need to exist.
 *
 * CLI: reads the code from stdin and prints `ValidationResult` as JSON.
 */

import { getQuickJS } from "./executor.ts"
import { wrapUserCode } from "./parse.ts"

export type ValidationResult =
  | { ok: true }
  | { ok: false; error: string; line?: number; column?: number }

const COMPILE_TIMEOUT_MS = 2000

export async function validateCommandCode(code: string): Promise<ValidationResult> {
  let wrapped: string
  try {
    wrapped = wrapUserCode(code, "functionBody")
  } catch (error) {
    const message = (error instanceof Error ? error.message : String(error)).replace(/^Failed to parse code: /, "")
    // meriyah reports positions in the original code as "[line:column-line:column]: message", columns from 0
    const m = message.match(/^\[(\d+):(\d+)-\d+:\d+\]: (.*)$/s)
    return m ? { ok: false, line: Number(m[1]), column: Number(m[2]) + 1, error: m[3] } : { ok: false, error: message }
  }

  const QuickJS = await getQuickJS()
  const runtime = QuickJS.newRuntime()
  const deadline = performance.now() + COMPILE_TIMEOUT_MS
  runtime.setInterruptHandler(() => performance.now() > deadline)
  runtime.setMemoryLimit(64 * 1024 * 1024)
  const ctx = runtime.newContext()
  try {
    const source = ctx.newString(wrapped)
    ctx.setProp(ctx.global, "__source", source)
    source.dispose()
    // Code using `await` or `import` compiles only as an async function body. The executor cannot run such commands
    // yet, but they are valid code, so they are accepted rather than blocking the save.
    const result = ctx.evalCode(`
      (() => {
        try {
          new Function("args", __source)
          return null
        } catch (e) {
          try {
            new (Object.getPrototypeOf(async function() {}).constructor)("args", __source)
            return null
          } catch {
            return String(e && e.message || e)
          }
        }
      })()
    `)
    if (result.error) {
      const err = ctx.dump(result.error)
      result.error.dispose()
      return { ok: false, error: String(err?.message ?? err) }
    }
    const error = ctx.dump(result.value)
    result.value.dispose()
    return error === null ? { ok: true } : { ok: false, error }
  } finally {
    ctx.dispose()
    runtime.dispose()
  }
}

if (import.meta.main) {
  const code = new TextDecoder().decode(await new Response(Deno.stdin.readable).arrayBuffer())
  console.log(JSON.stringify(await validateCommandCode(code)))
}

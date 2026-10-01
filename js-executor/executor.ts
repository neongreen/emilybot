/**
 * QuickJS wrapper for sandboxed JavaScript execution.
 *
 * Commands and fields enter the VM as one JSON string; `prelude.js` builds `$`, `$name` globals and the lib helpers
 * inside the VM. Only strings cross the boundary: printed output, lazy command wrapping, and module source from the
 * module loader. User code, including fetching its imports, runs under one deadline (`timeoutMs`), so runaway loops
 * and slow imports end with a timeout error. Collected output and the inspected result are capped in size.
 */

import type { QuickJSContext, QuickJSHandle, QuickJSRuntime, QuickJSWASMModule } from "quickjs-emscripten"
import { DEBUG_SYNC, newQuickJSWASMModule, RELEASE_SYNC } from "quickjs-emscripten/variants"
import { quickJsModuleLoader, quickJsModuleNormalizer } from "./imports.ts"
import { debug } from "./logging.ts"
import { wrapUserCode } from "./parse.ts"
import type { CommandData, ExecutionResult } from "./types.ts"

/** Default budget for user code, including fetching its imports. */
export const DEFAULT_TIMEOUT_MS = 5000
/** Max characters of printed output and of the inspected result kept on the host; the rest is dropped. */
export const OUTPUT_LIMIT_CHARS = 64 * 1024
export const TRUNCATED_MARKER = "…(output truncated)"
const MEMORY_LIMIT_BYTES = 1024 * 1024 * 10 // 10 MB for user code, on top of the loaded commands

export const TIMEOUT_ERROR = (ms: number) =>
  `JavaScript execution timed out (${ms / 1000}s limit). Check for infinite loops.`

const PRELUDE = Deno.readTextFileSync(new URL("./prelude.js", import.meta.url))

export type ExecuteOptions = {
  timeoutMs?: number
}

let quickJsModule: Promise<QuickJSWASMModule> | undefined
function getQuickJS(): Promise<QuickJSWASMModule> {
  quickJsModule ??= newQuickJSWASMModule(Deno.env.get("DEBUG") === "1" ? DEBUG_SYNC : RELEASE_SYNC)
  return quickJsModule
}

const inspect = (x: unknown) => Deno.inspect(x, { depth: 999, colors: false, compact: true, breakLength: 100 })

/** Rebuilds a value encoded by `__encode` in prelude.js so that Deno.inspect prints it like the original. */
export function decodeValue(encoded: unknown): unknown {
  const seen = new Map<number, unknown>()
  const go = (e: any): unknown => {
    if (e === null || typeof e !== "object") return e
    switch (e.t) {
      case "u":
        return undefined
      case "n":
        return Number(e.v)
      case "b":
        return BigInt(e.v)
      case "y":
        return Symbol(e.v)
      case "ref":
        return seen.get(e.i)
    }
    const fill = (target: any) => {
      seen.set(e.i, target)
      for (const [k, v] of e.p ?? []) target[k] = go(v)
      return target
    }
    switch (e.t) {
      case "f": {
        const name: string = e.n ?? ""
        const fn = e.k === "AsyncFunction"
          ? { [name]: async function() {} }[name]
          : e.k === "GeneratorFunction"
          ? { [name]: function*() {} }[name]
          : { [name]: function() {} }[name]
        return fill(fn)
      }
      case "a": {
        const arr: unknown[] = []
        seen.set(e.i, arr)
        for (const x of e.v) {
          if (x && x.t === "h") arr.length++
          else arr.push(go(x))
        }
        return arr
      }
      case "d":
        return fill(new Date(e.v))
      case "r":
        return fill(new RegExp(e.s, e.f))
      case "e": {
        const err = new Error(e.m)
        if (e.n !== "Error") Object.defineProperty(err, "name", { value: e.n, configurable: true, writable: true })
        err.stack = e.s ? `${e.n}: ${e.m}\n${e.s}`.trimEnd() : `${e.n}: ${e.m}`
        return fill(err)
      }
      case "m": {
        const m = new Map()
        seen.set(e.i, m)
        for (const [k, v] of e.v) m.set(go(k), go(v))
        return m
      }
      case "s": {
        const s = new Set()
        seen.set(e.i, s)
        for (const x of e.v) s.add(go(x))
        return s
      }
      case "p":
        return fill(new Promise(() => {}))
      case "o": {
        if (e.c === null) return fill(Object.create(null))
        if (e.c === "Object") return fill({})
        const cls = { [e.c]: class {} }[e.c]
        return fill(Object.create(cls.prototype))
      }
    }
    return e
  }
  return go(encoded)
}

function errorMessage(ctx: QuickJSContext, handle: QuickJSHandle): string {
  const err = ctx.dump(handle)
  handle.dispose()
  if (err && typeof err === "object" && "message" in err) return String(err.message)
  return String(err)
}

class TimeoutError extends Error {}

/**
 * Runs pending jobs until the promise settles; returns the settled value handle.
 * Non-promises are returned as-is.
 */
function settle(ctx: QuickJSContext, runtime: QuickJSRuntime, handle: QuickJSHandle): QuickJSHandle {
  for (;;) {
    const state = ctx.getPromiseState(handle)
    if (state.type === "fulfilled") {
      if (!state.notAPromise) handle.dispose()
      return state.value
    }
    if (state.type === "rejected") {
      handle.dispose()
      throw new Error(errorMessage(ctx, state.error))
    }
    const jobs = runtime.executePendingJobs()
    if (jobs.error) throw new Error(errorMessage(ctx, jobs.error))
    if (jobs.value === 0) {
      handle.dispose()
      throw new Error("Execution finished with a promise that never resolves")
    }
  }
}

/**
 * Execute user code.
 *
 * @param fields Values exposed as globals and on `$` (must be JSON-serializable). A function form is accepted for
 *   compatibility with older callers and is called with no environment.
 */
export async function execute(
  fields: Record<string, unknown> | ((env: unknown) => Record<string, unknown>),
  commands: CommandData[] = [],
  code: string,
  options: ExecuteOptions = {},
): Promise<ExecutionResult> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const fieldValues = typeof fields === "function" ? fields(undefined) : fields

  const QuickJS = await getQuickJS()
  const runtime = QuickJS.newRuntime()
  const ctx = runtime.newContext()
  const output: string[] = []
  let outputChars = 0
  let outputTruncated = false

  // One deadline for user code and its import fetches.
  let deadline = Infinity
  let timedOut = false
  runtime.setInterruptHandler(() => {
    if (Date.now() > deadline) {
      timedOut = true
      return true
    }
    return false
  })
  runtime.setModuleLoader((moduleName) => {
    const remaining = deadline - Date.now()
    if (remaining <= 0) {
      timedOut = true
      return { value: `throw new Error("Timed out before importing ${JSON.stringify(moduleName).slice(1, -1)}")` }
    }
    const result = quickJsModuleLoader(moduleName, { timeoutMs: remaining })
    if (Date.now() > deadline) timedOut = true
    return result
  }, quickJsModuleNormalizer)

  try {
    // --- Bridge functions (strings only) ---
    const hostPrint = ctx.newFunction("__host_print", (argsHandle) => {
      if (outputTruncated) return
      const args: unknown[] = JSON.parse(ctx.getString(argsHandle))
      const line = args.map((a) => typeof a === "string" ? a : inspect(decodeValue(a))).join(" ")
      if (outputChars + line.length > OUTPUT_LIMIT_CHARS) {
        output.push(line.slice(0, Math.max(0, OUTPUT_LIMIT_CHARS - outputChars)) + TRUNCATED_MARKER)
        outputTruncated = true
      } else {
        output.push(line)
        outputChars += line.length + 1
      }
    })
    const hostWrap = ctx.newFunction("__host_wrap", (nameHandle, codeHandle) => {
      const name = ctx.getString(nameHandle)
      try {
        debug("wrapping command", name)
        return ctx.newString(
          JSON.stringify({ ok: true, code: wrapUserCode(ctx.getString(codeHandle), "functionBody") }),
        )
      } catch (error) {
        return ctx.newString(
          JSON.stringify({ ok: false, error: error instanceof Error ? error.message : String(error) }),
        )
      }
    })
    ctx.setProp(ctx.global, "__host_print", hostPrint)
    ctx.setProp(ctx.global, "__host_wrap", hostWrap)
    hostPrint.dispose()
    hostWrap.dispose()

    const initJson = ctx.newString(JSON.stringify({ fields: fieldValues, commands }))
    ctx.setProp(ctx.global, "__init_json", initJson)
    initJson.dispose()

    ctx.unwrapResult(ctx.evalCode(PRELUDE, "prelude.js")).dispose()
    const encodeFn = ctx.getProp(ctx.global, "__encode")
    ctx.unwrapResult(ctx.evalCode("delete globalThis.__encode")).dispose()
    // The limit applies on top of what the commands and prelude already use
    const usageHandle = runtime.computeMemoryUsage()
    const usage = ctx.dump(usageHandle)
    usageHandle.dispose()
    runtime.setMemoryLimit(usage.memory_used_size + MEMORY_LIMIT_BYTES)

    // --- User code ---
    const wrapped = wrapUserCode(code, "module")
    debug("wrapped code:", wrapped)
    deadline = Date.now() + timeoutMs
    const moduleResult = ctx.evalCode(wrapped, "file:///code.mjs", { type: "module" })
    if (moduleResult.error) throw new Error(errorMessage(ctx, moduleResult.error))

    // The module evaluates to its namespace (possibly via a promise); `default` is the promise of the user's result.
    const namespace = settle(ctx, runtime, moduleResult.value)
    const defaultExport = ctx.getProp(namespace, "default")
    namespace.dispose()
    const value = settle(ctx, runtime, defaultExport)
    deadline = Infinity

    const isUndefined = ctx.typeof(value) === "undefined"
    let inspected: string | undefined
    if (!isUndefined) {
      const encoded = ctx.unwrapResult(ctx.callFunction(encodeFn, ctx.undefined, value))
      inspected = inspect(decodeValue(JSON.parse(ctx.getString(encoded))))
      if (inspected.length > OUTPUT_LIMIT_CHARS) inspected = inspected.slice(0, OUTPUT_LIMIT_CHARS) + TRUNCATED_MARKER
      encoded.dispose()
    }
    value.dispose()
    encodeFn.dispose()

    return { success: true, output: output.join("\n"), value: inspected }
  } catch (error) {
    debug("execute failed:", error)
    const message = timedOut ? TIMEOUT_ERROR(timeoutMs) : error instanceof Error ? error.message : String(error)
    return { success: false, output: "", value: undefined, error: message }
  }
  // The runtime is not disposed: the executor process exits after one run, and disposing with leaked handles
  // after an interrupted or failed run asserts in the debug build.
}

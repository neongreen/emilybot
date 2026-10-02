/**
 * QuickJS wrapper for sandboxed JavaScript execution.
 *
 * Commands and fields enter the VM as one JSON string; `prelude.js` builds `$`, `$name` globals and the lib helpers
 * inside the VM. Only strings cross the boundary: printed output, lazy command wrapping, and module source from the
 * module loader.
 *
 * Limits, all per invocation:
 * - one elapsed-time deadline (`timeoutMs`) that starts after the trusted bootstrap and covers compiling and running
 *   user code, nested commands, promise jobs and import fetches. A host callback (parsing a command, a fetch) cannot
 *   be preempted mid-call; the fetch gets only the remaining time, and the Python caller keeps a process backstop.
 * - a QuickJS heap limit for user code, on top of the loaded commands.
 * - an output budget (UTF-8 bytes) shared by printed output and the inspected result. Exceeding it stops execution.
 */

import type { QuickJSContext, QuickJSHandle, QuickJSRuntime, QuickJSWASMModule } from "quickjs-emscripten"
import { DEBUG_SYNC, newQuickJSWASMModule, RELEASE_SYNC } from "quickjs-emscripten/variants"
import { quickJsModuleLoader, quickJsModuleNormalizer } from "./imports.ts"
import { debug } from "./logging.ts"
import { wrapUserCode } from "./parse.ts"
import type { CommandData, ErrorKind, ExecutionResult } from "./types.ts"

/** Default elapsed-time budget for user code, including fetching its imports. */
export const DEFAULT_TIMEOUT_MS = 5000
/** Budget for printed output plus the inspected result, in UTF-8 bytes. */
export const OUTPUT_LIMIT_BYTES = 1024 * 1024
const MEMORY_LIMIT_BYTES = 1024 * 1024 * 10 // 10 MB for user code, on top of the loaded commands
/** Objects nested deeper than this print as `[Object]` / `[Array]`. */
const INSPECT_DEPTH = 100

export const TIMEOUT_ERROR = (ms: number) =>
  `JavaScript execution timed out (${ms / 1000}s limit). Check for infinite loops.`
export const OUTPUT_LIMIT_ERROR = `Output exceeded the ${OUTPUT_LIMIT_BYTES / 1024 / 1024} MiB limit`

const PRELUDE = Deno.readTextFileSync(new URL("./prelude.js", import.meta.url))

export type ExecuteOptions = {
  timeoutMs?: number
  /** Receives how long the trusted bootstrap and the user code took. */
  onTimings?: (timings: { bootstrapMs: number; userMs: number }) => void
}

let quickJsModule: Promise<QuickJSWASMModule> | undefined
export function getQuickJS(): Promise<QuickJSWASMModule> {
  quickJsModule ??= newQuickJSWASMModule(Deno.env.get("DEBUG") === "1" ? DEBUG_SYNC : RELEASE_SYNC)
  return quickJsModule
}

const inspect = (x: unknown) =>
  Deno.inspect(x, { depth: INSPECT_DEPTH, colors: false, compact: true, breakLength: 100 })
const utf8Length = (s: string) => new TextEncoder().encode(s).length

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
      case "deep":
        return e.a ? [{}] : { _: {} } // past the inspect depth, printed as [Array] / [Object]
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

class ExecError extends Error {
  constructor(public kind: ErrorKind, message: string) {
    super(message)
  }
}

/** Converts a thrown VM value into an ExecError and disposes its handle. */
function vmError(ctx: QuickJSContext, handle: QuickJSHandle): ExecError {
  const err = ctx.dump(handle)
  handle.dispose()
  if (err && typeof err === "object" && "message" in err) {
    const name = String(err.name)
    const message = String(err.message)
    // QuickJS reports deep recursion while compiling (e.g. a command calling itself) as a SyntaxError
    if (name === "SyntaxError" && message !== "stack overflow") return new ExecError("syntax", message)
    if (message === "out of memory") return new ExecError("memory", message)
    return new ExecError("runtime", message)
  }
  return new ExecError("runtime", String(err))
}

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
      throw vmError(ctx, state.error)
    }
    const jobs = runtime.executePendingJobs()
    if (jobs.error) throw vmError(ctx, jobs.error)
    if (jobs.value === 0) {
      handle.dispose()
      throw new ExecError("runtime", "Execution finished with a promise that never resolves")
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
  const startedAt = performance.now()
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const fieldValues = typeof fields === "function" ? fields(undefined) : fields

  const QuickJS = await getQuickJS()
  const runtime = QuickJS.newRuntime()
  const ctx = runtime.newContext()
  const output: string[] = []
  let outputBytes = 0

  // Set once, when user code starts; never extended or reset.
  let deadline = Infinity
  // Why the interrupt handler stopped execution, if it did.
  let stopKind: ErrorKind | null = null
  const stop = (kind: ErrorKind) => {
    stopKind ??= kind
    deadline = -Infinity
  }
  runtime.setInterruptHandler(() => {
    if (performance.now() > deadline) {
      stopKind ??= "timeout"
      return true
    }
    return false
  })
  runtime.setModuleLoader((moduleName) => {
    const remaining = deadline - performance.now()
    if (remaining <= 0) {
      stopKind ??= "timeout"
      return { value: `throw new Error(${JSON.stringify(`Timed out before importing ${moduleName}`)})` }
    }
    const result = quickJsModuleLoader(moduleName, { timeoutMs: remaining })
    if (performance.now() > deadline) stopKind ??= "timeout"
    return result
  }, quickJsModuleNormalizer)

  /** Adds to the output budget; stops execution when it runs out. */
  const spend = (bytes: number): boolean => {
    outputBytes += bytes
    if (outputBytes > OUTPUT_LIMIT_BYTES) {
      stop("output")
      return false
    }
    return true
  }

  let bootstrapMs = 0
  try {
    // --- Bridge functions (strings only) ---

    // Receives a JSON array of printed arguments (strings, or values encoded by `encode` in prelude.js),
    // or null when the VM ran out of output budget while encoding.
    const hostPrint = ctx.newFunction("__host_print", (argsHandle) => {
      if (ctx.typeof(argsHandle) !== "string") return void stop("output")
      // UTF-8 is at least as long as UTF-16, so this rejects oversized payloads before copying them out of the VM
      const lengthHandle = ctx.getProp(argsHandle, "length")
      const length = ctx.getNumber(lengthHandle)
      lengthHandle.dispose()
      if (outputBytes + length > OUTPUT_LIMIT_BYTES * 2 + 1024) return void stop("output")
      const args: unknown[] = JSON.parse(ctx.getString(argsHandle))
      const line = args.map((a) => typeof a === "string" ? a : inspect(decodeValue(a))).join(" ")
      if (spend(utf8Length(line) + 1)) output.push(line)
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

    const initJson = ctx.newString(JSON.stringify({ fields: fieldValues, commands, outputLimit: OUTPUT_LIMIT_BYTES }))
    ctx.setProp(ctx.global, "__init_json", initJson)
    initJson.dispose()

    const prelude = ctx.evalCode(PRELUDE, "prelude.js")
    if (prelude.error) throw vmError(ctx, prelude.error)
    prelude.value.dispose()
    const encodeFn = ctx.getProp(ctx.global, "__encode")
    ctx.unwrapResult(ctx.evalCode("delete globalThis.__encode")).dispose()
    const usageHandle = runtime.computeMemoryUsage()
    const usage = ctx.dump(usageHandle)
    usageHandle.dispose()
    runtime.setMemoryLimit(usage.memory_used_size + MEMORY_LIMIT_BYTES)

    // --- User code ---
    const userStart = performance.now()
    bootstrapMs = userStart - startedAt
    deadline = userStart + timeoutMs

    let wrapped: string
    try {
      wrapped = wrapUserCode(code, "module")
    } catch (error) {
      throw new ExecError("syntax", error instanceof Error ? error.message : String(error))
    }
    debug("wrapped code:", wrapped)
    const moduleResult = ctx.evalCode(wrapped, "file:///code.mjs", { type: "module" })
    if (moduleResult.error) throw vmError(ctx, moduleResult.error)

    // The module evaluates to its namespace (possibly via a promise); `default` is the promise of the user's result.
    const namespace = settle(ctx, runtime, moduleResult.value)
    const defaultExport = ctx.getProp(namespace, "default")
    namespace.dispose()
    const value = settle(ctx, runtime, defaultExport)

    let inspected: string | undefined
    if (ctx.typeof(value) !== "undefined") {
      const remaining = Math.max(0, OUTPUT_LIMIT_BYTES - outputBytes)
      const budget = ctx.newNumber(remaining)
      const encoded = ctx.callFunction(encodeFn, ctx.undefined, value, budget)
      budget.dispose()
      if (encoded.error) throw vmError(ctx, encoded.error)
      if (ctx.typeof(encoded.value) !== "string") stop("output")
      else {
        inspected = inspect(decodeValue(JSON.parse(ctx.getString(encoded.value))))
        if (!spend(utf8Length(inspected))) inspected = undefined
      }
      encoded.value.dispose()
    }
    value.dispose()
    encodeFn.dispose()
    if (stopKind) throw new ExecError(stopKind, "")

    options.onTimings?.({ bootstrapMs, userMs: performance.now() - startedAt - bootstrapMs })
    return { success: true, output: output.join("\n"), value: inspected }
  } catch (error) {
    debug("execute failed:", error)
    const kind: ErrorKind = stopKind ?? (error instanceof ExecError ? error.kind : "runtime")
    const message = kind === "timeout"
      ? TIMEOUT_ERROR(timeoutMs)
      : kind === "output"
      ? OUTPUT_LIMIT_ERROR
      : error instanceof Error
      ? error.message
      : String(error)
    options.onTimings?.({ bootstrapMs, userMs: performance.now() - startedAt - bootstrapMs })
    return { success: false, output: "", value: undefined, error: message, kind }
  }
  // The runtime is not disposed: the executor process exits after one run, and disposing with leaked handles
  // after an interrupted or failed run asserts in the debug build.
}

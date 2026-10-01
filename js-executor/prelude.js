// Evaluated inside QuickJS before user code. Sets up `$`, `$name` command globals, fields, and the lib helpers.
//
// Expects these globals, installed by executor.ts and removed here:
//   __init_json: JSON string { fields: Record<string, unknown>, commands: { name, content, run }[] }
//   __host_print(json): receives an encoded argument list (see __encode) and appends one output line
//   __host_wrap(name, code): returns JSON { ok: true, code } or { ok: false, error } with the wrapped function body
//
// Everything here runs in the sandbox; only the three functions above cross into the host, and only with strings.
;(() => {
  const hostPrint = globalThis.__host_print
  const hostWrap = globalThis.__host_wrap
  const init = JSON.parse(globalThis.__init_json)
  delete globalThis.__init_json
  delete globalThis.__host_print
  delete globalThis.__host_wrap

  // --- Encoding values for printing on the host (Deno.inspect) ---

  // Turns a VM value into a JSON-safe tree that the host rebuilds into an equivalent value for Deno.inspect.
  // Primitives other than non-finite numbers are kept as-is; everything else is a tagged object.
  function encode(value) {
    const ids = new Map()
    const go = (v) => {
      switch (typeof v) {
        case "undefined":
          return { t: "u" }
        case "number":
          return Number.isFinite(v) && !Object.is(v, -0) ? v : { t: "n", v: Object.is(v, -0) ? "-0" : String(v) }
        case "bigint":
          return { t: "b", v: String(v) }
        case "symbol":
          return { t: "y", v: v.description }
        case "string":
        case "boolean":
          return v
      }
      if (v === null) return null
      if (ids.has(v)) return { t: "ref", i: ids.get(v) }
      const i = ids.size
      ids.set(v, i)
      const props = () => Object.keys(v).map((k) => [k, go(v[k])])
      if (typeof v === "function") {
        const kind = v.constructor && v.constructor.name
        return { t: "f", i, n: v.name, k: kind, p: props() }
      }
      if (Array.isArray(v)) {
        const items = []
        for (let k = 0; k < v.length; k++) items.push(k in v ? go(v[k]) : { t: "h" })
        return { t: "a", i, v: items }
      }
      if (v instanceof Date) return { t: "d", i, v: v.getTime() }
      if (v instanceof RegExp) return { t: "r", i, s: v.source, f: v.flags }
      if (v instanceof Error) return { t: "e", i, n: v.name, m: v.message, s: v.stack }
      if (v instanceof Map) return { t: "m", i, v: Array.from(v, ([k, x]) => [go(k), go(x)]) }
      if (v instanceof Set) return { t: "s", i, v: Array.from(v, go) }
      if (v instanceof Promise) return { t: "p", i }
      const proto = Object.getPrototypeOf(v)
      const c = proto === null ? null : (proto.constructor && proto.constructor.name) || "Object"
      return { t: "o", i, c, p: props() }
    }
    return go(value)
  }
  globalThis.__encode = (v) => JSON.stringify(encode(v))

  // --- Output ---

  function print(...args) {
    hostPrint(JSON.stringify(args.map((a) => (typeof a === "object" && a !== null ? encode(a) : String(a)))))
  }
  globalThis.console = { log: print }

  // --- lib (mirrors js-executor/lib.ts) ---

  function random(...args) {
    if (args.length === 1) {
      const arg = args[0]
      if (Array.isArray(arg)) {
        return arg[Math.floor(Math.random() * arg.length)]
      } else {
        throw new Error(
          `random(x) expects x to be an array, got ${typeof arg}. If you want to generate a random number, use random(min, max).`,
        )
      }
    } else if (args.length === 2) {
      return Math.floor(Math.random() * (args[1] - args[0] + 1)) + args[0]
    } else {
      throw new Error(
        `random can be used either like random([x, y, ...]) (with one argument) or random(min, max) (with two arguments), got ${args.length} arguments.`,
      )
    }
  }

  function shuffle(array) {
    const result = [...array]
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[result[i], result[j]] = [result[j], result[i]]
    }
    return result
  }

  const makeLib = () => ({
    min: Math.min,
    max: Math.max,
    tail: (array) => array.slice(1),
    init: (array) => array.slice(0, -1),
    drop: (array, n) => array.slice(n),
    dropLast: (array, n) => array.slice(0, -n),
    reverse: (array) => [...array].reverse(),
    random,
    shuffle,
    print,
  })

  const fields = { ...init.fields, lib: makeLib(), ...makeLib() }

  // --- Commands ---

  // Wraps a command's code into a function body on first use; the host parses it with meriyah.
  const wrappedCache = new Map()
  function wrapCommand(name, code) {
    if (!wrappedCache.has(name)) {
      const res = JSON.parse(hostWrap(name, code))
      wrappedCache.set(
        name,
        res.ok
          ? res.code
          : `throw new Error(${
            JSON.stringify(`Command '${name}' has invalid JavaScript and cannot be executed: ${res.error}`)
          })`,
      )
    }
    return wrappedCache.get(name)
  }

  // `this` inside a command's code
  function commandRecord(command) {
    const record = {
      name: command.name,
      content: command.content,
      code: command.run || null,
    }
    Object.defineProperty(record, "wrappedCode", {
      get: () => (record.code ? wrapCommand(record.name, record.code) : null),
      enumerable: true,
    })
    return record
  }

  function runCommand(record, self, args) {
    if (record.code && record.code.trim()) {
      const func = new Function("args", wrapCommand(record.name, record.code))
      return func.call(self, args)
    } else {
      console.log(record.content)
    }
  }

  const $commandsMap__ = {}
  const $ = {
    commands: $commandsMap__,
    cmd: function(name, ...args) {
      if (!(name in this.commands)) {
        throw new Error("Command not found: " + name)
      }
      return this.commands[name].run(...args)
    },
  }
  globalThis.$ = $

  for (const key in fields) {
    $[key] = fields[key]
    globalThis[key] = fields[key]
  }

  const records = init.commands.map(commandRecord)
  globalThis.$init__ = { fields, commands: records }

  for (const record of records) {
    const obj = Object.create(record)
    Object.assign(obj, {
      name: record.name,
      content: record.content,
      code: record.code,
      run: function(...args) {
        return runCommand(record, this, args)
      },
    })
    $commandsMap__[record.name] = obj
  }

  const normalizeCommandName = (name) => name.replace(/-/g, "_")

  function createCommandObject(record) {
    const cmd = function(...args) {
      return runCommand(record, record, args)
    }
    cmd._name = record.name
    cmd._content = record.content
    cmd._code = record.code
    Object.defineProperty(cmd, "_wrappedCode", { get: () => record.wrappedCode, enumerable: true })
    cmd._run = function() {
      return cmd()
    }
    return cmd
  }

  const commandGlobals = {}

  // First pass: nested commands (with slashes)
  for (const record of records) {
    const parts = record.name.split("/")
    if (parts.length > 1) {
      let current = commandGlobals
      for (let i = 0; i < parts.length - 1; i++) {
        const part = normalizeCommandName(parts[i])
        if (!current[part]) {
          current[part] = {}
        }
        current = current[part]
      }
      current[normalizeCommandName(parts[parts.length - 1])] = createCommandObject(record)
    }
  }

  // Second pass: direct commands (no slashes)
  for (const record of records) {
    if (!record.name.includes("/")) {
      const normalizedName = normalizeCommandName(record.name)
      const existing = commandGlobals[normalizedName]
      if (existing && typeof existing === "object" && !existing._name) {
        // A container for nested commands: make it callable and keep its children
        const selfCommand = createCommandObject(record)
        existing._self = selfCommand
        const callableContainer = function() {
          return selfCommand.apply(this, arguments)
        }
        Object.assign(callableContainer, existing)
        commandGlobals[normalizedName] = callableContainer
      } else {
        commandGlobals[normalizedName] = createCommandObject(record)
      }
    }
  }

  for (const [name, obj] of Object.entries(commandGlobals)) {
    globalThis["$" + name] = obj
  }
})()

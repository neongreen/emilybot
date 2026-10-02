// Evaluated inside QuickJS before user code. Sets up `$`, `$name` command globals, fields, and the lib helpers.
//
// Expects these globals, installed by executor.ts and removed here:
//   __init_json: JSON string
//     { fields: Record<string, unknown>, commands: { id?, name, content, run }[], outputLimit, storeEnabled }
//   __host_print(json): receives an encoded argument list (see __encode) and appends one output line
//   __host_wrap(name, code): returns JSON { ok: true, code } or { ok: false, error } with the wrapped function body
//   __host_store_load(id): returns JSON { version, data } or { error } for the store of the alias with this id
//
// Everything here runs in the sandbox; only the functions above cross into the host, and only with strings.
// Leaves `__encode` and `__store_flush` for the host to pick up and remove.
;(() => {
  const hostPrint = globalThis.__host_print
  const hostWrap = globalThis.__host_wrap
  const hostStoreLoad = globalThis.__host_store_load
  const init = JSON.parse(globalThis.__init_json)
  delete globalThis.__init_json
  delete globalThis.__host_print
  delete globalThis.__host_wrap
  delete globalThis.__host_store_load

  // --- Encoding values for printing on the host (Deno.inspect) ---

  // Turns a VM value into a JSON-safe tree that the host rebuilds into an equivalent value for Deno.inspect.
  // Primitives other than non-finite numbers are kept as-is; everything else is a tagged object.
  // Shared (non-circular) references are expanded, like Deno.inspect does, so the size of the tree bounds the size
  // of the printed text; `budget` caps that size and encoding throws OVER_BUDGET past it.
  const OVER_BUDGET = {}
  const MAX_DEPTH = 100 // matches INSPECT_DEPTH in executor.ts
  function encode(value, budget) {
    let size = 0
    let nextId = 0
    const ancestors = new Map()
    const charge = (n) => {
      size += n
      if (size > budget) throw OVER_BUDGET
    }
    const go = (v, depth) => {
      charge(8)
      switch (typeof v) {
        case "undefined":
          return { t: "u" }
        case "number":
          return Number.isFinite(v) && !Object.is(v, -0) ? v : { t: "n", v: Object.is(v, -0) ? "-0" : String(v) }
        case "bigint":
          charge(String(v).length)
          return { t: "b", v: String(v) }
        case "symbol":
          charge(String(v.description).length)
          return { t: "y", v: v.description }
        case "string":
          charge(v.length)
          return v
        case "boolean":
          return v
      }
      if (v === null) return null
      if (ancestors.has(v)) return { t: "ref", i: ancestors.get(v) }
      if (depth > MAX_DEPTH) return { t: "deep", a: Array.isArray(v) }
      const i = nextId++
      ancestors.set(v, i)
      try {
        const props = () =>
          Object.keys(v).map((k) => {
            charge(k.length)
            return [k, go(v[k], depth + 1)]
          })
        if (typeof v === "function") {
          const kind = v.constructor && v.constructor.name
          return { t: "f", i, n: v.name, k: kind, p: props() }
        }
        if (Array.isArray(v)) {
          const items = []
          for (let k = 0; k < v.length; k++) items.push(k in v ? go(v[k], depth + 1) : (charge(8), { t: "h" }))
          return { t: "a", i, v: items }
        }
        if (v instanceof Date) return { t: "d", i, v: v.getTime() }
        if (v instanceof RegExp) {
          charge(v.source.length)
          return { t: "r", i, s: v.source, f: v.flags }
        }
        if (v instanceof Error) {
          charge(String(v.message).length + String(v.stack).length)
          return { t: "e", i, n: v.name, m: v.message, s: v.stack }
        }
        if (v instanceof Map) return { t: "m", i, v: Array.from(v, ([k, x]) => [go(k, depth + 1), go(x, depth + 1)]) }
        if (v instanceof Set) return { t: "s", i, v: Array.from(v, (x) => go(x, depth + 1)) }
        if (v instanceof Promise) return { t: "p", i }
        const proto = Object.getPrototypeOf(v)
        const c = proto === null ? null : (proto.constructor && proto.constructor.name) || "Object"
        return { t: "o", i, c, p: props() }
      } finally {
        ancestors.delete(v)
      }
    }
    return go(value, 0)
  }
  // JSON of the encoded value, or null if it is over budget
  const encodeJson = (v, budget) => {
    try {
      return JSON.stringify(encode(v, budget))
    } catch (e) {
      if (e === OVER_BUDGET) return null
      throw e
    }
  }
  globalThis.__encode = encodeJson

  // --- Output ---

  // The host enforces the aggregate output budget; this bounds the work for a single call.
  function print(...args) {
    let encoded = []
    try {
      for (const a of args) encoded.push(typeof a === "object" && a !== null ? encode(a, init.outputLimit) : String(a))
    } catch (e) {
      if (e !== OVER_BUDGET) throw e
      encoded = null
    }
    hostPrint(encoded === null ? null : JSON.stringify(encoded))
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

  // --- Per-alias store (`this.store`) ---
  //
  // Loaded lazily from the host on first use. Reads see this run's own writes; writes are buffered here and handed
  // to the host (`__store_flush`) after the run succeeds, which commits them only if no touched store changed.
  const MAX_KEY_LENGTH = 100
  const loadedStores = new Map() // alias id -> { data: Map, writes: Map key -> { v } | { d: true } }
  const storeApis = new Map() // alias id -> the `this.store` object

  function openStore(id) {
    let s = loadedStores.get(id)
    if (!s) {
      const res = JSON.parse(hostStoreLoad(id))
      if (res.error) throw new Error(`this.store is unavailable: ${res.error}`)
      s = { data: new Map(Object.entries(res.data)), writes: new Map() }
      loadedStores.set(id, s)
    }
    return s
  }

  function checkKey(method, key) {
    if (typeof key !== "string" || key.length === 0 || key.length > MAX_KEY_LENGTH) {
      throw new Error(
        `this.store.${method}: keys must be non-empty strings of at most ${MAX_KEY_LENGTH} characters, got ${
          typeof key === "string" ? `a string of length ${key.length}` : typeof key
        }`,
      )
    }
  }

  // A deep copy of `value` if it is JSON (null, boolean, finite number, string, array, plain object); throws otherwise.
  function jsonCopy(value, path, ancestors) {
    const reject = (what) => {
      throw new Error(
        `this.store.set: ${path} is ${what}, which cannot be stored. `
          + `Store only null, booleans, finite numbers, strings, arrays and plain objects.`,
      )
    }
    switch (typeof value) {
      case "string":
      case "boolean":
        return value
      case "number":
        return Number.isFinite(value) ? value : reject(String(value))
      case "undefined":
        return reject("undefined")
      case "function":
        return reject("a function")
      case "bigint":
        return reject("a bigint")
      case "symbol":
        return reject("a symbol")
    }
    if (value === null) return null
    if (ancestors.includes(value)) reject("a circular reference")
    ancestors.push(value)
    try {
      if (Array.isArray(value)) {
        const out = []
        for (let i = 0; i < value.length; i++) {
          if (!(i in value)) reject(`an array with an empty slot at index ${i}`)
          out.push(jsonCopy(value[i], `${path}[${i}]`, ancestors))
        }
        return out
      }
      const proto = Object.getPrototypeOf(value)
      if (proto !== Object.prototype && proto !== null) {
        reject(`a ${(proto && proto.constructor && proto.constructor.name) || "non-plain object"}`)
      }
      const out = {}
      for (const k of Object.keys(value)) {
        Object.defineProperty(out, k, {
          value: jsonCopy(value[k], `${path}.${k}`, ancestors),
          enumerable: true,
          writable: true,
          configurable: true,
        })
      }
      return out
    } finally {
      ancestors.pop()
    }
  }

  const clone = (v) => JSON.parse(JSON.stringify(v))

  function storeFor(id) {
    if (!storeApis.has(id)) {
      storeApis.set(
        id,
        Object.freeze({
          get(key, fallback) {
            checkKey("get", key)
            const s = openStore(id)
            return s.data.has(key) ? clone(s.data.get(key)) : fallback
          },
          set(key, value) {
            checkKey("set", key)
            const copy = jsonCopy(value, "value", [])
            const s = openStore(id)
            s.data.set(key, copy)
            s.writes.set(key, { v: copy })
          },
          delete(key) {
            checkKey("delete", key)
            const s = openStore(id)
            s.data.delete(key)
            s.writes.set(key, { d: true })
          },
          keys() {
            return Array.from(openStore(id).data.keys())
          },
        }),
      )
    }
    return storeApis.get(id)
  }

  // Writes of every store this run loaded, as JSON { [id]: { [key]: { v } | { d: true } } }
  globalThis.__store_flush = () => {
    const out = {}
    for (const [id, s] of loadedStores) {
      const writes = {}
      for (const [key, w] of s.writes) {
        Object.defineProperty(writes, key, { value: w, enumerable: true, writable: true, configurable: true })
      }
      out[id] = writes
    }
    return JSON.stringify(out)
  }

  // --- Commands ---

  // Wraps a command's code into a function body on first use; the host parses it with meriyah.
  // Keyed by the code itself, so a command object whose `code` was reassigned gets its new code wrapped.
  const wrappedCache = new Map()
  function wrapCommand(name, code) {
    if (!wrappedCache.has(code)) {
      const res = JSON.parse(hostWrap(name, code))
      wrappedCache.set(code, res)
    }
    const res = wrappedCache.get(code)
    if (res.ok) return res.code
    const message = `Command '${name}' has invalid JavaScript and cannot be executed: ${res.error}`
    return `throw new SyntaxError(${JSON.stringify(message)})`
  }

  // `this` inside a command's code
  // record -> { id, run } as received from the host; not visible on the record itself
  const storedCommands = new WeakMap()

  function commandRecord(command) {
    const record = {
      name: command.name,
      content: command.content,
      code: command.run || null,
    }
    storedCommands.set(record, { id: command.id, run: command.run || null })
    Object.defineProperty(record, "wrappedCode", {
      get: () => (record.code ? wrapCommand(record.name, record.code) : null),
      enumerable: true,
    })
    return record
  }

  // `stored` is the record the command came from. `this.store` is provided only while running that alias's stored
  // code unchanged. This keeps one-off code from writing state by accident; it is not a security boundary, since
  // user code controls the whole VM. The host enforces scoping, quotas and the commit rules regardless.
  function runCommand(record, self, args, stored) {
    if (record.code && record.code.trim()) {
      const func = new Function("args", wrapCommand(record.name, record.code))
      const info = storedCommands.get(stored)
      if (init.storeEnabled && info && info.id && record.code === info.run) {
        self = Object.create(self, { store: { value: storeFor(info.id), enumerable: false } })
      }
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
      // Reads `this` like before, so reassigning `$.commands.x.code` changes what runs
      run: function(...args) {
        return runCommand(this, this, args, record)
      },
    })
    $commandsMap__[record.name] = obj
  }

  const normalizeCommandName = (name) => name.replace(/-/g, "_")

  function createCommandObject(record) {
    const cmd = function(...args) {
      return runCommand(record, record, args, record)
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

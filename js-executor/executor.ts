/**
 * QuickJS wrapper for sandboxed JavaScript execution
 *
 * WARNING: This executor can hang forever on fetches because we do them synchronously.
 * Timeout protection must be implemented at the Python/process level using asyncio.wait_for()
 * or by using gtimeout when running manually.
 */

import { Arena } from "quickjs-emscripten-sync"
import { DEBUG_SYNC, newQuickJSWASMModule, RELEASE_SYNC } from "quickjs-emscripten/variants"
import { quickJsModuleLoader, quickJsModuleNormalizer } from "./imports.ts"
import { debug } from "./logging.ts"
import { wrapUserCode } from "./parse.ts"
import type { CommandData, ExecutionResult } from "./types.ts"

export async function execute(
  fields: Record<string, any> = {},
  commands: CommandData[] = [],
  code: string,
): Promise<ExecutionResult> {
  const isDebug = Deno.env.get("DEBUG") === "1"

  // Use sync version for all code
  const QuickJS = await newQuickJSWASMModule(isDebug ? DEBUG_SYNC : RELEASE_SYNC)
  const runtime = QuickJS.newRuntime()

  // Set up module loader for external imports
  runtime.setModuleLoader(quickJsModuleLoader, quickJsModuleNormalizer)

  const ctx = runtime.newContext()

  const arena = new Arena(ctx, {
    isMarshalable(_target: any): boolean {
      // We want to marshal functions and tagging/whitelisting them is tricky, so we just allow everything
      return true
    },
  })
  arena.context.runtime.setMemoryLimit(1024 * 1024 * 10) // 10 MB

  try {
    // Capture console.log output from the user code
    const consoleOutput: string[] = []
    arena.expose({
      console: {
        log: (...args: any[]) => {
          // Make the output for objects nicer
          const showArg = (arg: any) => {
            if (typeof arg === "object" && arg !== null) {
              // it doesn't seem to allow Deno.customInspect to run when it's inside QuickJS, so that's good
              return Deno.inspect(arg, { depth: 999, colors: false, compact: true, breakLength: 100 }) // Use Deno's inspect for better object output
            }
            return String(arg)
          }
          consoleOutput.push(args.map(showArg).join(" "))
        },
      },
    })

    const exposed = {
      "$init__": {
        fields,
        "commands": commands.map((c) => {
          let wrappedCode = null
          if (c.run) {
            try {
              wrappedCode = wrapUserCode(c.run, "functionBody")
            } catch (error) {
              // Create a fallback wrapped code that throws an error when called
              wrappedCode = `throw new Error(`
                + JSON.stringify(
                  `Command '${c.name}' has invalid JavaScript and cannot be executed: `
                    + (error instanceof Error ? error.message : String(error)),
                ) + `)`
            }
          }
          return {
            name: c.name,
            content: c.content,
            code: c.run || null,
            wrappedCode,
          }
        }),
      },
    }
    debug("exposing", exposed)
    arena.expose(exposed)
    debug("expose done")

    // Set up the command system.
    // TODO: move this to a separate JS file and use `import` to load it?
    arena.evalCode(`
        const $commandsMap__ = ({})
        const $ = ({
          commands: $commandsMap__,
          cmd: function(name, ...args) {
            if (!(name in this.commands)) {
              throw new Error("Command not found: " + name)
            }
            return this.commands[name].run(...args)
          },
        })
        
        // Inject context variables as globals
        for (const key in $init__.fields) {
          $[key] = $init__.fields[key]
          // Also make them available as global variables
          globalThis[key] = $init__.fields[key]
        }

      for (const command of $init__.commands) {
        const obj = ({
          name: command.name,
          content: command.content,
          code: command.code || null,
          wrappedCode: command.wrappedCode || null,
          run: function(...args) {
            if (this.code && this.code.trim()) {
              // Create a function that has access to the args parameter and this context
              // TODO: use createCommandObject instead
              const func = new Function('args', this.wrappedCode)
              return func.call(this, args)
            } else {
              console.log(this.content)
            }
          }
        })
        $commandsMap__[command.name] = obj
      }
      
      // Create global command objects
      function normalizeCommandName(name) {
        return name.replace(/-/g, '_')
      }
      
      // Needs: name, content, code, wrappedCode
      function createCommandObject(command) {
        const { name, content, code, wrappedCode } = command
        const cmd = function(...args) {
          if (code && code.trim()) {
            const func = new Function('args', wrappedCode)
            return func.call(command, args)  // "this" will be the command, args as parameter
          } else {
            console.log(content)
          }
        }
        cmd._name = name
        cmd._content = content
        cmd._code = code || null
        cmd._wrappedCode = wrappedCode || null
        cmd._run = function() {
          return cmd()
        }
        return cmd
      }
      
      // Build global command objects
      const commandGlobals = {}
      
      // First pass: handle nested commands (with slashes)
      for (const command of $init__.commands) {
        const parts = command.name.split('/')
        if (parts.length > 1) {
          let current = commandGlobals
          for (let i = 0; i < parts.length - 1; i++) {
            const part = normalizeCommandName(parts[i])
            if (!current[part]) {
              current[part] = {}
            }
            current = current[part]
          }
          const lastPart = normalizeCommandName(parts[parts.length - 1])
          current[lastPart] = createCommandObject(command)
        }
      }
      
      // Second pass: handle direct commands (no slashes)
      for (const command of $init__.commands) {
        if (!command.name.includes('/')) {
          const normalizedName = normalizeCommandName(command.name)
          // Check if this name already exists as a container for nested commands
          if (commandGlobals[normalizedName] && typeof commandGlobals[normalizedName] === 'object' && !commandGlobals[normalizedName]._name) {
            // This is a container object for nested commands, don't overwrite it
            // Instead, add the command as a property and make the container callable
            const selfCommand = createCommandObject(command)
            commandGlobals[normalizedName]._self = selfCommand
            // Make the container callable by delegating to the self command
            const container = commandGlobals[normalizedName]
            const callableContainer = function() {
              return selfCommand.apply(this, arguments)
            }
            // Copy all properties from the container to the callable
            Object.assign(callableContainer, container)
            commandGlobals[normalizedName] = callableContainer
          } else {
            commandGlobals[normalizedName] = createCommandObject(command)
          }
        }
      }
      
      // Add all command objects to global scope
      for (const [name, obj] of Object.entries(commandGlobals)) {
        globalThis["$" + name] = obj
      }
    `)

    debug("after initial evalCode")

    // Execute the user code as a module
    debug("wrapped code:", wrapUserCode(code, "module"))
    const handle = ctx.evalCode(wrapUserCode(code, "module"), "file:///code.mjs", { type: "module" })
    debug("after evalCode:", handle)

    // Get the result and handle async values
    let result = arena._unwrapResultAndUnmarshal(handle)
    arena.executePendingJobs()
    // Resolve promises but only when they are promises
    if (result instanceof Promise) {
      debug("result is a promise:", result)
      result = await result
    }
    if (result.default) {
      debug("stripping default export:", result)
      result = result.default
    }
    if (result instanceof Promise) {
      debug("unwrapping promise again:", result)
      result = await result
    }
    debug("result:", result)

    return {
      success: true,
      output: consoleOutput.join("\n"),
      value: result !== undefined
        ? Deno.inspect(result, { depth: 999, colors: false, compact: true, breakLength: 100 })
        : undefined,
    }
  } catch (error) {
    return {
      success: false,
      output: "",
      value: undefined,
      error: error instanceof Error ? error.message : String(error),
    }
  } finally {
    // Clean up resources - let QuickJS handle cleanup automatically
    // TODO: do we even care
  }
}

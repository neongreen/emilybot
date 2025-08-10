/**
 * QuickJS wrapper for sandboxed JavaScript execution
 */

import { Arena } from "quickjs-emscripten-sync"
import {
  DEBUG_ASYNC,
  DEBUG_SYNC,
  newQuickJSAsyncWASMModule,
  newQuickJSWASMModule,
  RELEASE_ASYNC,
  RELEASE_SYNC,
} from "quickjs-emscripten/variants"
import { hasImports, quickJsModuleLoader, quickJsModuleNormalizer } from "./imports.ts"
import { debug } from "./logging.ts"
import { wrapUserCode } from "./parse.ts"
import type { CommandData, ExecutionResult } from "./types.ts"

export async function execute(
  fields: Record<string, any> = {},
  commands: CommandData[] = [],
  code: string,
): Promise<ExecutionResult> {
  const hasImportStatements = hasImports(code)
  const isDebug = Deno.env.get("DEBUG") === "1"

  let runtime, ctx

  if (hasImportStatements) {
    // Use async version for code with imports.
    // It's much slower but currently we can't do imports without it.
    const AsyncQuickJS = await newQuickJSAsyncWASMModule(isDebug ? DEBUG_ASYNC : RELEASE_ASYNC)
    runtime = AsyncQuickJS.newRuntime()

    // Set up module loader for external imports
    runtime.setModuleLoader(quickJsModuleLoader, quickJsModuleNormalizer)

    ctx = runtime.newContext()
  } else {
    // Use sync version for code without imports
    const QuickJS = await newQuickJSWASMModule(isDebug ? DEBUG_SYNC : RELEASE_SYNC)
    runtime = QuickJS.newRuntime()

    ctx = runtime.newContext()
  }

  const arena = new Arena(ctx, {
    isMarshalable(_target: any): boolean {
      // We want to marshal functions and tagging/whitelisting them is tricky, so we just allow everything
      return true
    },
  })
  arena.context.runtime.setMemoryLimit(1024 * 1024) // 1 MB

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

    arena.expose({ "$init__": { "fields": fields, "commands": commands } })
    debug("after expose", { fields, commands })

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
          code: command.run || null,
          run: function(...args) {
            if (this.code && this.code.trim()) {
              // Create a function that has access to the args parameter and this context
              // TODO: for commands that look like modules (with imports etc), this won't work
              const func = new Function('args', this.code)
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
      
      function createCommandObject(name, content, code) {
        const cmd = function(...args) {
          if (code && code.trim()) {
            const commandContext = {name, content, code}
            const func = new Function('args', code)
            return func.call(commandContext, args)  // "this" will be the commandContext, args as parameter
          } else {
            console.log(content)
          }
        }
        cmd._name = name
        cmd._content = content
        cmd._code = code || null
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
          current[lastPart] = createCommandObject(command.name, command.content, command.run)
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
            const selfCommand = createCommandObject(command.name, command.content, command.run)
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
            commandGlobals[normalizedName] = createCommandObject(command.name, command.content, command.run)
          }
        }
      }
      
      // Add all command objects to global scope
      for (const [name, obj] of Object.entries(commandGlobals)) {
        globalThis["$" + name] = obj
      }
    `)

    debug("after initial evalCode")

    // Execute the user code as an async module
    debug("wrapped code:", wrapUserCode(code))
    const handle = await ctx.evalCode(wrapUserCode(code), "file:///code.mjs", { type: "module" })
    debug("after evalCodeAsync:", handle)

    // Get the result and handle async values
    let result = arena._unwrapResultAndUnmarshal(handle)
    arena.executePendingJobs()
    // Resolve promises but only when they are promises
    if (result instanceof Promise) {
      debug("result is a promise:", result)
      result = await result
    }
    result = result.default
    if (result instanceof Promise) {
      debug("result.default is a promise:", result)
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
    if (error instanceof Error && error.message === "timeout") {
      return {
        success: false,
        output: "",
        value: undefined,
        error: "Execution timed out",
      }
    } else {
      return {
        success: false,
        output: "",
        value: undefined,
        error: error instanceof Error ? error.message : String(error),
      }
    }
  } finally {
    // Clean up resources - let QuickJS handle cleanup automatically
    // Explicit disposal can cause assertion failures with async modules
  }
}

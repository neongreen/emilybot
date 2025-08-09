/**
 * QuickJS wrapper for sandboxed JavaScript execution
 */

import { getQuickJS } from "quickjs-emscripten"
import { Arena } from "quickjs-emscripten-sync"
import { type CommandData, type ExecutionResult } from "./types.ts"

export async function execute(
  fields: Record<string, any> = {},
  commands: CommandData[] = [],
  code: string,
): Promise<ExecutionResult> {
  const QuickJS = await getQuickJS()
  const ctx = QuickJS.newContext()
  const arena = new Arena(ctx, {
    isMarshalable(_target: any): boolean {
      // We want to marshal functions and tagging/whitelisting them is tricky
      return true
    },
  })

  arena.context.runtime.setMemoryLimit(1024 * 1024) // Set memory limit to 1MB

  try {
    // Capture console.log output
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
    // TODO: can I deepfreeze or smth? do I even need to?
    // TODO: rename code run etc
    // TODO: forbid 'console' etc
    arena.evalCode(`
      const $commandsMap__ = ({})
      const $ = ({
        commands: $commandsMap__,
        cmd: function(name) {
          if (!(name in this.commands)) {
            throw new Error("Command not found: " + name)
          }
          return this.commands[name].run()
        },
      })
      for (const key in $init__.fields) {
        $[key] = $init__.fields[key]
      }

      for (const command of $init__.commands) {
        const obj = ({
          name: command.name,
          content: command.content,
          code: command.run || null,
          run: function() {
            if (this.code && this.code.trim()) {
              return eval("(() => {\\n" + this.code + "\\n})()")
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
        const cmd = function() {
          if (code && code.trim()) {
            // Create a context object with command properties
            const commandContext = {
              name: name,
              content: content,
              code: code
            }
            // Use Function constructor to create a function with proper 'this' binding
            const func = new Function('name', 'content', 'code', code)
            return func.call(commandContext, name, content, code)
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

    const result = arena.evalCode(code)
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
  }
}

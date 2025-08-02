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

    arena.expose({ "$$": { "fields": fields, "commands": commands } })
    // TODO: can I deepfreeze or smth? do I even need to?
    // TODO: rename code run etc
    // TODO: forbid 'console' etc
    arena.evalCode(`
      const commandsMap = ({})
      const $ = ({
        commands: commandsMap,
        cmd: function(name) {
          if (!(name in this.commands)) {
            throw new Error("Command not found: " + name)
          }
          return this.commands[name].run()
        },
      })
      for (const key in $$.fields) {
        $[key] = $$.fields[key]
      }
      for (const command of $$.commands) {
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
        commandsMap[command.name] = obj
      }
      $.commands = commandsMap
      Object.freeze($)
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

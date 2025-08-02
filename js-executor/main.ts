/**
 * Main Deno CLI script for JavaScript execution with hard timeout
 */

import z, { success, ZodError } from "zod/v4"
import { execute } from "./executor.ts"
import { lib } from "./lib.ts"
import { validateCommands } from "./types.ts"

async function main() {
  if (Deno.args.length !== 3) {
    console.error("Usage: main.ts <code> <fields> <commands>")
    Deno.exit(1)
  }

  const [code, fieldsJson, commandsJson] = Deno.args

  let fields, commands
  try {
    fields = JSON.parse(fieldsJson)
    if (typeof fields !== "object" || fields === null) {
      throw new Error("Fields must be a valid JSON object")
    }
    commands = validateCommands(JSON.parse(commandsJson))
  } catch (error) {
    if (error instanceof ZodError) {
      console.error(`Failed to parse or validate input:\n${z.prettifyError(error)}`)
    } else {
      console.error(`Error: ${error instanceof Error ? error.message : String(error)}`)
    }
    Deno.exit(1)
  }

  try {
    // Create a hard timeout that will kill the process
    const timeoutId = setTimeout(() => {
      console.error("Execution timed out after 1 second")
      Deno.exit(1)
    }, 1000)

    const context = {
      ...fields,
      lib: lib,
    }

    try {
      // Execute JavaScript code
      const result = await execute(context, commands, code)

      // Clear timeout since execution completed
      clearTimeout(timeoutId)

      if (result.success) {
        console.log(JSON.stringify(result))
        Deno.exit(0)
      } else {
        console.error(result.error || "Unknown execution error")
        Deno.exit(1)
      }
    } catch (error) {
      clearTimeout(timeoutId)
      throw error
    }
  } catch (error) {
    console.error(`Execution failed: ${error instanceof Error ? error.message : String(error)}`)
    Deno.exit(1)
  }
}

if (import.meta.main) {
  await main()
}

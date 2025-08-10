/**
 * Main Deno CLI script for JavaScript execution
 *
 * WARNING: This executor can hang forever on fetches (which we have to do synchronously).
 * Timeout protection must be implemented at the Python/process level using asyncio.wait_for()
 * or by using gtimeout when running manually.
 */

import { z, ZodError } from "zod/v4"
import { getArgs } from "./cli.ts"
import { execute } from "./executor.ts"
import { lib } from "./lib.ts"
import { validateCommands, validateFields } from "./types.ts"

async function main() {
  const { code, fieldsFile, commandsFile } = getArgs()

  // console.debug("args", { code, fieldsFile, commandsFile })

  let fields, commands
  try {
    const fieldsJson = fieldsFile ? await Deno.readTextFile(fieldsFile) : "{}"
    const commandsJson = commandsFile ? await Deno.readTextFile(commandsFile) : "[]"

    fields = validateFields(JSON.parse(fieldsJson))
    commands = validateCommands(JSON.parse(commandsJson))
  } catch (error) {
    if (error instanceof ZodError) {
      console.error(`Failed to validate input:\n${z.prettifyError(error)}`)
    } else {
      console.error(`Error: ${error instanceof Error ? error.message : String(error)}`)
    }
    Deno.exit(1)
  }

  try {
    const context = {
      ...fields,
      lib: lib,
    }

    try {
      // Execute JavaScript code
      const result = await execute(context, commands, code)

      if (result.success) {
        console.log(JSON.stringify(result))
        Deno.exit(0)
      } else {
        console.error(result.error || "Unknown execution error")
        Deno.exit(1)
      }
    } catch (error) {
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

/**
 * Main Deno CLI script for JavaScript execution
 *
 * User code is interrupted after `--timeoutMs` of execution; import fetches time out on their own.
 * The Python caller still keeps a wall-clock backstop in case the process itself gets stuck.
 */

import { z, ZodError } from "zod/v4"
import { getArgs } from "./cli.ts"
import { execute } from "./executor.ts"
import { LIB_NAMES } from "./lib.ts"
import { validateCommands, validateFields } from "./types.ts"

async function main() {
  const { code, fieldsFile, commandsFile, timeoutMs } = getArgs()

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

  // If fields clash with lib, error out
  const clash = LIB_NAMES.filter((name) => Object.hasOwn(fields, name))
  if (clash.length > 0) {
    console.error(`Given fields clash with lib functions: ${clash.join(", ")}`)
    Deno.exit(1)
  }

  try {
    const result = await execute(fields, commands, code, { timeoutMs })
    if (result.success) {
      console.log(JSON.stringify(result))
      Deno.exit(0)
    } else {
      console.error(result.error || "Unknown execution error")
      Deno.exit(1)
    }
  } catch (error) {
    console.error(`Execution failed: ${error instanceof Error ? error.message : String(error)}`)
    Deno.exit(1)
  }
}

if (import.meta.main) {
  await main()
}

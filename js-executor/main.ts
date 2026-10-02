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
import { storeLoaderFromFile } from "./stores.ts"
import { validateCommands, validateFields } from "./types.ts"

async function main() {
  const { code, fieldsFile, commandsFile, timeoutMs, storesFile, serverId, storesError } = getArgs()

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

  // The result goes to stdout as JSON either way, so the caller can tell error kinds apart without parsing text.
  // Exit code 1 without JSON on stdout means the executor itself failed (bad input, crash).
  try {
    let timings
    const result = await execute(fields, commands, code, {
      timeoutMs,
      onTimings: (t) => timings = t,
      loadStore: storesError !== null
        ? () => ({ error: storesError })
        : storesFile && serverId
        ? storeLoaderFromFile(storesFile, serverId)
        : undefined,
    })
    console.log(JSON.stringify({ ...result, timings }))
    Deno.exit(result.success ? 0 : 1)
  } catch (error) {
    console.error(`Execution failed: ${error instanceof Error ? error.message : String(error)}`)
    Deno.exit(1)
  }
}

if (import.meta.main) {
  await main()
}

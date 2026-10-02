/**
 * CLI argument parsing and validation using Zod
 */

import { parseArgs } from "@std/cli"
import z, { ZodError } from "zod/v4"

// Zod schemas for argument validation
const ArgsSchema = z.object({
  _: z.array(z.string()).length(1).describe("Code to execute"),
  fieldsFile: z.string().optional().describe("Path to fields JSON file"),
  commandsFile: z.string().optional().describe("Path to commands JSON file"),
  timeoutMs: z.coerce.number().positive().optional().describe("User code execution budget in milliseconds"),
  storesFile: z.string().optional().describe("Path to store.json; with --serverId, enables `this.store`"),
  serverId: z.string().optional().describe("Server whose stores in --storesFile this run may use"),
  storesError: z.string().optional().describe("Why stores are unavailable; enables `this.store`, which then fails"),
})

export function getArgs(): {
  code: string
  fieldsFile: string | null
  commandsFile: string | null
  timeoutMs: number | undefined
  storesFile: string | null
  serverId: string | null
  storesError: string | null
} {
  // Parse these as strings: a Discord id does not fit in a JS number
  const rawArgs = parseArgs(Deno.args, {
    string: ["serverId", "storesError", "storesFile", "fieldsFile", "commandsFile"],
  })
  // console.debug("rawArgs", rawArgs)

  // Validate the parsed arguments structure
  let args
  try {
    args = ArgsSchema.parse(rawArgs)
  } catch (error) {
    if (error instanceof ZodError) {
      console.error(`Invalid command line arguments:\n${z.prettifyError(error)}`)
    } else {
      console.error(`Error validating arguments: ${error instanceof Error ? error.message : String(error)}`)
    }
    Deno.exit(1)
  }

  return {
    code: args._[0],
    fieldsFile: args.fieldsFile ?? null,
    commandsFile: args.commandsFile ?? null,
    timeoutMs: args.timeoutMs,
    storesFile: args.storesFile ?? null,
    serverId: args.serverId ?? null,
    storesError: args.storesError ?? null,
  }
}

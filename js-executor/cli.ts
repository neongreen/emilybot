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
})

export function getArgs(): {
  code: string
  fieldsFile: string | null
  commandsFile: string | null
} {
  const rawArgs = parseArgs(Deno.args)
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
  }
}

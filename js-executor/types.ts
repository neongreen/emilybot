/**
 * Type definitions for JavaScript execution context
 */

import { z } from "zod/v4"

export interface ExecutionResult {
  success: boolean
  output: string // Console.log output
  value?: string // Result of the executed code, if not undefined
  error?: string // Error message if failed
}

export type ErrorType = "timeout" | "memory" | "syntax" | "runtime"

export interface JSExecutionError {
  type: ErrorType
  message: string
}

export type CommandData = {
  name: string
  content: string
  run: string | null
}

// Command validation schemas
const CommandDataSchema = z.object({
  name: z.string(),
  content: z.string(),
  run: z.string().nullable(),
})

const CommandsArraySchema = z.array(CommandDataSchema)

/**
 * Validates commands array using zod schema
 */
export function validateCommands(commands: unknown): CommandData[] {
  return CommandsArraySchema.parse(commands)
}

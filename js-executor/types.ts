/**
 * Type definitions for JavaScript execution context
 */

import { z } from "zod/v4"

export interface ExecutionResult {
  success: boolean
  output: string // Console.log output
  value?: string // Result of the executed code, if not undefined
  error?: string // Error message if failed
  kind?: ErrorKind // Why it failed
  store?: StoreTransaction // Present when the run used `this.store`; commit it only if the run succeeded
}

/** A store as loaded from the host. */
export type StoreSnapshot = { version: number; data: Record<string, unknown> }

/** Loading a store: the store, a reason stores are unavailable, or "busy" (the file was being written; try again). */
export type StoreLoad = StoreSnapshot | { error: string } | { busy: true }

/** What a successful run did to stores: versions it read, and its writes per alias id. */
export type StoreTransaction = {
  reads: Record<string, number>
  writes: Record<string, Record<string, { v: unknown } | { d: true }>>
}

/** Why execution failed. Must match `ErrorType` in src/emilybot/execute/executor.py. */
export type ErrorKind = "timeout" | "memory" | "output" | "syntax" | "runtime" | "busy"

export type CommandData = {
  id?: string // Alias UUID; needed for `this.store`
  name: string
  content: string
  run: string | null
}

// Command validation schemas
const CommandDataSchema = z.object({
  id: z.string().optional(),
  name: z.string(),
  content: z.string(),
  run: z.string().nullable(),
})

const CommandsArraySchema = z.array(CommandDataSchema)

// Fields validation schema - allows any object structure
const FieldsSchema = z.record(z.string(), z.any())

/**
 * Validates commands array using zod schema
 */
export function validateCommands(commands: unknown): CommandData[] {
  return CommandsArraySchema.parse(commands)
}

/**
 * Validates fields object using zod schema
 */
export function validateFields(fields: unknown): Record<string, any> {
  return FieldsSchema.parse(fields)
}

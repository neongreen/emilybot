/**
 * Type definitions for JavaScript execution context
 */

import { z } from 'zod/v4';

/**
 * Available to the `.run` attribute of the alias.
 */
export interface AliasRunContext {
  content: string;      // Original entry content
  name: string;         // Entry name
  created_at: string;   // Entry creation timestamp
  user_id: number;      // Entry creator ID
}

/**
 * Available to the `.run` command for direct execution.
 */
export interface RunCommandContext {
  user_id: number;      // User who ran the command
  server_id: number | null;  // Server ID or null for DM
}

export type ExecutionContext = AliasRunContext | RunCommandContext;

export interface ExecutionResult {
  success: boolean;
  output: string;       // Console.log output
  error?: string;       // Error message if failed
}

export type ErrorType = "timeout" | "memory" | "syntax" | "runtime";

export interface JSExecutionError {
  type: ErrorType;
  message: string;
}

// Zod schemas for validation
const AliasRunContextSchema = z.object({
  content: z.string(),
  name: z.string(),
  created_at: z.string(),
  user_id: z.number(),
});

const RunCommandContextSchema = z.object({
  user_id: z.number(),
  server_id: z.number().nullable(),
});

const ExecutionContextSchema = z.union([
  AliasRunContextSchema,
  RunCommandContextSchema,
]);

const ExecutionResultSchema = z.object({
  success: z.boolean(),
  output: z.string(),
  error: z.string().optional(),
});

const JSExecutionErrorSchema = z.object({
  type: z.enum(["timeout", "memory", "syntax", "runtime"]),
  message: z.string(),
});

/**
 * Validates execution context using zod schemas
 */
export function validateContext(context: unknown): ExecutionContext {
  return ExecutionContextSchema.parse(context);
}

/**
 * Validates execution result using zod schema
 */
export function validateExecutionResult(result: unknown): ExecutionResult {
  return ExecutionResultSchema.parse(result);
}

/**
 * Validates JS execution error using zod schema
 */
export function validateJSExecutionError(error: unknown): JSExecutionError {
  return JSExecutionErrorSchema.parse(error);
}
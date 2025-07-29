/**
 * Type definitions for JavaScript execution context
 */

export interface ExecutionContext {
  content: string;      // Original entry content
  name: string;         // Entry name
  created_at: string;   // Entry creation timestamp
  user_id: number;      // Entry creator ID
}

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
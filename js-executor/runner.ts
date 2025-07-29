/**
 * Timeout wrapper for JavaScript execution
 * This script runs the actual executor with a hard timeout
 */

import { JavaScriptExecutor } from "./executor.ts";
import type { ExecutionContext } from "./context.ts";

async function runWithTimeout() {
  const args = Deno.args;
  
  if (args.length !== 2) {
    console.error("Expected two args");
    Deno.exit(1);
  }
  
  const [jsCode, contextJson] = args;
  
  try {
    // Parse context JSON
    const context: ExecutionContext = JSON.parse(contextJson);
    
    // Validate context structure
    if (!context.content || !context.name || !context.created_at || typeof context.user_id !== 'number') {
      console.error("Invalid context structure");
      Deno.exit(1);
    }
    
    // Create a promise that will timeout
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => {
        reject(new Error("TIMEOUT"));
      }, 1000); // 1 second hard timeout
    });
    
    // Create execution promise
    const executionPromise = (async () => {
      const executor = new JavaScriptExecutor(1000);
      return await executor.execute(jsCode, context);
    })();
    
    // Race between execution and timeout
    const result = await Promise.race([executionPromise, timeoutPromise]);
    
    if (result.success) {
      console.log(result.output);
      Deno.exit(0);
    } else {
      console.error(result.error || "Unknown execution error");
      Deno.exit(1);
    }
    
  } catch (error) {
    if (error instanceof Error && error.message === "TIMEOUT") {
      console.error("Execution timed out after 1 second");
      Deno.exit(1);
    }
    
    console.error(`Failed to parse context JSON: ${error instanceof Error ? error.message : String(error)}`);
    Deno.exit(1);
  }
}

if (import.meta.main) {
  await runWithTimeout();
}
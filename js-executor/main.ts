/**
 * Main Deno CLI script for JavaScript execution with hard timeout
 */

import { JavaScriptExecutor } from "./executor.ts";
import type { ExecutionContext } from "./context.ts";

async function main() {
  const args = Deno.args;
  
  if (args.length !== 2) {
    console.error("Usage: deno run --allow-env=QTS_DEBUG js-executor/main.ts <js-code> <context-json>");
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
    
    // Create a hard timeout that will kill the process
    const timeoutId = setTimeout(() => {
      console.error("Execution timed out after 1 second");
      Deno.exit(1);
    }, 1000);
    
    try {
      // Execute JavaScript code
      const executor = new JavaScriptExecutor(1000);
      const result = await executor.execute(jsCode, context);
      
      // Clear timeout since execution completed
      clearTimeout(timeoutId);
      
      if (result.success) {
        console.log(result.output);
        Deno.exit(0);
      } else {
        console.error(result.error || "Unknown execution error");
        Deno.exit(1);
      }
    } catch (error) {
      clearTimeout(timeoutId);
      console.error(`Execution failed: ${error instanceof Error ? error.message : String(error)}`);
      Deno.exit(1);
    }
    
  } catch (error) {
    console.error(`Failed to parse context JSON: ${error instanceof Error ? error.message : String(error)}`);
    Deno.exit(1);
  }
}

if (import.meta.main) {
  await main();
}
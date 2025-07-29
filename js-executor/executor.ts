/**
 * QuickJS wrapper for sandboxed JavaScript execution
 */

import { getQuickJS, QuickJSContext, QuickJSRuntime } from "https://esm.sh/quickjs-emscripten@0.23.0";
import type { ExecutionContext, ExecutionResult, JSExecutionError } from "./context.ts";

export class JavaScriptExecutor {
  private timeout: number;

  constructor(timeout: number = 1000) {
    this.timeout = timeout;
  }

  async execute(code: string, context: ExecutionContext): Promise<ExecutionResult> {
    let runtime: QuickJSRuntime | null = null;
    let vm: QuickJSContext | null = null;
    
    try {
      const QuickJS = await getQuickJS();
      runtime = QuickJS.newRuntime();
      
      // Set memory limit (1MB)
      runtime.setMemoryLimit(1024 * 1024);
      
      vm = runtime.newContext();
      
      // Capture console.log output
      const consoleOutput: string[] = [];
      
      // Inject console.log function
      const consoleLogHandle = vm.newFunction("log", (...args: any[]) => {
        const message = args.map(arg => vm!.dump(arg)).join(" ");
        consoleOutput.push(message);
      });
      
      const consoleHandle = vm.newObject();
      vm.setProp(consoleHandle, "log", consoleLogHandle);
      vm.setProp(vm.global, "console", consoleHandle);
      
      // Inject context object
      const contextHandle = vm.newObject();
      vm.setProp(contextHandle, "content", vm.newString(context.content));
      vm.setProp(contextHandle, "name", vm.newString(context.name));
      vm.setProp(contextHandle, "created_at", vm.newString(context.created_at));
      vm.setProp(contextHandle, "user_id", vm.newNumber(context.user_id));
      vm.setProp(vm.global, "context", contextHandle);
      
      // Dispose handles after setting properties
      consoleLogHandle.dispose();
      consoleHandle.dispose();
      contextHandle.dispose();
      
      // Execute JavaScript code with timeout handling
      try {
        const result = vm.evalCode(code);
        
        if (result.error) {
          let errorStr = "Unknown error";
          try {
            // Try to get the error message property
            const messageProp = vm.getProp(result.error, "message");
            if (messageProp) {
              errorStr = vm.dump(messageProp);
              messageProp.dispose();
            } else {
              errorStr = vm.dump(result.error);
            }
          } catch (e) {
            errorStr = "Error dumping failed";
          }
          result.error.dispose();
          return {
            success: false,
            output: consoleOutput.join("\n"), // Include any console output before error
            error: `runtime: ${errorStr}`
          };
        } else {
          result.value.dispose();
          return {
            success: true,
            output: consoleOutput.join("\n")
          };
        }
      } catch (error) {
        return {
          success: false,
          output: "",
          error: `syntax: ${error instanceof Error ? error.message : String(error)}`
        };
      }
      
    } catch (error) {
      if (error instanceof Error && error.message === "timeout") {
        return {
          success: false,
          output: "",
          error: "Execution timed out after 1 second"
        };
      }
      
      const jsError = error as JSExecutionError;
      return {
        success: false,
        output: "",
        error: `${jsError.type || 'unknown'}: ${jsError.message || String(error)}`
      };
    } finally {
      // Clean up resources
      if (vm) {
        vm.dispose();
      }
      if (runtime) {
        runtime.dispose();
      }
    }
  }
}
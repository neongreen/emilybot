/**
 * Debug logger: logs if LOG_LEVEL is "debug"/"trace" or DEBUG is set.
 */
export function debug(...args: any[]) {
  const logLevel = Deno.env.get("LOG_LEVEL")
  const DEBUG = Deno.env.get("DEBUG")

  if (logLevel === "trace") {
    console.trace(...args)
  } else if (logLevel === "debug" || DEBUG?.toLowerCase() === "true" || DEBUG === "1") {
    console.debug(...args)
  }
}

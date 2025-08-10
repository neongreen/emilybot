import { JSModuleLoadSuccess, SuccessOrFail } from "quickjs-emscripten-core"
import { syncFetch } from "./fetch.ts"
import { debug } from "./logging.ts"
import { parse } from "./parse.ts"

// Check for dynamic import expressions (these would be in function bodies)
// We need to traverse the AST to find ImportExpression nodes
function hasImportExpressions(node: any): boolean {
  if (node.type === "ImportExpression") {
    return true
  }

  // Recursively check child nodes
  for (const key in node) {
    const value = node[key]
    if (value && typeof value === "object") {
      if (Array.isArray(value)) {
        for (const item of value) {
          if (item && typeof item === "object" && hasImportExpressions(item)) {
            return true
          }
        }
      } else if (hasImportExpressions(value)) {
        return true
      }
    }
  }

  return false
}

/**
 * Detects if the code contains any import statements or import expressions
 */
export function hasImports(code: string): boolean {
  try {
    const parseResult = parse(code)

    if (!parseResult.success) {
      // If parsing fails, fall back to regex check for safety
      return /import\s+/.test(code) || /import\s*\(/.test(code) || /export\s+/.test(code)
    }

    const ast = parseResult.ast

    // Check for import declarations
    for (const node of ast.body) {
      if (node.type === "ImportDeclaration") {
        return true
      }
    }

    return hasImportExpressions(ast)
  } catch (e) {
    debug("Error while checking for imports:", e)
    return false
  }
}

/**
 * Process allowed import URLs.
 *
 * Throws an error if the url is not allowed. Only esm.sh urls are currently allowed.
 */
export function processImportPath(url: string): string {
  // Only support esm.sh urls
  const urlObj = new URL(url)
  if (urlObj.hostname !== "esm.sh") {
    throw new Error(`Only esm.sh urls are supported`)
  }
  return urlObj.toString()
}

/**
 * Fetches a module and returns its source code
 *
 * On error, doesn't throw, but returns a "module" evaluating which will throw.
 * This is because I have no idea how to make QuickJS accept an error thrown by a module loader.
 * Maybe it's better now that we have sync fetch.
 */
export function quickJsModuleLoader(moduleName: string): SuccessOrFail<JSModuleLoadSuccess, Error> {
  try {
    const url = processImportPath(moduleName)
    // TODO: for esm links request es2015 or 2020 or idk
    const response = syncFetch(url)
    if (!response.ok) {
      throw new Error(`${response.status}`)
    }
    const text = response.text()
    return { value: text }
  } catch (e: unknown) {
    debug(`Error while loading module ${moduleName}:`, e)
    // Constructing a 'throw' module
    return { value: `throw new Error(${JSON.stringify(e instanceof Error ? e.message : e)})` }
  }
}

/**
 * Resolves a module path based on, uhhh, the base path.
 *
 * If the base path is a local file (e.g. we are in foo.js and we are loading `https://esm.sh/bar`),
 * the base path has to be specified as a file:// url.
 */
export function quickJsModuleNormalizer(baseModuleName: string, requestedName: string): string {
  return (new URL(requestedName, baseModuleName)).toString()
}

import { JSModuleLoadSuccess, SuccessOrFail } from "quickjs-emscripten-core"
import { debug } from "./logging.ts"

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
 * This is because I have no idea how to make QuickJS accept an error thrown by an async module loader.
 */
export async function quickJsModuleLoader(
  moduleName: string,
): Promise<SuccessOrFail<JSModuleLoadSuccess, Error>> {
  try {
    const url = processImportPath(moduleName)
    // TODO: for esm links request es2015 or 2020 or idk
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`)
    }
    const text = await response.text()
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

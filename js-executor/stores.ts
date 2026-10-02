/**
 * Reading alias stores for `this.store`. The file is data/store.json as written by src/emilybot/store.py:
 * `{ "stores": { [aliasId]: { server_id, version, data } } }`, with `server_id` a string.
 */

import type { StoreLoad } from "./types.ts"

/**
 * A loader that reads `path` on first use and serves the stores of server `serverId`.
 *
 * Python may be saving the file at the same time. A missing or empty file means no stores yet. A file that does not
 * parse (for example caught half-written by an in-place save) makes the run busy: it ends and saves nothing, and the
 * user is asked to try again. A version that changes after this read is caught when the run's writes are committed.
 */
export function storeLoaderFromFile(path: string, serverId: string): (aliasId: string) => StoreLoad {
  let stores: Record<string, { server_id: unknown; version: number; data: Record<string, unknown> }> | undefined
  return (aliasId) => {
    if (stores === undefined) {
      let text = ""
      try {
        text = Deno.readTextFileSync(path)
      } catch (error) {
        if (!(error instanceof Deno.errors.NotFound)) return { busy: true }
      }
      try {
        stores = text.trim() ? JSON.parse(text).stores : {}
        if (typeof stores !== "object" || stores === null) throw new Error("no stores object")
      } catch {
        stores = undefined
        return { busy: true }
      }
    }
    const rec = Object.hasOwn(stores, aliasId) ? stores[aliasId] : undefined
    if (!rec || String(rec.server_id) !== serverId) return { version: 0, data: {} }
    return { version: rec.version, data: rec.data }
  }
}

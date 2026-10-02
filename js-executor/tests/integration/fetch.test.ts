import { assertEquals, assertThrows } from "@std/assert"
import { syncFetch } from "../../fetch.ts"

// syncFetch blocks this thread, so the fixture server runs in a worker.
const SERVER = `
  const big = new Uint8Array(64 * 1024)
  const server = Deno.serve({ hostname: "127.0.0.1", port: 0, onListen: () => {} }, (req) => {
    const path = new URL(req.url).pathname
    if (path === "/ok") return new Response("hello")
    if (path === "/missing") return new Response("nope", { status: 404 })
    if (path === "/stall") return new Promise(() => {})
    if (path === "/stall-body") {
      return new Response(new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode("partial")) } }))
    }
    if (path === "/big") {
      let sent = 0
      return new Response(new ReadableStream({ pull(c) { if (sent++ < 32) c.enqueue(big); else c.close() } }))
    }
    return new Response("?", { status: 400 })
  })
  postMessage(server.addr.port)
`

async function withServer(fn: (base: string) => void) {
  const url = URL.createObjectURL(new Blob([SERVER], { type: "text/javascript" }))
  const worker = new Worker(url, { type: "module" })
  try {
    const port = await new Promise<number>((resolve) => worker.onmessage = (e) => resolve(e.data))
    fn(`http://127.0.0.1:${port}`)
  } finally {
    worker.terminate()
    URL.revokeObjectURL(url)
  }
}

Deno.test("syncFetch: ok, non-200, stalled, and oversized responses", async () => {
  await withServer((base) => {
    const ok = syncFetch(`${base}/ok`)
    assertEquals([ok.status, ok.ok, ok.text()], [200, true, "hello"])

    const missing = syncFetch(`${base}/missing`)
    assertEquals([missing.status, missing.ok], [404, false])

    const start = performance.now()
    assertThrows(() => syncFetch(`${base}/stall`, { timeoutMs: 300 }), Error, "timed out")
    assertThrows(() => syncFetch(`${base}/stall-body`, { timeoutMs: 300 }), Error, "timed out")
    const elapsed = performance.now() - start
    if (elapsed > 2000) throw new Error(`timeouts took ${elapsed} ms`)

    // 2 MiB body against a 1 MiB cap
    assertThrows(() => syncFetch(`${base}/big`, { maxBodyBytes: 1024 * 1024 }), Error, "larger than")
    assertEquals(syncFetch(`${base}/big`, { maxBodyBytes: 4 * 1024 * 1024 }).body.length, 2 * 1024 * 1024)
  })
})

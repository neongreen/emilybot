type SyncResponse = {
  status: number
  ok: boolean
  body: Uint8Array
  text(): string
  json(): unknown
}

// ctrl[0] states
const PENDING = 0
const DONE = 1
const FAILED = -1
const TOO_LARGE = -2

const WORKER_SOURCE = `
  onmessage = async (e) => {
    const { url, init, ctrlSab, bodySab } = e.data
    const ctrl = new Int32Array(ctrlSab)
    const body = new Uint8Array(bodySab)
    const finish = (state) => {
      Atomics.store(ctrl, 0, state)
      Atomics.notify(ctrl, 0)
      close()
    }
    try {
      const res = await fetch(url, init)
      Atomics.store(ctrl, 1, res.status | 0)
      Atomics.store(ctrl, 2, res.ok ? 1 : 0)
      let n = 0
      if (res.body) {
        // Read incrementally and stop as soon as the body outgrows the buffer
        for await (const chunk of res.body) {
          if (n + chunk.byteLength > body.byteLength) {
            await res.body.cancel().catch(() => {})
            return finish(${TOO_LARGE})
          }
          body.set(chunk, n)
          n += chunk.byteLength
        }
      }
      Atomics.store(ctrl, 3, n)
      finish(${DONE})
    } catch (_) {
      finish(${FAILED})
    }
  }
`

/**
 * A synchronous fetch that blocks the main thread until the response body is read or `timeoutMs` passes.
 *
 * We can't use async fetching in sync QuickJS, and the async build of QuickJS is slow.
 * Throws on network failure, timeout, or a body larger than `maxBodyBytes`; non-2xx statuses are returned.
 */
export function syncFetch(
  url: string,
  init: { method?: string; headers?: Record<string, string>; maxBodyBytes?: number; timeoutMs?: number } = {},
): SyncResponse {
  const max = init.maxBodyBytes ?? (8 * 1024 * 1024) // 8 MiB cap
  const timeoutMs = init.timeoutMs ?? 5000
  const ctrlSab = new SharedArrayBuffer(16) // [state, status, ok, len]
  const ctrl = new Int32Array(ctrlSab)
  const bodySab = new SharedArrayBuffer(max)

  const workerUrl = URL.createObjectURL(new Blob([WORKER_SOURCE], { type: "text/javascript" }))
  let worker: Worker | undefined
  try {
    worker = new Worker(workerUrl, { type: "module" })
    const headers = init.headers ? { ...init.headers } : undefined
    worker.postMessage({ url, init: { method: init.method, headers }, ctrlSab, bodySab })

    const waited = Atomics.wait(ctrl, 0, PENDING, Math.max(0, timeoutMs))
    const state = Atomics.load(ctrl, 0)
    if (waited === "timed-out" && state === PENDING) {
      throw new Error(`Fetching ${url} timed out after ${(timeoutMs / 1000).toFixed(1)}s`)
    }
    if (state === TOO_LARGE) throw new Error(`Fetching ${url} failed: response is larger than ${max} bytes`)
    if (state !== DONE) throw new Error(`Fetching ${url} failed`)

    const len = Atomics.load(ctrl, 3)
    return {
      status: Atomics.load(ctrl, 1),
      ok: Atomics.load(ctrl, 2) === 1,
      body: new Uint8Array(bodySab.slice(0, len)),
      text() {
        return new TextDecoder().decode(this.body)
      },
      json() {
        return JSON.parse(this.text())
      },
    }
  } finally {
    worker?.terminate()
    URL.revokeObjectURL(workerUrl)
  }
}

// demo
if (import.meta.main) {
  const r = syncFetch("https://httpbin.org/get")
  console.log("status", r.status)
  console.log(r.text().slice(0, 120))
}

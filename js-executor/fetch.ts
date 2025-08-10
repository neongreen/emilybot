// deno run --allow-net sync_fetch_worker.ts

type SyncResponse = {
  status: number
  ok: boolean
  body: Uint8Array
  text(): string
  json(): unknown
}
/**
 * A synchronous fetch that blocks the main thread.
 *
 * We can't use async fetching in sync QuickJS, and the async build of QuickJS is slow.
 */
export function syncFetch(
  url: string,
  init: { method?: string; headers?: Record<string, string>; maxBodyBytes?: number } = {},
): SyncResponse {
  const max = init.maxBodyBytes ?? (8 * 1024 * 1024) // 8 MiB cap
  const ctrlSab = new SharedArrayBuffer(16) // [done, status, ok, len]
  const ctrl = new Int32Array(ctrlSab)
  const bodySab = new SharedArrayBuffer(max)
  const body = new Uint8Array(bodySab)

  const workerSrc = `
    onmessage = async (e) => {
      const { url, init, ctrlSab, bodySab } = e.data
      const ctrl = new Int32Array(ctrlSab)
      const body = new Uint8Array(bodySab)
      try {
        const res = await fetch(url, init)
        const buf = new Uint8Array(await res.arrayBuffer())
        const n = Math.min(buf.byteLength, body.byteLength)
        body.set(buf.subarray(0, n))
        Atomics.store(ctrl, 1, res.status|0)
        Atomics.store(ctrl, 2, res.ok ? 1 : 0)
        Atomics.store(ctrl, 3, n|0)
        Atomics.store(ctrl, 0, 1)     // done
        Atomics.notify(ctrl, 0)
      } catch (_) {
        Atomics.store(ctrl, 1, 0)
        Atomics.store(ctrl, 2, 0)
        Atomics.store(ctrl, 3, 0)
        Atomics.store(ctrl, 0, -1)    // error
        Atomics.notify(ctrl, 0)
      }
      close()
    }
  `
  const blob = new Blob([workerSrc], { type: "text/javascript" })
  const worker = new Worker(URL.createObjectURL(blob), { type: "module" })

  let headers: Record<string, string> | undefined
  if (init.headers) {
    headers = { ...init.headers }
  }

  worker.postMessage({ url, init: { method: init.method, headers }, ctrlSab, bodySab })

  // block until worker signals
  Atomics.wait(ctrl, 0, 0)

  try {
    worker.terminate()
  } catch {
    // ignore
  }

  const done = Atomics.load(ctrl, 0)
  if (done < 0) throw new Error("syncFetch failed")
  const len = Atomics.load(ctrl, 3)
  const status = Atomics.load(ctrl, 1)
  const ok = Atomics.load(ctrl, 2) === 1
  const data = new Uint8Array(body.buffer.slice(0, len))

  const resp: SyncResponse = {
    status,
    ok,
    body: data,
    text() {
      return new TextDecoder().decode(this.body)
    },
    json() {
      return JSON.parse(this.text())
    },
  }
  return resp
}

// demo
if (import.meta.main) {
  const r = syncFetch("https://httpbin.org/get")
  console.log("status", r.status)
  console.log(r.text().slice(0, 120))
}

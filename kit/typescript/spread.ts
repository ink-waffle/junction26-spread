/** The client for the Spread API (HANDBOOK.md, API.md), on Bun or on Node 22.18 or later, with
 * nothing else. Answers are plain objects in the shapes of types.ts. */
import type {
  Action, ActionResult, Advance, Advanced, DeskEvent, DeskSnapshot, DriverProfile, Final,
  PracticeBoard, Reveal, Score, WorldMap, WorldSummary,
} from "./types.ts"

export type * from "./types.ts"

const ACTIONS_PER_CALL = 50

/** A request that failed. `status` is the HTTP status, 0 when the server did not
 * answer; `field` names the part of the body that did not parse. */
export class SpreadError extends Error {
  readonly status: number
  readonly field: string | undefined
  constructor(status: number, error: string, field?: string) {
    const detail = [...(status ? [`HTTP ${status}`] : []), ...(field ? [`field ${field}`] : [])].join(", ")
    super(detail ? `${error} (${detail})` : error)
    this.status = status
    this.field = field
  }
}

/** The server did not answer: it is down or restarting, or SPREAD_URL is wrong. */
export class Unreachable extends SpreadError {}

/** While the server restarts, the proxy in front of it answers 502, 503 or 504 for it. */
const restarting = (status: number): boolean => status >= 502 && status <= 504

/** Stops a body or query that holds a number with a fraction. Every number that the API takes is a
 * whole number: minutes, cents, levels and legs. The server refuses others with 400. */
function checkWhole(value: unknown, field = ""): void {
  if (typeof value === "number" && !Number.isInteger(value)) throw new SpreadError(0, `${value} is not a whole number. Minutes and cents are whole numbers: round them before you send`, field)
  if (typeof value !== "object" || value === null) return
  for (const [key, item] of Object.entries(value)) checkWhole(item, Array.isArray(value) ? `${field}[${key}]` : field ? `${field}.${key}` : key)
}

/** The error for an answer other than 2xx, with what to do where the server's text does not say it. */
function failure(status: number, body: string, path: string): SpreadError {
  if (restarting(status)) return new Unreachable(0, `The server is restarting (HTTP ${status})`)
  let answer: { error?: string; field?: string }
  try {
    answer = JSON.parse(body)
  } catch {
    answer = { error: body.trim().slice(0, 200) || "no message" }
  }
  let error = answer.error ?? "no message"
  if (status === 401) error = "The server does not accept this key. Set SPREAD_KEY to your team key"
  // Only where the server says to delete a world: a full set of practice slots, or a ranking run
  // that has not ended. A team that has played a ranking round's worlds waits for the next round.
  else if (status === 409 && (path === "/v1/worlds" || path.endsWith("/fork")) && error.includes("delete")) {
    error += ". client.worlds() lists them; client.world(worldId).delete() deletes one"
  }
  return new SpreadError(status, error, answer.field)
}

/** The client's copy of one of the server's request buckets, from the RateLimit headers of
 * the last answer. The client waits until the bucket holds the tokens for a request, so a system
 * that runs at the limit gets almost no 429 answers. */
class Bucket {
  readonly name: string
  readonly perSecond: number
  tokens: number
  at = performance.now()

  constructor(name: string, headers: Headers) {
    this.name = name
    this.perSecond = Number(headers.get("ratelimit-limit"))
    const nextToken = Number(headers.get("ratelimit-reset")) / 1000
    // The headers give whole tokens; the wait for the next token gives the fraction.
    this.tokens = Number(headers.get("ratelimit-remaining")) + (nextToken > 0 ? 1 - nextToken * this.perSecond : 0)
  }

  /** Takes the tokens for a request that carries `actions` actions. Returns the milliseconds to
   * wait until the bucket holds them. A final world takes one token for each action. */
  take(actions: number): number {
    const cost = this.name === "final-actions" ? Math.max(1, actions) : 1
    const now = performance.now()
    const tokens = this.tokens + ((now - this.at) / 1000) * this.perSecond
    const delayMs = Math.max(0, ((cost - tokens) * 1000) / this.perSecond)
    this.tokens = tokens + (delayMs / 1000) * this.perSecond - cost
    this.at = now + delayMs
    return delayMs
  }
}

/** One team key on one server. `url` and `key` default to the SPREAD_URL and SPREAD_KEY variables. */
export class Client {
  readonly url: string
  readonly key: string
  readonly #buckets = new Map<string, Bucket>() // bucket name -> the client's copy
  readonly #bucketOf = new Map<string, string>() // "METHOD /path" -> the bucket that the server charges

  constructor(options: { url?: string; key?: string } = {}) {
    this.url = (options.url ?? process.env.SPREAD_URL ?? "http://127.0.0.1:8080").replace(/\/$/, "")
    this.key = options.key ?? process.env.SPREAD_KEY ?? ""
    if (!/^https?:\/\/[^/]/.test(this.url)) {
      throw new SpreadError(0, `SPREAD_URL is "${this.url}". Set it to the server address, for example http://127.0.0.1:8080`)
    }
    if (!this.key) throw new SpreadError(0, "SPREAD_KEY is not set. Set it to your team key")
  }

  worlds(): Promise<WorldSummary[]> {
    return this.call("GET", "/v1/worlds")
  }

  /** A new practice world. It stands still until you call `advance`. With `{ board: true }`,
   * your next ranking run at the level, on a seed that the server chooses. */
  async create(level: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 = 8, options: { seed?: string; board?: boolean } = {}): Promise<World> {
    const { worldId } = await this.call<{ worldId: string }>("POST", "/v1/worlds", { level, ...options })
    return new World(this, worldId)
  }

  /** The practice rankings of a level: the current ranking round and the previous one. */
  board(level: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 = 8): Promise<PracticeBoard> {
    return this.call("GET", `/v1/leaderboards/practice?level=${level}`)
  }

  world(worldId: string): World {
    return new World(this, worldId)
  }

  /** The places, and the road km and minutes between every pair. */
  map(): Promise<WorldMap> {
    return this.call("GET", "/v1/map")
  }

  /** Your copy of the final world: `worldId`, `startsAt` (wall clock) and `now`. 404 before one is scheduled. */
  final(): Promise<Final> {
    return this.call("GET", "/v1/final")
  }

  /** One request. Waits until the server's bucket for the request has the tokens for it, and
   * waits out 429 answers for the time the server names. `actions` is the number of actions
   * that the request carries. */
  async call<T>(method: "GET" | "POST" | "DELETE", path: string, body?: unknown, actions = 0): Promise<T> {
    const route = `${method} ${path.split("?")[0]}`
    checkWhole(body)
    while (true) {
      const waitMs = this.#buckets.get(this.#bucketOf.get(route) ?? "")?.take(actions) ?? 0
      // Timers drop fractions of a millisecond and can fire up to one early; an early request gets 429.
      if (waitMs > 0) await sleep(Math.ceil(waitMs) + 1)
      let response: Response
      // A request lost on the network never gets an answer. After 20 seconds without the start of
      // one, the server counts as unreachable, and a final desk rebuilds and goes on.
      const answer = new AbortController()
      const timer = setTimeout(() => answer.abort(new Error("no answer in 20 seconds")), 20_000)
      try {
        response = await fetch(this.url + path, {
          method,
          headers: { authorization: `Bearer ${this.key}`, "content-type": "application/json" },
          ...(body === undefined ? {} : { body: JSON.stringify(body) }),
          signal: answer.signal,
        })
      } catch (error) {
        const reason = ((error as { cause?: Error }).cause?.message ?? (error as Error).message).replace(/[.?!]+$/, "")
        throw new Unreachable(0, `Cannot reach ${this.url}: ${reason}. Check SPREAD_URL, and that the server runs`)
      } finally {
        clearTimeout(timer)
      }
      const policy = response.headers.get("ratelimit-policy")
      if (policy) {
        const charged = policy.split(";")[0]!.replaceAll('"', "")
        this.#bucketOf.set(route, charged)
        this.#buckets.set(charged, new Bucket(charged, response.headers))
      }
      if (response.status === 429) {
        await sleep(Number(response.headers.get("retry-after") ?? 100))
        continue
      }
      // An answer that breaks off after its first bytes comes from a server that stopped.
      const text = await response.text().catch((error: unknown) => {
        throw new Unreachable(0, `The answer from ${this.url} broke off: ${(error as Error).message}`)
      })
      if (!response.ok) throw failure(response.status, text, path.split("?")[0]!)
      return (text ? JSON.parse(text) : undefined) as T
    }
  }
}

/** One world of the team: a practice world, a fork, or the team's copy of the final. */
export class World {
  readonly client: Client
  readonly id: string
  #lastSeq = -1

  constructor(client: Client, id: string) {
    this.client = client
    this.id = id
  }

  #path(tail = "", query: Record<string, string | number | undefined> = {}): string {
    checkWhole(query)
    const pairs = Object.entries(query).filter(([, value]) => value !== undefined) as [string, string][]
    return `/v1/worlds/${this.id}${tail}${pairs.length ? `?${new URLSearchParams(pairs)}` : ""}`
  }

  snapshot(): Promise<DeskSnapshot> {
    return this.client.call("GET", this.#path())
  }

  /** Sends actions in batches of 50. Results come back in the order of the actions. */
  async act(actions: readonly Action[]): Promise<ActionResult[]> {
    const results: ActionResult[] = []
    for (let i = 0; i < actions.length; i += ACTIONS_PER_CALL) {
      const batch = actions.slice(i, i + ACTIONS_PER_CALL)
      results.push(...(await this.client.call<ActionResult[]>("POST", this.#path("/actions"), batch, batch.length)))
    }
    return results
  }

  /** Practice worlds only. Applies `actions` at the current minute, then moves the
   * clock `{ to }` a minute, `{ by }` minutes, or `{ untilEvent, max }` to the first
   * event of one of the kinds, but not past `max`. One request does both. Returns the
   * minute reached, every event since the last advance without repeats, and the
   * `results` of the actions in their order. */
  async advance({ actions = [], ...target }: Advance): Promise<Required<Advanced>> {
    // A request carries at most 50 actions. The ones before the last 50 go first, in batches.
    const results = await this.act(actions.slice(0, -ACTIONS_PER_CALL))
    const last = actions.slice(-ACTIONS_PER_CALL)
    const step = await this.client.call<Advanced>("POST", this.#path("/advance"), last.length > 0 ? { ...target, actions: last } : target)
    const events = step.events.filter((event) => event.seq > this.#lastSeq)
    this.#lastSeq = events.at(-1)?.seq ?? this.#lastSeq
    return { now: step.now, events, results: [...results, ...(step.results ?? [])] }
  }

  /** Events with a sequence number above `after`, oldest first. */
  events(after = -1, limit?: number): Promise<DeskEvent[]> {
    return this.client.call("GET", this.#path("/events", { after, limit }))
  }

  /** Events as they happen, over the WebSocket. With `after`, first every event
   * above that sequence number. Reconnects by itself and misses nothing. With
   * `idleMs`, yields null after that long without an event, so a loop can check the clock. */
  async *stream(options: { after?: number; idleMs?: number } = {}): AsyncGenerator<DeskEvent | null> {
    let last = options.after
    for (let failures = 0; failures < 60; failures++) {
      // A WebSocket cannot report an HTTP error, so one read first checks the key and the world.
      try {
        await this.events(last ?? -1, 1)
      } catch (error) {
        if (!(error instanceof SpreadError) || error.status !== 0) throw error
        await sleep(1000)
        continue
      }
      const queue: (DeskEvent | { closed: number })[] = []
      let wake = () => {}
      const url = this.client.url.replace(/^http/, "ws") + this.#path("/stream", { after: last })
      // Bun and Node accept headers here; a browser does not, so run your system outside one.
      const socket = new WebSocket(url, { headers: { authorization: `Bearer ${this.client.key}` } } as unknown as string[])
      socket.onmessage = (message) => (queue.push(JSON.parse(String(message.data))), wake())
      socket.onclose = (close) => (queue.push({ closed: close.code }), wake())
      try {
        while (true) {
          if (queue.length === 0) {
            await new Promise<void>((done) => {
              wake = done
              if (options.idleMs !== undefined) setTimeout(done, options.idleMs)
            })
            if (queue.length === 0) yield null
            continue
          }
          const item = queue.shift()!
          if ("closed" in item) {
            if (item.closed === 1000) return // the world was deleted
            break
          }
          failures = 0
          last = item.seq
          yield item
        }
      } finally {
        socket.close()
      }
      await sleep(1000)
    }
    throw new Unreachable(0, `The stream of world ${this.id} failed 60 times in a row`)
  }

  /** Every driver's public profile. It can be up to 5 seconds old while the world moves. */
  roster(): Promise<DriverProfile[]> {
    return this.client.call("GET", this.#path("/drivers"))
  }

  /** A copy at the same minute with the same future draws. Practice worlds only. */
  async fork(): Promise<World> {
    const { worldId } = await this.client.call<{ worldId: string }>("POST", this.#path("/fork"))
    return new World(this.client, worldId)
  }

  score(): Promise<Score> {
    return this.client.call("GET", this.#path("/score"))
  }

  /** After the world has ended: your quotes and their outcomes, the truth of the cars you won, and the views of your gigs. */
  reveal(): Promise<Reveal> {
    return this.client.call("GET", this.#path("/reveal"))
  }

  /** Deletes a practice world and frees its slot. */
  delete(): Promise<void> {
    return this.client.call("DELETE", this.#path())
  }
}

const sleep = (ms: number) => new Promise((done) => setTimeout(done, ms))

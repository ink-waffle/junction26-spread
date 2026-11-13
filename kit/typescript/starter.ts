/** The starter: a whole dispatch system that you can read in five minutes, then change. HANDBOOK.md says
 * what it does and how to run it: `bun starter.ts`, or `node starter.ts` on Node 22.18 or later. */
import { parseArgs } from "node:util"
import { Client, SpreadError, Unreachable, World } from "./spread.ts"
import type { Action, ActionResult, DeskEvent, DeskEventKind, DeskSnapshot, FeeStep, Note, Order, PostAction, PriceRequest, Score, StopRef, TimeWindow } from "./spread.ts"

const HOUR = 60
const DAY = 24 * HOUR
const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
/** The events that need an answer. Views and account lines arrive with the next event that needs an answer. */
const WAKE_ON: DeskEventKind[] = ["price_request", "order_won", "order_changed", "order_cancelled", "visit_failed", "gig_expired", "deadline_close"]

/** How to post a leg again after a failed visit. */
type Retry = { pickupFrom: number; manualLicence: boolean; plates: boolean }
const FIRST_TRY: Retry = { pickupFrom: 0, manualLicence: false, plates: false }

/** What the starter remembers, and its answer to each event. The answers wait in the outbox
 * until the starter sends them, and the world applies them at the current minute. */
class Desk {
  readonly world: World
  readonly level: number
  now: number
  readonly outbox: Action[] = [] // the actions decided since the starter last sent
  readonly requests = new Map<string, PriceRequest>()
  readonly orders = new Map<string, Order>() // the orders won and not cancelled
  readonly legGigs = new Map<string, Map<number, string>>() // order id -> leg -> the gig that carries the leg
  readonly booked = new Set<string>() // the gigs that a driver holds now
  readonly posts = new Map<string, PostAction>() // gig id -> the post that made it
  readonly urgent = new Set<string>() // the orders whose deadline warning has come

  constructor(world: World, level: number, now: number) {
    this.world = world
    this.level = level
    this.now = now
  }

  /** Rebuilds what it knows from the world, so a starter that stopped keeps its orders. Then answers
   * what it missed: open requests, orders without a gig, failed visits without a new gig, and the
   * deadline warnings, so the orders that had one keep their steep fees. */
  async rejoin(snapshot: DeskSnapshot, history: DeskEvent[]): Promise<void> {
    const posted = Map.groupBy(snapshot.gigs, (gig) => gig.stops[0]!.orderId) // order id -> its gigs, oldest first
    for (const gig of snapshot.gigs) if (["booked", "working", "done"].includes(gig.status)) this.booked.add(gig.id)
    for (const gig of snapshot.gigs) if (["open", "booked", "working"].includes(gig.status)) this.carry({ type: "post", stops: gig.stops, audience: gig.audience, schedule: gig.schedule }, gig.id)
    for (const event of history) if (event.kind === "price_request") this.requests.set(event.request.id, event.request)
    for (const event of history) if (event.kind === "deadline_close") this.urgent.add(event.orderId)
    for (const order of snapshot.orders) if (this.requests.has(order.id) && order.status !== "cancelled") this.orders.set(order.id, order)
    for (const order of this.orders.values()) if (order.status === "waiting" && this.gigsOf(order.id).length === 0) await this.post(order, undelivered(order))
    for (const event of history) {
      const order = "orderId" in event ? this.orders.get(event.orderId) : undefined
      if (!order) continue
      if (event.kind === "visit_failed" && order.deliveredAt[event.leg] === null) {
        const later = (posted.get(order.id) ?? []).filter((gig) => gig.postedAt >= event.at && gig.id !== event.gigId)
        if (!later.some((gig) => gig.stops.some((stop) => stop.leg === event.leg))) await this.retry(order.id, event.leg, event.reason)
      }
    }
    for (const request of snapshot.openRequests) this.quote(request)
  }

  async handle(event: DeskEvent): Promise<void> {
    if (event.kind === "price_request") this.quote(event.request)
    else if (event.kind === "order_won") await this.win(event.order)
    else if (event.kind === "order_changed") await this.change(event.order)
    // The world has stopped a cancelled order's car and told each of its gigs what happens.
    else if (event.kind === "order_cancelled") for (const books of [this.orders, this.legGigs]) books.delete(event.orderId)
    else if (event.kind === "visit_failed") await this.retry(event.orderId, event.leg, event.reason)
    else if (event.kind === "gig_expired") this.repost(event.gigId)
    // It comes again when a driver drops the car after the first warning.
    else if (event.kind === "deadline_close") await this.raise(event.orderId)
    else if (event.kind === "gig_booked") this.booked.add(event.gigId)
    // After a no-show the gig is open again, as after a drop. A late driver still comes.
    else if (event.kind === "gig_dropped" || event.kind === "no_show") this.booked.delete(event.gigId)
    else if (event.kind === "delivered") this.delivered(event.orderId, event.leg, event.at)
  }

  delivered(orderId: string, leg: number, at: number): void {
    this.legGigs.get(orderId)?.delete(leg)
    const order = this.orders.get(orderId)
    if (order) order.deliveredAt[leg] = at
  }

  quote(request: PriceRequest): void {
    this.requests.set(request.id, request)
    const first = request.options[0]!
    this.outbox.push({ type: "quote", requestId: request.id, prices: { [first.kind]: first.listPriceCents } })
  }

  async win(order: Order): Promise<void> {
    if (!this.requests.has(order.id) || this.orders.has(order.id)) return // rejoin can know it already
    this.orders.set(order.id, order)
    await this.post(order, undelivered(order))
  }

  async change(order: Order): Promise<void> {
    if (!this.orders.has(order.id)) return
    this.orders.set(order.id, order)
    if (await this.withdraw(order.id)) await this.post(order, undelivered(order))
  }

  /** Posts a gig again when one of its windows ended before a driver booked it. */
  repost(gigId: string): void {
    const action = this.posts.get(gigId)
    // A gig the starter has already taken off and posted again, after a change of plan, needs nothing.
    if (!action || !action.stops.some(({ orderId, leg }) => this.legGigs.get(orderId)?.get(leg) === gigId)) return
    for (const { orderId, leg } of action.stops) this.legGigs.get(orderId)?.delete(leg)
    const order = this.orders.get(action.stops[0]!.orderId)
    if (!order) return
    // One of its windows has ended, perhaps at a site's closing time before the window's own end: post without its own stop windows.
    this.outbox.push({ ...action, stops: withoutWindows(action.stops, Infinity), schedule: this.feesFor(order, pickups(action)) })
  }

  /** From the order's deadline warning on, its gigs that no driver holds go at the steep fees. */
  async raise(orderId: string): Promise<void> {
    const order = this.orders.get(orderId)
    if (!order) return
    this.urgent.add(orderId)
    await this.sendPostOf(orderId)
    for (const gigId of this.gigsOf(orderId)) {
      if (!this.booked.has(gigId)) this.outbox.push({ type: "reprice", gigId, schedule: this.feesFor(order, pickups(this.posts.get(gigId)!)) })
    }
  }

  /** The fees for some of the order's cars from now: rising, or steep once its deadline warning has come. */
  feesFor(order: Order, cars: number): FeeStep[] {
    const fee = (this.requests.get(order.id)!.referenceFeeCents * cars) / order.legs.length
    return this.urgent.has(order.id) ? steep(this.now, fee, this.level) : rising(this.now, fee, this.level)
  }

  async retry(orderId: string, leg: number, reason: string): Promise<void> {
    const order = this.orders.get(orderId)
    if (!order) return
    this.legGigs.get(orderId)?.delete(leg) // the world has taken the car out of the failed gig
    const carNotThere = reason === "not_ready" || reason === "closed"
    const pickupFrom = carNotThere ? retryFrom(order, this.requests.get(orderId)!, leg, this.now) : 0
    await this.post(order, [leg], { pickupFrom, manualLicence: reason === "licence", plates: reason === "no_plates" })
  }

  async post(order: Order, legs: number[], retry = FIRST_TRY): Promise<void> {
    // A premium car needs an experienced driver: the fine is €150 a car.
    const audience = { experienced: order.legs.some((leg) => leg.car.premium), manualLicence: retry.manualLicence }
    const stops = withoutWindows(stopsFor(order, legs, this.requests.get(order.id)!.note, retry), this.now)
    this.outbox.push({ type: "post", stops, audience, schedule: this.feesFor(order, legs.length) })
    if (legs.length === 1) return
    // A trade-in over the 12-hour limit for a gig with two cars goes as one gig per car.
    await this.send()
    if (this.gigsOf(order.id).length === 0) for (const leg of legs) await this.post(order, [leg], retry)
  }

  /** The gigs that carry the order's undelivered legs: one, or one for each leg of a split trade-in. */
  gigsOf(orderId: string): string[] {
    return [...new Set(this.legGigs.get(orderId)?.values())]
  }

  /** Remembers a gig that the world accepted: the post that made it, and the legs it carries. */
  carry(action: PostAction, gigId: string): void {
    for (const { orderId, leg } of action.stops) this.legGigs.set(orderId, (this.legGigs.get(orderId) ?? new Map()).set(leg, gigId))
    this.posts.set(gigId, action)
  }

  /** Takes an order's gigs out of the drivers' app. False, and nothing withdrawn, when a driver holds one of them. */
  async withdraw(orderId: string): Promise<boolean> {
    await this.sendPostOf(orderId)
    const gigs = this.gigsOf(orderId)
    if (gigs.some((gigId) => this.booked.has(gigId))) return false
    this.legGigs.delete(orderId)
    for (const gigId of gigs) this.outbox.push({ type: "withdraw", gigId })
    return true
  }

  /** A post of the order still in the outbox goes to the world now, so the starter knows its gig. Each gig carries one order. */
  async sendPostOf(orderId: string): Promise<void> {
    if (this.outbox.some((action) => action.type === "post" && action.stops[0]!.orderId === orderId)) await this.send()
  }

  /** Sends the outbox now. In practice, the outbox goes with the next advance instead. */
  async send(): Promise<void> {
    const actions = this.outbox.splice(0)
    if (actions.length > 0) this.readResults(actions, await this.world.act(actions))
  }

  readResults(actions: Action[], results: ActionResult[]): void {
    actions.forEach((action, i) => {
      if (action.type === "post" && results[i]?.ok) this.carry(action, results[i]!.id)
    })
  }
}

/** When to try a car again after a visit found it not ready or the site closed: two hours on, or,
 * when the dealer moved the deadline for a car that is late, when the car should be ready by the
 * same delay. */
function retryFrom(order: Order, request: PriceRequest, leg: number, now: number): number {
  const promised = request.options.find((option) => option.kind === order.option)?.deadline ?? order.deadline
  const delay = Math.max(0, order.deadline - promised)
  return Math.max(now + 2 * HOUR, order.legs[leg]!.pickup.window.from + delay)
}

const undelivered = (order: Order): number[] => order.legs.map((_, leg) => leg).filter((leg) => order.deliveredAt[leg] === null)

/** The cars a post carries. */
const pickups = (action: PostAction): number => action.stops.filter((stop) => stop.kind === "pickup").length

/** Leaves out the stop windows that end before `before`, so the world's window applies: once the order's
 * window has ended, it runs to the end of the world. */
const withoutWindows = (stops: StopRef[], before: number): StopRef[] =>
  stops.map((stop) => (stop.window && stop.window.to < before ? { ...stop, window: undefined } : stop))

/** The fee at once, then 10% of it more every hour: six steps, up to 1.5 times. Level 1 takes one fee only. */
const rising = (now: number, fee: number, level: number): FeeStep[] =>
  (level === 1 ? [0] : [0, 1, 2, 3, 4, 5]).map((k) => ({ at: now + k * HOUR, feeCents: Math.max(1, Math.round(fee * (1 + k / 10))) }))

/** 1.5 times the fee at once, then a quarter of it more every half hour, up to 2.5 times. Level 1 takes one fee only. */
const steep = (now: number, fee: number, level: number): FeeStep[] =>
  (level === 1 ? [0] : [0, 1, 2, 3, 4]).map((k) => ({ at: now + k * 30, feeCents: Math.max(1, Math.round(fee * (1.5 + k / 4))) }))

/** A pickup and a delivery for each leg. An electric car under 30% gets a charging stop.
 * A stop has its own window only when the note or the retry makes it narrower. Without
 * one, the world plans the pickup in the order's window and the delivery by the deadline. */
function stopsFor(order: Order, legs: number[], note: Note | null, retry: Retry): StopRef[] {
  return legs.flatMap((leg): StopRef[] => {
    const { car, pickup, delivery } = order.legs[leg]!
    const noted = windowFromNote(note, pickup.window, "pickup")
    const start = Math.max(noted.from, retry.pickupFrom)
    const pickupWindow = { from: start, to: Math.max(noted.to, start) }
    const deliveryBase = { from: delivery.window.from, to: Math.max(delivery.window.from, order.deadline) }
    const deliveryWindow = windowFromNote(note, deliveryBase, "delivery")
    const lowBattery = car.electric && car.chargePercent !== null && car.chargePercent < 30
    const first: StopRef = { orderId: order.id, leg, kind: "pickup", withPlates: retry.plates, withCharging: lowBattery }
    const second: StopRef = { orderId: order.id, leg, kind: "delivery" }
    return [narrower(first, pickupWindow, pickup.window), narrower(second, deliveryWindow, deliveryBase)]
  })
}

const narrower = (stop: StopRef, window: TimeWindow, base: TimeWindow): StopRef =>
  window.from > base.from || window.to < base.to ? { ...stop, window } : stop

/** "Not before", "at the earliest" and a ready time all mean from then on; read them before BEFORE. */
const AFTER = /jälkeen|alkaen|aikaisintaan|\bafter\b|\bfrom\b|earliest|not before|ei ennen|valmis|\bready\b|efter|tidigast|inte före|klar/
const BEFORE = /ennen|mennessä|viim|\bbefore\b|\bby\b|latest|före|senast/
const DELIVERY = /toimit|perillä|perille|vastaanot|kohde|deliver|arrive|destination|receiv|leverera|leverans|framme|mottag/
const CLOCK = /(?:klo|kl\.?)\s*(\d{1,2})(?:[.:](\d{2}))?|\b(\d{1,2})[.:](\d{2})\b/g
/** Opening hours as a range: "9-16", "klo 9.00-14.30", "kl 10-14". */
const RANGE = /\b(\d{1,2})(?:[.:](\d{2}))?\s*[-–]\s*(\d{1,2})(?:[.:](\d{2}))?\b/g

/** Narrows a stop's window by clock times in the note, found by keywords: "nouto ennen 15.30",
 * "klo 12 jälkeen", "deliver by 19:00", "efter kl. 12", "aikaisintaan klo 13.30", "not before
 * 16:00", and opening hours as a range, "arkisin 9-16". The time is on the window's own day. */
function windowFromNote(note: Note | null, window: TimeWindow, stop: "pickup" | "delivery"): TimeWindow {
  if (!note) return window
  let text = note.text.toLowerCase()
  if (DELIVERY.test(text) !== (stop === "delivery")) return window
  const minutes = (hour: number, minute: number): number | null => (hour > 24 || minute > 59 ? null : hour * HOUR + minute)
  const dayStart = (t: number) => Math.floor(t / DAY) * DAY
  let { from, to } = window
  // Opening hours hold every day: they move the window's start to the first day's opening and its end to the last day's closing.
  for (const match of text.matchAll(RANGE)) {
    const opens = minutes(Number(match[1]), Number(match[2] ?? 0))
    const closes = minutes(Number(match[3]), Number(match[4] ?? 0))
    if (opens === null || closes === null || opens >= closes) continue
    from = Math.max(from, dayStart(from) + opens)
    to = Math.min(to, dayStart(to) + closes)
  }
  text = text.replace(RANGE, " ")
  for (const match of text.matchAll(CLOCK)) {
    const m = minutes(Number(match[1] ?? match[3]), Number(match[2] ?? match[4] ?? 0))
    if (m === null) continue
    const time = dayStart(window.from) + m
    const around = text.slice(Math.max(0, match.index - 16), match.index + match[0].length + 16)
    if (AFTER.test(around)) from = Math.max(from, time)
    else if (BEFORE.test(around)) to = Math.min(to, time)
  }
  return from <= to ? { from, to } : window
}

/** Steps the world from one event that needs an answer to the next, and stops at each midnight for a report. */
async function playPractice(world: World, level: number): Promise<void> {
  const { now, endsAt } = await world.snapshot()
  const desk = new Desk(world, level, now)
  while (desk.now < endsAt) {
    const day = Math.floor(desk.now / DAY)
    const midnight = (day + 1) * DAY
    // One request a step: the advance applies the outbox, then moves the clock.
    const actions = desk.outbox.splice(0)
    const step = await world.advance({ untilEvent: WAKE_ON, max: Math.min(endsAt, midnight), actions })
    desk.readResults(actions, step.results)
    desk.now = step.now
    for (const event of step.events) await desk.handle(event)
    if (Math.floor(desk.now / DAY) > day) report(WEEKDAYS[day % 7]!, await world.score())
  }
}

/** Rebuilds the books, then answers events as they come. After a second without an event,
 * it reads the clock. */
async function playFinal(world: World): Promise<void> {
  const history = await world.events()
  const snapshot = await world.snapshot()
  if (snapshot.now >= snapshot.endsAt) return
  const level = (await world.client.worlds()).find((summary) => summary.worldId === world.id)?.level ?? 8
  const desk = new Desk(world, level, snapshot.now)
  await desk.rejoin(snapshot, history)
  await desk.send()
  for await (const event of world.stream({ after: history.at(-1)?.seq ?? -1, idleMs: 1000 })) {
    const day = Math.floor(desk.now / DAY)
    desk.now = event === null ? (await world.client.final()).now : Math.max(desk.now, event.at)
    if (event !== null) await desk.handle(event)
    await desk.send()
    if (Math.floor(desk.now / DAY) > day) report(WEEKDAYS[day % 7]!, await world.score())
    if (desk.now >= snapshot.endsAt) return
  }
}

function report(label: string, score: Score): void {
  const euros = (cents: number) => (cents / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).padStart(11)
  const percent = (share: number, width: number) => `${(100 * share).toFixed(1)}%`.padStart(width)
  const orders = `${String(score.wonOrders).padStart(4)} orders  ${percent(score.onTimeShare, 6)} on time  ${percent(score.undeliveredShare, 5)} not delivered`
  console.log(`${label.padEnd(9)}  margin €${euros(score.marginCents)}  revenue €${euros(score.revenueCents)}  ${orders}`)
}

/** Your copy of the final that is set or runs now. Waits while none is set and while the last one has ended:
 * the organisers set a test final 15 minutes before its start, and the final 30 minutes before. */
async function nextFinal(client: Client): Promise<World> {
  for (let said = false; ; said = true) {
    const set = await client.final().catch((error: unknown) => {
      if (error instanceof SpreadError && error.status === 404) return null
      throw error
    })
    const world = set ? client.world(set.worldId) : null
    if (world) {
      const snapshot = await world.snapshot()
      if (snapshot.now < snapshot.endsAt) return world
    }
    if (!said) console.log("No final is set. Waiting for it: the organisers set a test final 15 minutes before its start, and the final 30 minutes before.")
    await new Promise((done) => setTimeout(done, 10_000))
  }
}

const USAGE = "Usage: bun starter.ts [--level 1-8] [--seed <text>] [--board] [--final]. Set SPREAD_URL and SPREAD_KEY first."

async function main(): Promise<void> {
  const { values: args } = parseArgs({
    options: { level: { type: "string", default: "8" }, seed: { type: "string" }, board: { type: "boolean" }, final: { type: "boolean" } },
  })
  const level = Number(args.level)
  if (![1, 2, 3, 4, 5, 6, 7, 8].includes(level)) throw new SpreadError(0, `--level must be 1 to 8. ${USAGE}`)
  const client = new Client()
  let world: World | undefined
  let score: Score | undefined
  if (args.final) {
    process.once("SIGINT", () => exit("Stopped. The final world keeps running without your system; start it again with --final."))
    // A server restart drops every connection. The desk then rebuilds its books from the server, as after its own restart.
    while (true) {
      try {
        if (!world) {
          world = await nextFinal(client)
          console.log(`Final world ${world.id}.`)
        }
        await playFinal(world)
        score = await world.score()
        break
      } catch (error) {
        if (!(error instanceof Unreachable)) throw error
        console.error(`spread: ${error.message}. Trying again in 5 seconds.`)
        await new Promise((done) => setTimeout(done, 5000))
      }
    }
  } else {
    const run = await client.create(level as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8, { seed: args.seed, board: args.board })
    world = run
    // A ranking run that a team deletes plays to its end without the team's system, and counts.
    const name = `${args.board ? "Ranking run" : "Practice world"} ${run.id}`
    const afterStop = (deleted: boolean) =>
      args.board ? `${name} plays to its end without your system, and counts.` : deleted ? `${name} is deleted.` : `${name} is not deleted: it holds one of your eight practice slots.`
    console.log(`${name}, level ${level}. ${args.board ? "Ctrl-C or an error stops your system: the run then plays to its end without it, and counts." : "Ctrl-C or an error stops the run and deletes the world."}`)
    const remove = () => run.delete().then(() => true, () => false)
    process.once("SIGINT", () => void remove().then((deleted) => exit(`Stopped. ${afterStop(deleted)}`)))
    // A world left behind holds one of the team's eight practice slots.
    await playPractice(run, level).catch(async (error: unknown) => {
      console.error(`Stopped by the error below. ${afterStop(await remove())}`)
      throw error
    })
  }
  score ??= await world.score()
  report("End", score)
  console.log(score.ranked ? "Ranked." : score.wonOrders === 0 ? "Not ranked: no order won." : "Not ranked: the delivery minimum is 90% of the orders on time.")
}

function exit(message: string): never {
  console.error(message)
  process.exit(1)
}

await main().catch((error: unknown) => {
  if (error instanceof SpreadError) exit(`spread: ${error.message}`)
  if (error instanceof TypeError && "code" in error && String(error.code).startsWith("ERR_PARSE_ARGS")) exit(`${error.message}. ${USAGE}`)
  throw error
})

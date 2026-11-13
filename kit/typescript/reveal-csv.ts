/** Writes an ended practice world and its reveal to CSV files, one for each table. See HANDBOOK.md, Research.
 *   bun reveal-csv.ts <world id>                    a practice world that has ended, for example one your system played
 *   bun reveal-csv.ts [--seed <text>] [--level 1-8]   a new practice world, run to its end with no actions: its requests only
 *   --out <folder>                                  instead of reveal-<world id> */
import { mkdirSync, writeFileSync } from "node:fs"
import { parseArgs } from "node:util"
import { Client, SpreadError } from "./spread.ts"

type Row = Record<string, unknown>

/** One row: a nested object gives columns with dotted names, and a list gives one column of JSON. */
function flat(value: object, prefix = "", row: Row = {}): Row {
  for (const [key, item] of Object.entries(value)) {
    if (item !== null && typeof item === "object" && !Array.isArray(item)) flat(item, `${prefix}${key}.`, row)
    else row[prefix + key] = Array.isArray(item) ? JSON.stringify(item) : item
  }
  return row
}

function write(folder: string, name: string, rows: Row[]): void {
  const names = [...new Set(rows.flatMap((row) => Object.keys(row)))]
  // A null object, such as no change of plan, leaves its dotted columns empty and needs no column of its own.
  const columns = names.filter((column) => !names.some((other) => other.startsWith(`${column}.`)))
  const quoted = (text: string) => (/[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text)
  const cell = (value: unknown) => quoted(value === null || value === undefined ? "" : String(value))
  const lines = [columns, ...rows.map((row) => columns.map((column) => row[column]))].map((line) => line.map(cell).join(","))
  writeFileSync(`${folder}/${name}.csv`, lines.join("\n") + "\n")
  console.log(`${folder}/${name}.csv: ${rows.length} rows`)
}

const flags = { seed: { type: "string" }, level: { type: "string", default: "8" }, out: { type: "string" } } as const
const { values: args, positionals } = parseArgs({ allowPositionals: true, options: flags })
try {
  const client = new Client()
  const world = positionals[0] ? client.world(positionals[0]) : await client.create(Number(args.level) as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8, { seed: args.seed })
  if (!positionals[0]) {
    await world.advance({ to: (await world.snapshot()).endsAt })
    console.log(`Practice world ${world.id}, level ${args.level}, ran to its end with no actions.`)
  }
  const [reveal, events, { gigs }, roster, map] = [await world.reveal(), await world.events(), await world.snapshot(), await world.roster(), await client.map()]
  const folder = args.out ?? `reveal-${world.id}`
  mkdirSync(folder, { recursive: true })
  const truth = new Map(reveal.orders.map((order) => [order.orderId, order.legs]))
  const requests = reveal.requests.map(({ request: { legs, options, note, ...request }, quote, ...answer }) => ({
    ...request, ...answer, legs: legs.length, note: note?.text ?? null, language: note?.language ?? null,
    ...Object.fromEntries(options.flatMap(({ kind, ...option }) => Object.entries({ ...option, quoteCents: quote?.[kind] }).map(([key, value]) => [`${kind}.${key}`, value]))),
  }))
  write(folder, "requests", requests)
  write(folder, "legs", reveal.requests.flatMap(({ request }) => request.legs.map((leg, i) => ({ requestId: request.id, leg: i, ...flat(leg), ...flat(truth.get(request.id)?.[i] ?? {}, "truth.") }))))
  write(folder, "drivers", roster.map((driver) => flat(driver)))
  write(folder, "views", reveal.views.map((view) => flat(view)))
  write(folder, "gigs", gigs.map((gig) => ({ ...flat(gig), orders: [...new Set(gig.stops.map((stop) => stop.orderId))].join(" ") })))
  write(folder, "events", events.filter((event) => event.kind !== "price_request").map((event) => flat(event)))
  write(folder, "places", map.places)
  write(folder, "roads", map.roads)
} catch (error) {
  if (!(error instanceof SpreadError)) throw error
  console.error(`spread: ${error.message}`)
  process.exit(1)
}

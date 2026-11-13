// Generated from the API contract, /openapi.json on the server. Do not edit.
// Times are world minutes from Monday 00:00; money is integer game-euro cents.

export type QuoteAction = {
  type: "quote"
  requestId: string
  prices: Partial<Record<"same_day" | "next_day" | "within_3_days", number>>
}

export type TimeWindow = {
  from: number
  to: number
}

export type StopRef = {
  orderId: string
  leg: number
  kind: "pickup" | "delivery"
  window?: TimeWindow
  withPlates?: boolean
  withCharging?: boolean
}

export type Audience = {
  experienced: boolean
  manualLicence: boolean
}

export type FeeStep = {
  at: number
  feeCents: number
}

export type PostAction = {
  type: "post"
  stops: StopRef[]
  audience: Audience
  schedule: FeeStep[]
}

export type OfferAction = {
  type: "offer"
  gigId: string
  driverId: string
  feeCents: number
}

export type RepriceAction = {
  type: "reprice"
  gigId: string
  schedule: FeeStep[]
}

export type WithdrawAction = {
  type: "withdraw"
  gigId: string
}

export type ReleaseAction = {
  type: "release"
  gigId: string
}

export type Action =
  | QuoteAction
  | PostAction
  | OfferAction
  | RepriceAction
  | WithdrawAction
  | ReleaseAction

export type ActionDone = {
  ok: true
  id: string
}

export type ActionRefused = {
  ok: false
  reason: string
}

export type ActionResult =
  | ActionDone
  | ActionRefused

export type Car = {
  premium: boolean
  electric: boolean
  chargePercent: number | null
}

export type Saturday = {
  opens: number
  closes: number
}

export type OpeningHours = {
  opens: number
  closes: number
  weekdays: number[]
  saturday: Saturday | null
}

export type StopPlace = {
  placeId: string
  privateAddress: boolean
  window: TimeWindow
  hours: OpeningHours | null
}

export type Leg = {
  car: Car
  pickup: StopPlace
  delivery: StopPlace
}

export type DeliveryOption = {
  kind: "same_day" | "next_day" | "within_3_days"
  deadline: number
  listPriceCents: number
}

export type Note = {
  text: string
  language: "fi" | "sv" | "en"
}

export type PriceRequest = {
  id: string
  dealerId: string
  batchId: string | null
  arrivedAt: number
  respondBy: number
  legs: Leg[]
  options: DeliveryOption[]
  referenceFeeCents: number
  note: Note | null
}

export type PriceRequestEvent = {
  seq: number
  at: number
  kind: "price_request"
  request: PriceRequest
}

export type Order = {
  id: string
  dealerId: string
  option: "same_day" | "next_day" | "within_3_days"
  priceCents: number
  deadline: number
  legs: Leg[]
  status: "waiting" | "booked" | "moving" | "delivered" | "cancelled"
  deliveredAt: (number | null)[]
  lastPickupAt: number
}

export type OrderWonEvent = {
  seq: number
  at: number
  kind: "order_won"
  order: Order
}

export type OrderLostEvent = {
  seq: number
  at: number
  kind: "order_lost"
  requestId: string
}

export type OrderChangedEvent = {
  seq: number
  at: number
  kind: "order_changed"
  order: Order
  message: Note
}

export type CancelledGig = {
  gigId: string
  outcome: "withdrawn" | "released" | "shortened" | "continues"
}

export type OrderCancelledEvent = {
  seq: number
  at: number
  kind: "order_cancelled"
  orderId: string
  gigs: CancelledGig[]
}

export type ReleaseEvent = {
  seq: number
  at: number
  kind: "release"
  orderId: string
  leg: number
}

export type GigViewedEvent = {
  seq: number
  at: number
  kind: "gig_viewed"
  gigId: string
  driverId: string
}

export type GigBookedEvent = {
  seq: number
  at: number
  kind: "gig_booked"
  gigId: string
  driverId: string
  feeCents: number
}

export type GigDroppedEvent = {
  seq: number
  at: number
  kind: "gig_dropped"
  gigId: string
  driverId: string
}

export type GigStartedEvent = {
  seq: number
  at: number
  kind: "gig_started"
  gigId: string
  driverId: string
}

export type DriverLateEvent = {
  seq: number
  at: number
  kind: "driver_late"
  gigId: string
  driverId: string
  pickupAt: number
}

export type NoShowEvent = {
  seq: number
  at: number
  kind: "no_show"
  gigId: string
  driverId: string
}

export type GigExpiredEvent = {
  seq: number
  at: number
  kind: "gig_expired"
  gigId: string
}

export type OfferAnsweredEvent = {
  seq: number
  at: number
  kind: "offer_answered"
  gigId: string
  driverId: string
  answer: "accepted" | "declined" | "expired"
}

export type PickedUpEvent = {
  seq: number
  at: number
  kind: "picked_up"
  gigId: string
  orderId: string
  leg: number
  placeId: string
}

export type VisitFailedEvent = {
  seq: number
  at: number
  kind: "visit_failed"
  gigId: string
  orderId: string
  leg: number
  reason: "not_ready" | "closed" | "licence" | "no_plates"
}

export type DeliveredEvent = {
  seq: number
  at: number
  kind: "delivered"
  gigId: string
  orderId: string
  leg: number
  placeId: string
}

export type DeadlineCloseEvent = {
  seq: number
  at: number
  kind: "deadline_close"
  orderId: string
  lastPickupAt: number
}

export type ForecastEvent = {
  seq: number
  at: number
  kind: "forecast"
  text: string
  from: number
  to: number
  placeIds: string[]
}

export type LedgerLine = {
  at: number
  kind: "revenue" | "late_refund" | "undelivered_penalty" | "driver_fee" | "failed_visit" | "release_fee" | "waiting" | "fine"
  cents: number
  orderId: string | null
  gigId: string | null
  detail: string
}

export type LedgerEvent = {
  seq: number
  at: number
  kind: "ledger"
  line: LedgerLine
}

export type DeskEvent =
  | PriceRequestEvent
  | OrderWonEvent
  | OrderLostEvent
  | OrderChangedEvent
  | OrderCancelledEvent
  | ReleaseEvent
  | GigViewedEvent
  | GigBookedEvent
  | GigDroppedEvent
  | GigStartedEvent
  | DriverLateEvent
  | NoShowEvent
  | GigExpiredEvent
  | OfferAnsweredEvent
  | PickedUpEvent
  | VisitFailedEvent
  | DeliveredEvent
  | DeadlineCloseEvent
  | ForecastEvent
  | LedgerEvent

export type Gig = {
  id: string
  stops: StopRef[]
  audience: Audience
  schedule: FeeStep[]
  status: "open" | "booked" | "working" | "done" | "withdrawn"
  postedAt: number
  feeCents: number
  driverId: string | null
}

export type DriverPosition = {
  driverId: string
  placeId: string
  gigId: string
}

export type Score = {
  marginCents: number
  revenueCents: number
  marginShare: number
  wonOrders: number
  onTimeShare: number
  undeliveredShare: number
  ranked: boolean
}

export type DeskSnapshot = {
  worldId: string
  now: number
  endsAt: number
  openRequests: PriceRequest[]
  orders: Order[]
  gigs: Gig[]
  driverPositions: DriverPosition[]
  score: Score
}

export type DriverProfile = {
  id: string
  homePlaceId: string
  rating: number
  licence: "manual" | "automatic_only"
  completedGigs: number
  drops: number
}

export type DeskEventKind =
  | "price_request" | "order_won" | "order_lost" | "order_changed" | "order_cancelled" | "release" | "gig_viewed" | "gig_booked" | "gig_dropped" | "gig_started" | "driver_late" | "no_show" | "gig_expired" | "offer_answered" | "picked_up" | "visit_failed" | "delivered" | "deadline_close" | "forecast" | "ledger"

export type CreateWorld = {
  seed?: string
  level: number
  board?: boolean
}

export type WorldId = {
  worldId: string
}

export type WorldSummary = {
  worldId: string
  kind: "practice" | "final"
  level: number
  parent: string | null
  season: number | null
  boardRun: number | null
  ended: boolean
}

export type AdvanceTo = {
  to: number
  actions?: Action[]
}

export type AdvanceBy = {
  by: number
  actions?: Action[]
}

export type AdvanceUntil = {
  untilEvent: DeskEventKind[]
  max: number
  actions?: Action[]
}

export type Advance =
  | AdvanceTo
  | AdvanceBy
  | AdvanceUntil

export type Advanced = {
  results?: ActionResult[]
  now: number
  events: DeskEvent[]
}

export type BoardRun = {
  run: number
  marginCents: number
  onTimeShare: number
  wonOrders: number
  ranked: boolean
  deletedAt: number | null
}

export type BoardTeam = {
  rank: number | null
  team: string
  name: string
  played: number
  ranked: boolean
  marginCents: number | null
  onTimeShare: number | null
  runs: BoardRun[]
}

export type BoardSeason = {
  season: number
  name: string
  startedAt: string
  teams: BoardTeam[]
}

export type PracticeBoard = {
  level: number
  current: BoardSeason | null
  previous: BoardSeason | null
}

export type RevealedRequest = {
  request: PriceRequest
  quote: Partial<Record<"same_day" | "next_day" | "within_3_days", number>> | null
  outcome: "won" | "lost" | "unquoted"
  option: "same_day" | "next_day" | "within_3_days" | null
}

export type LegTruth = {
  readyAt: number
  releasedAt: number | null
  pickupHours: OpeningHours | null
  deliveryHours: OpeningHours | null
  manualGearbox: boolean
  needsPlates: boolean
  summerTyres: boolean
  noteDeadline: number | null
  pickedUpAt: number | null
  deliveredAt: number | null
}

export type RevealedOrder = {
  orderId: string
  legs: LegTruth[]
}

export type View = {
  gigId: string
  driverId: string
  at: number
  feeCents: number
}

export type Reveal = {
  requests: RevealedRequest[]
  orders: RevealedOrder[]
  views: View[]
}

export type Final = {
  worldId: string
  startsAt: string
  now: number
}

export type Place = {
  id: string
  name: string
  lat: number
  lon: number
}

export type Road = {
  from: string
  to: string
  km: number
  minutes: number
}

export type WorldMap = {
  places: Place[]
  roads: Road[]
}

export type Error = {
  error: string
  field?: string
}

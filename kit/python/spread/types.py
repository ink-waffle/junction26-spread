"""Generated from the API contract, /openapi.json on the server. Do not edit.

Times are world minutes from Monday 00:00; money is integer game-euro cents."""
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

QuoteAction = TypedDict("QuoteAction", {
    "type": Literal["quote"],
    "requestId": str,
    "prices": Dict[Literal["same_day", "next_day", "within_3_days"], int],
})

TimeWindow = TypedDict("TimeWindow", {
    "from": int,
    "to": int,
})

StopRef = TypedDict("StopRef", {
    "orderId": str,
    "leg": int,
    "kind": Literal["pickup", "delivery"],
    "window": TimeWindow,
    "withPlates": bool,
    "withCharging": bool,
}, total=False)

Audience = TypedDict("Audience", {
    "experienced": bool,
    "manualLicence": bool,
})

FeeStep = TypedDict("FeeStep", {
    "at": int,
    "feeCents": int,
})

PostAction = TypedDict("PostAction", {
    "type": Literal["post"],
    "stops": List[StopRef],
    "audience": Audience,
    "schedule": List[FeeStep],
})

OfferAction = TypedDict("OfferAction", {
    "type": Literal["offer"],
    "gigId": str,
    "driverId": str,
    "feeCents": int,
})

RepriceAction = TypedDict("RepriceAction", {
    "type": Literal["reprice"],
    "gigId": str,
    "schedule": List[FeeStep],
})

WithdrawAction = TypedDict("WithdrawAction", {
    "type": Literal["withdraw"],
    "gigId": str,
})

ReleaseAction = TypedDict("ReleaseAction", {
    "type": Literal["release"],
    "gigId": str,
})

Action = Union[
    QuoteAction,
    PostAction,
    OfferAction,
    RepriceAction,
    WithdrawAction,
    ReleaseAction,
]

ActionDone = TypedDict("ActionDone", {
    "ok": Literal[True],
    "id": str,
})

ActionRefused = TypedDict("ActionRefused", {
    "ok": Literal[False],
    "reason": str,
})

ActionResult = Union[
    ActionDone,
    ActionRefused,
]

Car = TypedDict("Car", {
    "premium": bool,
    "electric": bool,
    "chargePercent": Optional[int],
})

Saturday = TypedDict("Saturday", {
    "opens": int,
    "closes": int,
})

OpeningHours = TypedDict("OpeningHours", {
    "opens": int,
    "closes": int,
    "weekdays": List[int],
    "saturday": Optional[Saturday],
})

StopPlace = TypedDict("StopPlace", {
    "placeId": str,
    "privateAddress": bool,
    "window": TimeWindow,
    "hours": Optional[OpeningHours],
})

Leg = TypedDict("Leg", {
    "car": Car,
    "pickup": StopPlace,
    "delivery": StopPlace,
})

DeliveryOption = TypedDict("DeliveryOption", {
    "kind": Literal["same_day", "next_day", "within_3_days"],
    "deadline": int,
    "listPriceCents": int,
})

Note = TypedDict("Note", {
    "text": str,
    "language": Literal["fi", "sv", "en"],
})

PriceRequest = TypedDict("PriceRequest", {
    "id": str,
    "dealerId": str,
    "batchId": Optional[str],
    "arrivedAt": int,
    "respondBy": int,
    "legs": List[Leg],
    "options": List[DeliveryOption],
    "referenceFeeCents": int,
    "note": Optional[Note],
})

PriceRequestEvent = TypedDict("PriceRequestEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["price_request"],
    "request": PriceRequest,
})

Order = TypedDict("Order", {
    "id": str,
    "dealerId": str,
    "option": Literal["same_day", "next_day", "within_3_days"],
    "priceCents": int,
    "deadline": int,
    "legs": List[Leg],
    "status": Literal["waiting", "booked", "moving", "delivered", "cancelled"],
    "deliveredAt": List[Optional[int]],
    "lastPickupAt": int,
})

OrderWonEvent = TypedDict("OrderWonEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["order_won"],
    "order": Order,
})

OrderLostEvent = TypedDict("OrderLostEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["order_lost"],
    "requestId": str,
})

OrderChangedEvent = TypedDict("OrderChangedEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["order_changed"],
    "order": Order,
    "message": Note,
})

CancelledGig = TypedDict("CancelledGig", {
    "gigId": str,
    "outcome": Literal["withdrawn", "released", "shortened", "continues"],
})

OrderCancelledEvent = TypedDict("OrderCancelledEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["order_cancelled"],
    "orderId": str,
    "gigs": List[CancelledGig],
})

ReleaseEvent = TypedDict("ReleaseEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["release"],
    "orderId": str,
    "leg": int,
})

GigViewedEvent = TypedDict("GigViewedEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["gig_viewed"],
    "gigId": str,
    "driverId": str,
})

GigBookedEvent = TypedDict("GigBookedEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["gig_booked"],
    "gigId": str,
    "driverId": str,
    "feeCents": int,
})

GigDroppedEvent = TypedDict("GigDroppedEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["gig_dropped"],
    "gigId": str,
    "driverId": str,
})

GigStartedEvent = TypedDict("GigStartedEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["gig_started"],
    "gigId": str,
    "driverId": str,
})

DriverLateEvent = TypedDict("DriverLateEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["driver_late"],
    "gigId": str,
    "driverId": str,
    "pickupAt": int,
})

NoShowEvent = TypedDict("NoShowEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["no_show"],
    "gigId": str,
    "driverId": str,
})

GigExpiredEvent = TypedDict("GigExpiredEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["gig_expired"],
    "gigId": str,
})

OfferAnsweredEvent = TypedDict("OfferAnsweredEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["offer_answered"],
    "gigId": str,
    "driverId": str,
    "answer": Literal["accepted", "declined", "expired"],
})

PickedUpEvent = TypedDict("PickedUpEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["picked_up"],
    "gigId": str,
    "orderId": str,
    "leg": int,
    "placeId": str,
})

VisitFailedEvent = TypedDict("VisitFailedEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["visit_failed"],
    "gigId": str,
    "orderId": str,
    "leg": int,
    "reason": Literal["not_ready", "closed", "licence", "no_plates"],
})

DeliveredEvent = TypedDict("DeliveredEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["delivered"],
    "gigId": str,
    "orderId": str,
    "leg": int,
    "placeId": str,
})

DeadlineCloseEvent = TypedDict("DeadlineCloseEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["deadline_close"],
    "orderId": str,
    "lastPickupAt": int,
})

ForecastEvent = TypedDict("ForecastEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["forecast"],
    "text": str,
    "from": int,
    "to": int,
    "placeIds": List[str],
})

LedgerLine = TypedDict("LedgerLine", {
    "at": int,
    "kind": Literal["revenue", "late_refund", "undelivered_penalty", "driver_fee", "failed_visit", "release_fee", "waiting", "fine"],
    "cents": int,
    "orderId": Optional[str],
    "gigId": Optional[str],
    "detail": str,
})

LedgerEvent = TypedDict("LedgerEvent", {
    "seq": int,
    "at": int,
    "kind": Literal["ledger"],
    "line": LedgerLine,
})

DeskEvent = Union[
    PriceRequestEvent,
    OrderWonEvent,
    OrderLostEvent,
    OrderChangedEvent,
    OrderCancelledEvent,
    ReleaseEvent,
    GigViewedEvent,
    GigBookedEvent,
    GigDroppedEvent,
    GigStartedEvent,
    DriverLateEvent,
    NoShowEvent,
    GigExpiredEvent,
    OfferAnsweredEvent,
    PickedUpEvent,
    VisitFailedEvent,
    DeliveredEvent,
    DeadlineCloseEvent,
    ForecastEvent,
    LedgerEvent,
]

Gig = TypedDict("Gig", {
    "id": str,
    "stops": List[StopRef],
    "audience": Audience,
    "schedule": List[FeeStep],
    "status": Literal["open", "booked", "working", "done", "withdrawn"],
    "postedAt": int,
    "feeCents": int,
    "driverId": Optional[str],
})

DriverPosition = TypedDict("DriverPosition", {
    "driverId": str,
    "placeId": str,
    "gigId": str,
})

Score = TypedDict("Score", {
    "marginCents": int,
    "revenueCents": int,
    "marginShare": float,
    "wonOrders": int,
    "onTimeShare": float,
    "undeliveredShare": float,
    "ranked": bool,
})

DeskSnapshot = TypedDict("DeskSnapshot", {
    "worldId": str,
    "now": int,
    "endsAt": int,
    "openRequests": List[PriceRequest],
    "orders": List[Order],
    "gigs": List[Gig],
    "driverPositions": List[DriverPosition],
    "score": Score,
})

DriverProfile = TypedDict("DriverProfile", {
    "id": str,
    "homePlaceId": str,
    "rating": float,
    "licence": Literal["manual", "automatic_only"],
    "completedGigs": int,
    "drops": int,
})

DeskEventKind = Literal["price_request", "order_won", "order_lost", "order_changed", "order_cancelled", "release", "gig_viewed", "gig_booked", "gig_dropped", "gig_started", "driver_late", "no_show", "gig_expired", "offer_answered", "picked_up", "visit_failed", "delivered", "deadline_close", "forecast", "ledger"]

CreateWorld = TypedDict("CreateWorld", {
    "seed": str,
    "level": int,
    "board": bool,
}, total=False)

WorldId = TypedDict("WorldId", {
    "worldId": str,
})

WorldSummary = TypedDict("WorldSummary", {
    "worldId": str,
    "kind": Literal["practice", "final"],
    "level": int,
    "parent": Optional[str],
    "season": Optional[int],
    "boardRun": Optional[int],
    "ended": bool,
})

AdvanceTo = TypedDict("AdvanceTo", {
    "to": int,
    "actions": List[Action],
}, total=False)

AdvanceBy = TypedDict("AdvanceBy", {
    "by": int,
    "actions": List[Action],
}, total=False)

AdvanceUntil = TypedDict("AdvanceUntil", {
    "untilEvent": List[DeskEventKind],
    "max": int,
    "actions": List[Action],
}, total=False)

Advance = Union[
    AdvanceTo,
    AdvanceBy,
    AdvanceUntil,
]

Advanced = TypedDict("Advanced", {
    "results": List[ActionResult],
    "now": int,
    "events": List[DeskEvent],
}, total=False)

BoardRun = TypedDict("BoardRun", {
    "run": int,
    "marginCents": int,
    "onTimeShare": float,
    "wonOrders": int,
    "ranked": bool,
    "deletedAt": Optional[int],
})

BoardTeam = TypedDict("BoardTeam", {
    "rank": Optional[int],
    "team": str,
    "name": str,
    "played": int,
    "ranked": bool,
    "marginCents": Optional[int],
    "onTimeShare": Optional[float],
    "runs": List[BoardRun],
})

BoardSeason = TypedDict("BoardSeason", {
    "season": int,
    "name": str,
    "startedAt": str,
    "teams": List[BoardTeam],
})

PracticeBoard = TypedDict("PracticeBoard", {
    "level": int,
    "current": Optional[BoardSeason],
    "previous": Optional[BoardSeason],
})

RevealedRequest = TypedDict("RevealedRequest", {
    "request": PriceRequest,
    "quote": Optional[Dict[Literal["same_day", "next_day", "within_3_days"], int]],
    "outcome": Literal["won", "lost", "unquoted"],
    "option": Optional[Literal["same_day", "next_day", "within_3_days"]],
})

LegTruth = TypedDict("LegTruth", {
    "readyAt": int,
    "releasedAt": Optional[int],
    "pickupHours": Optional[OpeningHours],
    "deliveryHours": Optional[OpeningHours],
    "manualGearbox": bool,
    "needsPlates": bool,
    "summerTyres": bool,
    "noteDeadline": Optional[int],
    "pickedUpAt": Optional[int],
    "deliveredAt": Optional[int],
})

RevealedOrder = TypedDict("RevealedOrder", {
    "orderId": str,
    "legs": List[LegTruth],
})

View = TypedDict("View", {
    "gigId": str,
    "driverId": str,
    "at": int,
    "feeCents": int,
})

Reveal = TypedDict("Reveal", {
    "requests": List[RevealedRequest],
    "orders": List[RevealedOrder],
    "views": List[View],
})

Final = TypedDict("Final", {
    "worldId": str,
    "startsAt": str,
    "now": int,
})

Place = TypedDict("Place", {
    "id": str,
    "name": str,
    "lat": float,
    "lon": float,
})

Road = TypedDict("Road", {
    "from": str,
    "to": str,
    "km": float,
    "minutes": int,
})

WorldMap = TypedDict("WorldMap", {
    "places": List[Place],
    "roads": List[Road],
})

Error = TypedDict("Error", {
    "error": str,
    "field": str,
}, total=False)

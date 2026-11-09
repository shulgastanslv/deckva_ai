"""In-memory credit hub: quote → hold → spend | refund."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from app.catalog import PlanId, quote_carousel_credits

Bucket = Literal["promo", "plan", "topup"]
HoldStatus = Literal["held", "spent", "refunded"]

# Free onboarding: enough promo credits for ~3 Economy gens.
PROMO_SEED_CREDITS = 150
TOPUP_TTL_DAYS = 366


@dataclass
class CreditLot:
    id: str
    bucket: Bucket
    balance: int
    expires_at: float | None = None  # unix ts; None = end of billing cycle / no expire


@dataclass
class CreditLedgerEntry:
    id: str
    user_id: str
    kind: Literal["hold", "spend", "refund", "grant"]
    amount: int
    bucket: Bucket | None
    generation_id: str | None
    hold_id: str | None
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class CreditHold:
    id: str
    user_id: str
    generation_id: str
    amount: int
    status: HoldStatus
    allocations: list[tuple[str, int]]  # (lot_id, amount)
    created_at: float = field(default_factory=time.time)


@dataclass
class CreditWallet:
    user_id: str
    plan: PlanId
    lots: list[CreditLot] = field(default_factory=list)


_lock = threading.RLock()
_wallets: dict[str, CreditWallet] = {}
_holds: dict[str, CreditHold] = {}
_ledger: list[CreditLedgerEntry] = []
_spend_by_generation: dict[str, str] = {}  # generation_id → spend ledger id (idempotency)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _bucket_order(bucket: Bucket) -> int:
    return {"promo": 0, "plan": 1, "topup": 2}[bucket]


def _ensure_wallet_unlocked(user_id: str, plan: PlanId = "free") -> CreditWallet:
    wallet = _wallets.get(user_id)
    if wallet is None:
        lots: list[CreditLot] = []
        if plan == "free":
            lots.append(CreditLot(id=_new_id("lot"), bucket="promo", balance=PROMO_SEED_CREDITS))
        elif plan == "starter":
            lots.append(CreditLot(id=_new_id("lot"), bucket="plan", balance=2000))
        elif plan == "pro":
            lots.append(CreditLot(id=_new_id("lot"), bucket="plan", balance=7000))
        wallet = CreditWallet(user_id=user_id, plan=plan, lots=lots)
        _wallets[user_id] = wallet
        if lots:
            _ledger.append(
                CreditLedgerEntry(
                    id=_new_id("led"),
                    user_id=user_id,
                    kind="grant",
                    amount=sum(l.balance for l in lots),
                    bucket=lots[0].bucket,
                    generation_id=None,
                    hold_id=None,
                    meta={"reason": "seed"},
                )
            )
    else:
        wallet.plan = plan
    return wallet


def ensure_wallet(user_id: str, plan: PlanId = "free") -> CreditWallet:
    with _lock:
        return _ensure_wallet_unlocked(user_id, plan=plan)


def balance_of(user_id: str) -> dict[str, int]:
    with _lock:
        wallet = _ensure_wallet_unlocked(user_id)
        now = time.time()
        totals: dict[str, int] = {"promo": 0, "plan": 0, "topup": 0, "total": 0}
        for lot in wallet.lots:
            if lot.expires_at is not None and lot.expires_at < now:
                continue
            totals[lot.bucket] += lot.balance
            totals["total"] += lot.balance
        return totals


def quote(*, model_id: str, slides: int, mode: str = "fast") -> dict[str, Any]:
    quality = 1.15 if mode == "thinking" else 1.0
    amount = quote_carousel_credits(model_id=model_id, slides=slides, quality_mult=quality)
    return {
        "action": "carousel.generate",
        "modelId": model_id,
        "slides": slides,
        "mode": mode,
        "credits": amount,
    }


def _available_lots(wallet: CreditWallet) -> list[CreditLot]:
    now = time.time()
    lots = [
        lot
        for lot in wallet.lots
        if lot.balance > 0 and (lot.expires_at is None or lot.expires_at >= now)
    ]
    return sorted(lots, key=lambda l: (_bucket_order(l.bucket), l.expires_at or float("inf")))


def hold(*, user_id: str, generation_id: str, amount: int) -> CreditHold:
    if amount < 1:
        raise RuntimeError("hold amount must be >= 1")
    with _lock:
        # idempotent re-hold same generation
        for h in _holds.values():
            if h.generation_id == generation_id and h.user_id == user_id and h.status == "held":
                return h

        wallet = _ensure_wallet_unlocked(user_id)
        lots = _available_lots(wallet)
        remaining = amount
        allocations: list[tuple[str, int]] = []
        for lot in lots:
            if remaining <= 0:
                break
            take = min(lot.balance, remaining)
            lot.balance -= take
            allocations.append((lot.id, take))
            remaining -= take

        if remaining > 0:
            # rollback
            lot_by_id = {l.id: l for l in wallet.lots}
            for lot_id, take in allocations:
                lot_by_id[lot_id].balance += take
            raise RuntimeError(
                f"Недостаточно кредитов: нужно {amount}, доступно {amount - remaining}."
            )

        hold_row = CreditHold(
            id=_new_id("hold"),
            user_id=user_id,
            generation_id=generation_id,
            amount=amount,
            status="held",
            allocations=allocations,
        )
        _holds[hold_row.id] = hold_row
        _ledger.append(
            CreditLedgerEntry(
                id=_new_id("led"),
                user_id=user_id,
                kind="hold",
                amount=amount,
                bucket=None,
                generation_id=generation_id,
                hold_id=hold_row.id,
            )
        )
        return hold_row


def spend(hold_id: str) -> CreditLedgerEntry:
    with _lock:
        hold_row = _holds.get(hold_id)
        if hold_row is None:
            raise RuntimeError(f"Hold не найден: {hold_id}")
        if hold_row.status == "spent":
            existing = _spend_by_generation.get(hold_row.generation_id)
            if existing:
                for e in _ledger:
                    if e.id == existing:
                        return e
            raise RuntimeError("Hold уже spent, но ledger entry потерян.")
        if hold_row.status == "refunded":
            raise RuntimeError("Hold уже refunded.")

        # idempotency by generationId
        if hold_row.generation_id in _spend_by_generation:
            hold_row.status = "spent"
            for e in _ledger:
                if e.id == _spend_by_generation[hold_row.generation_id]:
                    return e

        entry = CreditLedgerEntry(
            id=_new_id("led"),
            user_id=hold_row.user_id,
            kind="spend",
            amount=hold_row.amount,
            bucket=None,
            generation_id=hold_row.generation_id,
            hold_id=hold_id,
        )
        hold_row.status = "spent"
        _spend_by_generation[hold_row.generation_id] = entry.id
        _ledger.append(entry)
        return entry


def refund(hold_id: str, *, reason: str = "") -> CreditLedgerEntry:
    with _lock:
        hold_row = _holds.get(hold_id)
        if hold_row is None:
            raise RuntimeError(f"Hold не найден: {hold_id}")
        if hold_row.status == "refunded":
            for e in reversed(_ledger):
                if e.hold_id == hold_id and e.kind == "refund":
                    return e
        if hold_row.status == "spent":
            raise RuntimeError("Нельзя refund после spend.")

        wallet = _wallets[hold_row.user_id]
        lot_by_id = {l.id: l for l in wallet.lots}
        for lot_id, take in hold_row.allocations:
            lot_by_id[lot_id].balance += take

        hold_row.status = "refunded"
        entry = CreditLedgerEntry(
            id=_new_id("led"),
            user_id=hold_row.user_id,
            kind="refund",
            amount=hold_row.amount,
            bucket=None,
            generation_id=hold_row.generation_id,
            hold_id=hold_id,
            meta={"reason": reason},
        )
        _ledger.append(entry)
        return entry


def grant_topup(user_id: str, credits: int) -> CreditLot:
    with _lock:
        wallet = _ensure_wallet_unlocked(user_id)
        lot = CreditLot(
            id=_new_id("lot"),
            bucket="topup",
            balance=credits,
            expires_at=time.time() + TOPUP_TTL_DAYS * 86400,
        )
        wallet.lots.append(lot)
        _ledger.append(
            CreditLedgerEntry(
                id=_new_id("led"),
                user_id=user_id,
                kind="grant",
                amount=credits,
                bucket="topup",
                generation_id=None,
                hold_id=None,
                meta={"pack": "manual"},
            )
        )
        return lot


def set_plan(user_id: str, plan: PlanId) -> CreditWallet:
    return ensure_wallet(user_id, plan=plan)


def ledger_for(user_id: str, *, limit: int = 50) -> list[CreditLedgerEntry]:
    with _lock:
        rows = [e for e in _ledger if e.user_id == user_id]
    return list(reversed(rows[-limit:]))

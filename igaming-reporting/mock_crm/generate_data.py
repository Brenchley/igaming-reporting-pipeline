"""
Generate a realistic synthetic iGaming dataset (ZAR, South African player base).

Produces players, payment transactions, bets (sportsbook + casino), bonus events
and the CRM's own daily summary report, which the pipeline later reconciles against.
All personal data is fake. Deterministic via --seed.
"""
import argparse
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROVINCES = ["GP", "WC", "KZN", "EC", "FS", "MP", "LP", "NW", "NC"]
CHANNELS = ["web", "android", "ios"]
CASINO_GAMES = ["slots", "live_roulette", "live_blackjack", "crash", "lucky_numbers"]
SPORTS = ["soccer", "rugby", "cricket", "horse_racing", "tennis"]
FIRST = ["Thabo", "Lerato", "Sipho", "Ayanda", "Johan", "Megan", "Kagiso", "Naledi", "Pieter", "Zanele"]
LAST = ["Nkosi", "Dlamini", "van der Merwe", "Botha", "Mokoena", "Naidoo", "Khumalo", "Smith", "Pillay", "Mahlangu"]

SAST = timezone(timedelta(hours=2))


def iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def money(x: float) -> float:
    return round(x, 2)


def fake_sa_id(rng: random.Random, dob: datetime) -> str:
    return dob.strftime("%y%m%d") + "".join(str(rng.randint(0, 9)) for _ in range(7))


def generate(n_players: int, days: int, seed: int, end: datetime):
    rng = random.Random(seed)
    start = end - timedelta(days=days)
    players, txns, bets, bonuses = [], [], [], []

    for i in range(n_players):
        pid = f"P{100000 + i}"
        reg = start + timedelta(seconds=rng.randint(0, int((end - start).total_seconds() * 0.98)))
        dob = datetime(rng.randint(1960, 2005), rng.randint(1, 12), rng.randint(1, 28))
        fn, ln = rng.choice(FIRST), rng.choice(LAST)
        segment = rng.choices(["casual", "regular", "high_value", "dormant"], [55, 30, 5, 10])[0]
        players.append({
            "player_id": pid,
            "first_name": fn,
            "last_name": ln,
            "email": f"{fn.lower()}.{ln.lower().replace(' ', '')}{i}@example.co.za",
            "mobile": f"+27{rng.choice(['6','7','8'])}{rng.randint(10000000, 99999999)}",
            "id_number": fake_sa_id(rng, dob),
            "date_of_birth": dob.strftime("%Y-%m-%d"),
            "province": rng.choice(PROVINCES),
            "registration_channel": rng.choice(CHANNELS),
            "registered_at": iso(reg),
            "kyc_status": rng.choices(["verified", "pending", "failed"], [85, 12, 3])[0],
            "marketing_opt_in": rng.random() < 0.6,
            "status": rng.choices(["active", "self_excluded", "closed"], [95, 3, 2])[0],
            "updated_at": iso(reg + timedelta(days=rng.randint(0, 5))),
        })
        if segment == "dormant":
            continue

        stake_scale = {"casual": 20, "regular": 60, "high_value": 600}[segment]
        active_prob = {"casual": 0.15, "regular": 0.45, "high_value": 0.7}[segment]
        balance = 0.0
        got_welcome = False
        day = reg
        while day < end:
            if rng.random() < active_prob or day == reg:
                session_start = day + timedelta(minutes=rng.randint(0, 600))
                # Deposit
                if balance < stake_scale * 2:
                    dep = money(rng.choice([50, 100, 200, 250, 500, 1000, 2000]) * (stake_scale / 40))
                    dep = max(dep, 20.0)
                    status = rng.choices(["completed", "failed"], [94, 6])[0]
                    txns.append({
                        "transaction_id": str(uuid.UUID(int=rng.getrandbits(128))),
                        "player_id": pid, "type": "deposit", "amount": dep, "currency": "ZAR",
                        "method": rng.choice(["card", "eft", "ozow", "voucher_1foryou", "ott_voucher"]),
                        "status": status, "created_at": iso(session_start),
                        "updated_at": iso(session_start + timedelta(seconds=30)),
                    })
                    if status == "completed":
                        balance += dep
                        if not got_welcome:
                            got_welcome = True
                            bonus_id = str(uuid.UUID(int=rng.getrandbits(128)))
                            amt = money(min(dep, 1000.0))
                            bonuses.append({"bonus_event_id": bonus_id + "-g", "bonus_id": bonus_id,
                                            "player_id": pid, "bonus_type": "welcome_match",
                                            "event_type": "granted", "amount": amt,
                                            "event_at": iso(session_start + timedelta(minutes=1))})
                            outcome = rng.choices(["released", "forfeited", "expired"], [30, 30, 40])[0]
                            rel_amt = money(amt * rng.uniform(0.3, 1.0)) if outcome == "released" else amt
                            bonuses.append({"bonus_event_id": bonus_id + "-" + outcome[0], "bonus_id": bonus_id,
                                            "player_id": pid, "bonus_type": "welcome_match",
                                            "event_type": outcome, "amount": rel_amt,
                                            "event_at": iso(session_start + timedelta(days=rng.randint(1, 14)))})
                # Free bet promo
                if rng.random() < 0.05:
                    bonus_id = str(uuid.UUID(int=rng.getrandbits(128)))
                    fb = money(rng.choice([25, 50, 100]))
                    bonuses.append({"bonus_event_id": bonus_id + "-g", "bonus_id": bonus_id, "player_id": pid,
                                    "bonus_type": "free_bet", "event_type": "granted", "amount": fb,
                                    "event_at": iso(session_start)})
                    if rng.random() < 0.4:
                        bonuses.append({"bonus_event_id": bonus_id + "-r", "bonus_id": bonus_id, "player_id": pid,
                                        "bonus_type": "free_bet", "event_type": "released",
                                        "amount": money(fb * rng.uniform(1.2, 3.5)),
                                        "event_at": iso(session_start + timedelta(hours=rng.randint(2, 48)))})
                # Bets
                for b in range(rng.randint(1, 25)):
                    if balance <= 1:
                        break
                    product = rng.choices(["casino", "sportsbook"], [60, 40])[0]
                    stake = money(min(balance, rng.expovariate(1 / stake_scale) + 1))
                    placed = session_start + timedelta(seconds=b * rng.randint(20, 300))
                    if product == "casino":
                        # Weighted multipliers give ~95% RTP (5% house edge), typical for slots/live games.
                        mult = rng.choices([0, 0.5, 1, 2, 5, 20, 50], [57, 10, 14, 12, 6, 1, 0.04])[0]
                        payout = money(stake * mult)
                        settled = placed + timedelta(seconds=rng.randint(2, 60))
                        game = rng.choice(CASINO_GAMES)
                    else:
                        odds = round(rng.uniform(1.2, 6.0), 2)
                        win = rng.random() < (1 / odds) * 0.93
                        payout = money(stake * odds) if win else 0.0
                        settled = placed + timedelta(hours=rng.randint(1, 72))
                        game = rng.choice(SPORTS)
                    is_settled = settled < end
                    bets.append({
                        "bet_id": str(uuid.UUID(int=rng.getrandbits(128))),
                        "player_id": pid, "product": product, "game_or_sport": game,
                        "stake": stake, "payout": payout if is_settled else None,
                        "is_bonus_bet": rng.random() < 0.08, "currency": "ZAR",
                        "status": "settled" if is_settled else "open",
                        "placed_at": iso(placed),
                        "settled_at": iso(settled) if is_settled else None,
                        "updated_at": iso(settled if is_settled else placed),
                    })
                    balance -= stake
                    if is_settled:
                        balance += payout
                # Withdrawal
                if balance > stake_scale * 20 and rng.random() < 0.5:
                    wd = money(balance * rng.uniform(0.5, 0.9))
                    status = rng.choices(["completed", "pending", "rejected"], [85, 10, 5])[0]
                    txns.append({
                        "transaction_id": str(uuid.UUID(int=rng.getrandbits(128))),
                        "player_id": pid, "type": "withdrawal", "amount": wd, "currency": "ZAR",
                        "method": "eft", "status": status,
                        "created_at": iso(session_start + timedelta(hours=2)),
                        "updated_at": iso(session_start + timedelta(hours=rng.randint(3, 30))),
                    })
                    if status == "completed":
                        balance -= wd
            day += timedelta(days=1)

    # Nothing can have happened after the extract cut-off.
    cutoff = iso(end - timedelta(seconds=1))
    txns = [t for t in txns if t["created_at"] < iso(end)]
    for t in txns:
        if t["updated_at"] > cutoff:
            t["updated_at"], t["status"] = cutoff, ("pending" if t["type"] == "withdrawal" else t["status"])
    bonuses = [b for b in bonuses if b["event_at"] < iso(end)]
    for p in players:
        p["updated_at"] = min(p["updated_at"], cutoff)
    return players, txns, bets, bonuses


def daily_summary(txns, bets, bonuses):
    """The CRM's own back-office daily report (dates in SAST). The pipeline reconciles to this."""
    out = {}

    def d(ts):
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(SAST).date().isoformat()

    def row(k):
        return out.setdefault(k, {"report_date": k, "deposits": 0.0, "withdrawals": 0.0,
                                  "stakes": 0.0, "payouts": 0.0, "bonus_released": 0.0})
    for t in txns:
        if t["status"] == "completed":
            row(d(t["created_at"]))["deposits" if t["type"] == "deposit" else "withdrawals"] += t["amount"]
    for b in bets:
        if b["status"] == "settled":
            r = row(d(b["settled_at"]))
            r["stakes"] += b["stake"]
            r["payouts"] += b["payout"]
    for e in bonuses:
        if e["event_type"] == "released":
            row(d(e["event_at"]))["bonus_released"] += e["amount"]
    rows = []
    for k in sorted(out):
        r = {key: (round(v, 2) if isinstance(v, float) else v) for key, v in out[k].items()}
        r["ggr"] = round(r["stakes"] - r["payouts"], 2)
        rows.append(r)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", type=int, default=1500)
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="mock_crm/data")
    args = ap.parse_args()

    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    players, txns, bets, bonuses = generate(args.players, args.days, args.seed, end)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in [("players", players), ("transactions", txns), ("bets", bets),
                       ("bonus_events", bonuses), ("daily_summary", daily_summary(txns, bets, bonuses))]:
        (out / f"{name}.json").write_text(json.dumps(rows))
        print(f"{name:15s} {len(rows):>8,d} rows")

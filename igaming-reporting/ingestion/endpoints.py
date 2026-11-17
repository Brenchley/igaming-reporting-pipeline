"""
Source contract: one entry per API resource.

This is the ONLY file that changes when pointing the pipeline at the operator's real
platform API (e.g. Aardvark): map the real paths, cursor/watermark fields and columns here.
`pii` controls POPIA handling at landing:  drop = never stored, hash = keyed HMAC only.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Endpoint:
    name: str                  # raw table name
    path: str
    primary_key: str
    watermark_field: str       # field used for incremental `updated_since`
    columns: dict              # column -> logical type (string|int|bool|money|timestamp|date)
    pii: dict = field(default_factory=dict)
    incremental: bool = True


PLAYERS = Endpoint(
    name="players", path="/v1/players", primary_key="player_id", watermark_field="updated_at",
    columns={
        "player_id": "string", "email_hash": "string", "mobile_hash": "string",
        "birth_year": "int", "province": "string", "registration_channel": "string",
        "registered_at": "timestamp", "kyc_status": "string", "marketing_opt_in": "bool",
        "status": "string", "updated_at": "timestamp",
    },
    # Names and SA ID numbers are never landed. Email/mobile are kept only as keyed hashes
    # (for de-duplication / matching), DOB is reduced to birth year.
    pii={"first_name": "drop", "last_name": "drop", "id_number": "drop",
         "email": "hash", "mobile": "hash", "date_of_birth": "birth_year"},
)

TRANSACTIONS = Endpoint(
    name="transactions", path="/v1/transactions", primary_key="transaction_id", watermark_field="updated_at",
    columns={
        "transaction_id": "string", "player_id": "string", "type": "string", "amount": "money",
        "currency": "string", "method": "string", "status": "string",
        "created_at": "timestamp", "updated_at": "timestamp",
    },
)

BETS = Endpoint(
    name="bets", path="/v1/bets", primary_key="bet_id", watermark_field="updated_at",
    columns={
        "bet_id": "string", "player_id": "string", "product": "string", "game_or_sport": "string",
        "stake": "money", "payout": "money", "is_bonus_bet": "bool", "currency": "string",
        "status": "string", "placed_at": "timestamp", "settled_at": "timestamp", "updated_at": "timestamp",
    },
)

BONUS_EVENTS = Endpoint(
    name="bonus_events", path="/v1/bonus-events", primary_key="bonus_event_id", watermark_field="event_at",
    columns={
        "bonus_event_id": "string", "bonus_id": "string", "player_id": "string", "bonus_type": "string",
        "event_type": "string", "amount": "money", "event_at": "timestamp",
    },
)

# The platform's own back-office totals, pulled so we can reconcile our numbers against them.
DAILY_SUMMARY = Endpoint(
    name="crm_daily_summary", path="/v1/reports/daily-summary", primary_key="report_date",
    watermark_field="report_date", incremental=False,
    columns={
        "report_date": "date", "deposits": "money", "withdrawals": "money", "stakes": "money",
        "payouts": "money", "bonus_released": "money", "ggr": "money",
    },
)

ALL = {e.name: e for e in [PLAYERS, TRANSACTIONS, BETS, BONUS_EVENTS, DAILY_SUMMARY]}

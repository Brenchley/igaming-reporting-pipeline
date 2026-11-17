"""Unit tests for ingestion logic (run: pytest -q)."""
from unittest.mock import MagicMock

from ingestion import endpoints
from ingestion.client import CrmClient
from ingestion.pii import apply_pii_rules, keyed_hash


def test_pii_rules_drop_and_hash():
    rec = {"player_id": "P1", "first_name": "Thabo", "last_name": "Nkosi", "id_number": "9001015800087",
           "email": "Thabo@Example.co.za ", "mobile": "+27 82 123 4567", "date_of_birth": "1990-01-01"}
    out = apply_pii_rules(rec, endpoints.PLAYERS.pii, key="k")
    assert {"first_name", "last_name", "id_number", "email", "mobile", "date_of_birth"}.isdisjoint(out)
    assert out["birth_year"] == 1990
    assert out["email_hash"] == keyed_hash("thabo@example.co.za", "k")  # normalised before hashing
    assert len(out["mobile_hash"]) == 64


def test_hash_is_keyed():
    assert keyed_hash("x@y.com", "key1") != keyed_hash("x@y.com", "key2")
    assert keyed_hash(None, "k") is None


def test_every_landed_player_column_is_declared():
    """Guards against a vendor API change silently landing new (possibly personal) fields."""
    rec = {"player_id": "P1", "first_name": "a", "last_name": "b", "id_number": "1", "email": "e",
           "mobile": "m", "date_of_birth": "1990-01-01", "province": "GP", "registration_channel": "web",
           "registered_at": "x", "kyc_status": "verified", "marketing_opt_in": True, "status": "active",
           "updated_at": "x"}
    assert set(apply_pii_rules(rec, endpoints.PLAYERS.pii, "k")) <= set(endpoints.PLAYERS.columns)


def _resp(status, body=None, headers=None):
    r = MagicMock(status_code=status, headers=headers or {})
    r.json.return_value = body
    r.raise_for_status.side_effect = None if status < 400 else Exception(status)
    return r


def test_pagination_and_retry(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    c = CrmClient("http://x", "t", page_size=2)
    c.session.get = MagicMock(side_effect=[
        _resp(200, {"data": [1, 2], "next_cursor": 2}),
        _resp(429, headers={"Retry-After": "1"}),
        _resp(200, {"data": [3], "next_cursor": None}),
    ])
    assert [p for p in c.paginate("/v1/bets")] == [[1, 2], [3]]
    assert c.session.get.call_count == 3

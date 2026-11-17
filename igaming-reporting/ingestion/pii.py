"""POPIA data minimisation applied before anything is written to the warehouse."""
import hashlib
import hmac


def keyed_hash(value: str | None, key: str) -> str | None:
    """HMAC-SHA256 of a normalised value. Keyed (not a plain hash) so values such as
    mobile numbers can't be recovered by brute-forcing the small input space."""
    if value is None or value == "":
        return None
    norm = value.strip().lower().replace(" ", "")
    return hmac.new(key.encode(), norm.encode(), hashlib.sha256).hexdigest()


def apply_pii_rules(record: dict, rules: dict, key: str) -> dict:
    out = dict(record)
    for fld, rule in rules.items():
        val = out.pop(fld, None)
        if rule == "hash":
            out[f"{fld}_hash"] = keyed_hash(val, key)
        elif rule == "birth_year":
            out["birth_year"] = int(val[:4]) if val else None
        elif rule == "drop":
            pass
        else:
            raise ValueError(f"Unknown PII rule {rule!r} for {fld}")
    return out

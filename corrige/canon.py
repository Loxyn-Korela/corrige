"""Canonical JSON (RFC 8785 subset) and content hashes.

The truth, the candidate, the journal and the verdict are hashed on their
canonical serialisation: keys sorted by code point, no whitespace, UTF-8,
integers as plain digits. Floats are refused: nothing in the Corrigé needs
them, and their canonical form is the one place where RFC 8785 is subtle.
"""
import json, hashlib


def _check(o):
    if isinstance(o, float):
        raise TypeError("floats are not allowed in canonical records")
    if isinstance(o, dict):
        for k, v in o.items():
            if not isinstance(k, str):
                raise TypeError("object keys must be strings")
            _check(v)
    elif isinstance(o, list):
        for v in o:
            _check(v)


def dumps(o):
    _check(o)
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256(o):
    return hashlib.sha256(dumps(o).encode("utf-8")).hexdigest()


def write(path, o):
    """Pretty file for humans, canonical hash inside the record."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
        f.write("\n")

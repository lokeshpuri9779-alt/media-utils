"""Offline, extensible ASTRA story planning with persistent novelty checks.

This module produces concept briefs, not completed scripts or approved uploads.
"""
import hashlib
import json
import sqlite3
from pathlib import Path
from astra_v2.story_plot_families import PLOT_FAMILIES


def load_families(directory=None):
    families = {k: tuple(v) for k, v in PLOT_FAMILIES.items()}
    if directory is None:
        return families
    for path in sorted(Path(directory).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        name, beats = data.get("name"), data.get("beat_roles")
        if not isinstance(name, str) or not name.strip() or name in families:
            raise ValueError("invalid or duplicate plot family in " + str(path))
        if not isinstance(beats, list) or len(beats) < 3 or any(
            not isinstance(b, str) or not b.strip() for b in beats
        ):
            raise ValueError("invalid beat roles in " + str(path))
        families[name] = tuple(beats)
    return families


def concept_key(concept):
    fields = ("family", "setting", "protagonist", "goal", "conflict", "twist")
    normalized = [str(concept.get(k, "")).strip().casefold() for k in fields]
    if any(not value for value in normalized):
        raise ValueError("all concept dimensions must be nonempty")
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False).encode()).hexdigest()


class NoveltyStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(str(path))
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS concepts "
            "(fingerprint TEXT PRIMARY KEY, concept_json TEXT NOT NULL, status TEXT NOT NULL)"
        )
        self.connection.commit()

    def reserve(self, concept):
        fingerprint = concept_key(concept)
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO concepts VALUES (?, ?, ?)",
            (fingerprint, json.dumps(concept, sort_keys=True), "draft"),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def close(self):
        self.connection.close()


def candidate_briefs(seed, count, *, families, settings, protagonists, goals,
                     conflicts, twists, format="short", chapters=5):
    if format not in ("short", "long"):
        raise ValueError("format must be short or long")
    if count < 0:
        raise ValueError("count cannot be negative")
    dimensions = [sorted(families), settings, protagonists, goals, conflicts, twists]
    if any(not d for d in dimensions):
        raise ValueError("candidate dimensions cannot be empty")
    for index in range(count):
        digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
        values = [dim[int.from_bytes(digest[4*i:4*i+4], "big") % len(dim)]
                  for i, dim in enumerate(dimensions)]
        family, setting, protagonist, goal, conflict, twist = values
        concept = dict(family=family, setting=setting, protagonist=protagonist,
                       goal=goal, conflict=conflict, twist=twist, format=format)
        concept["beat_roles"] = list(families[family])
        concept["chapters"] = [
            {"number": i + 1, "narrative_role": families[family][i % len(families[family])]}
            for i in range(chapters)
        ] if format == "long" else []
        concept["editorial_approved"] = False
        concept["asset_verified"] = False
        yield concept


def reserve_unique_candidates(store, candidates):
    for candidate in candidates:
        if store.reserve(candidate):
            yield candidate

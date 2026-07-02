"""Append-only Fact store for task execution context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.fact import (
    Fact,
    ValidationStatus,
    fact_from_dict,
    fact_is_expansion_ready,
    fact_scalar_value,
    fact_to_dict,
    new_fact_id,
)


@dataclass
class FactStore:
    """Runtime fact collection with append-only supersession."""

    facts: dict[str, Fact] = field(default_factory=dict)
    active_by_key: dict[str, str] = field(default_factory=dict)

    def active_fact(self, key: str) -> Fact | None:
        fact_id = self.active_by_key.get(key)
        if not fact_id:
            return None
        fact = self.facts.get(fact_id)
        if fact is None or not fact.supersession.active:
            return None
        return fact

    def active_facts(self) -> dict[str, Fact]:
        return {
            key: self.facts[fact_id]
            for key, fact_id in self.active_by_key.items()
            if fact_id in self.facts and self.facts[fact_id].supersession.active
        }

    def append_fact(self, fact: Fact) -> Fact:
        if not fact.id:
            fact.id = new_fact_id()
        self.facts[fact.id] = fact
        if fact.supersession.active:
            self.active_by_key[fact.key] = fact.id
        return fact

    def supersede(self, old_fact_id: str, new_fact: Fact, *, reason: str | None = None) -> Fact:
        old = self.facts.get(old_fact_id)
        if old is not None:
            old.supersession.active = False
            old.supersession.superseded_by = new_fact.id
            old.validation.status = ValidationStatus.SUPERSEDED
            if reason:
                old.supersession.reason = reason
        if not new_fact.id:
            new_fact.id = new_fact_id()
        new_fact.supersession.supersedes = old_fact_id
        new_fact.supersession.active = True
        if reason:
            new_fact.supersession.reason = reason
        return self.append_fact(new_fact)

    def upsert_active(self, fact: Fact) -> Fact:
        """Append a new fact, superseding any existing active fact for the same key."""
        existing = self.active_fact(fact.key)
        if existing is None:
            fact.supersession.active = True
            return self.append_fact(fact)
        return self.supersede(existing.id, fact)

    def get_value(self, key: str, default: Any = None) -> Any:
        fact = self.active_fact(key)
        if fact is None:
            return default
        return fact_scalar_value(fact)

    def has_expansion_ready(self, key: str) -> bool:
        fact = self.active_fact(key)
        return fact is not None and fact_is_expansion_ready(fact)

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": {fid: fact_to_dict(fact) for fid, fact in self.facts.items()},
            "active_by_key": dict(self.active_by_key),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> FactStore:
        if not data:
            return cls()
        facts = {
            fid: fact_from_dict(payload)
            for fid, payload in (data.get("facts") or {}).items()
        }
        return cls(
            facts=facts,
            active_by_key=dict(data.get("active_by_key") or {}),
        )


def fact_store_to_dict(store: FactStore) -> dict[str, Any]:
    return store.to_dict()


def fact_store_from_dict(data: dict[str, Any] | None) -> FactStore:
    return FactStore.from_dict(data)

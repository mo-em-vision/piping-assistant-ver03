"""Runtime Goal tree store for task execution context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.goal import (
    Goal,
    GoalRuntimeStatus,
    SatisfactionStatus,
    goal_from_dict,
    goal_to_dict,
    new_goal_id,
)


class GoalCycleError(ValueError):
    """Raised when linking goals would create a cycle."""


@dataclass
class GoalStore:
    goals: dict[str, Goal] = field(default_factory=dict)
    root_goal_ids: list[str] = field(default_factory=list)

    def get(self, goal_id: str) -> Goal | None:
        return self.goals.get(goal_id)

    def append_goal(self, goal: Goal, *, as_root: bool = False) -> Goal:
        if not goal.id:
            goal.id = new_goal_id()
        self.goals[goal.id] = goal
        if as_root and goal.id not in self.root_goal_ids:
            self.root_goal_ids.append(goal.id)
        return goal

    def link_child(self, parent_id: str, child_id: str) -> None:
        parent = self.goals.get(parent_id)
        child = self.goals.get(child_id)
        if parent is None or child is None:
            raise KeyError(f"Unknown goal: {parent_id!r} or {child_id!r}")
        if self._would_cycle(parent_id, child_id):
            raise GoalCycleError(f"Linking {parent_id} -> {child_id} would create a cycle")
        if child_id not in parent.state.child_goals:
            parent.state.child_goals.append(child_id)
        child.state.parent_goal = parent_id
        if child_id in self.root_goal_ids:
            self.root_goal_ids = [gid for gid in self.root_goal_ids if gid != child_id]

    def _would_cycle(self, parent_id: str, child_id: str) -> bool:
        if parent_id == child_id:
            return True
        visited: set[str] = set()
        stack = [child_id]
        while stack:
            current = stack.pop()
            if current == parent_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            node = self.goals.get(current)
            if node is None:
                continue
            stack.extend(node.state.child_goals)
        return False

    def roots(self) -> list[Goal]:
        return [self.goals[gid] for gid in self.root_goal_ids if gid in self.goals]

    def children(self, goal_id: str) -> list[Goal]:
        goal = self.goals.get(goal_id)
        if goal is None:
            return []
        return [self.goals[cid] for cid in goal.state.child_goals if cid in self.goals]

    def goals_by_class(self, goal_class: str) -> list[Goal]:
        return [g for g in self.goals.values() if g.goal_class.value == goal_class]

    def blocked_goals(self) -> list[Goal]:
        return [
            g
            for g in self.goals.values()
            if g.state.status == GoalRuntimeStatus.BLOCKED
            or g.satisfaction.status == SatisfactionStatus.BLOCKED
        ]

    def ready_goals(self) -> list[Goal]:
        return [
            g
            for g in self.goals.values()
            if g.state.status == GoalRuntimeStatus.READY
            or g.satisfaction.status == SatisfactionStatus.READY
        ]

    def satisfied_goals(self) -> list[Goal]:
        return [
            g
            for g in self.goals.values()
            if g.satisfaction.status == SatisfactionStatus.SATISFIED
            or g.state.status == GoalRuntimeStatus.SATISFIED
        ]

    def active_goals(self) -> list[Goal]:
        return [
            g
            for g in self.goals.values()
            if g.satisfaction.status
            not in {SatisfactionStatus.SATISFIED, SatisfactionStatus.SUPERSEDED}
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "goals": {gid: goal_to_dict(goal) for gid, goal in self.goals.items()},
            "root_goal_ids": list(self.root_goal_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> GoalStore:
        if not data:
            return cls()
        goals = {
            gid: goal_from_dict(payload)
            for gid, payload in (data.get("goals") or {}).items()
        }
        return cls(
            goals=goals,
            root_goal_ids=list(data.get("root_goal_ids") or []),
        )

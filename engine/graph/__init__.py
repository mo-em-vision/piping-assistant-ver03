"""Graph Engine public exports."""

__all__ = ["GraphCycleError", "GraphEngine", "normalize_root_id"]


def __getattr__(name: str):
    if name in {"GraphEngine", "normalize_root_id"}:
        from .graph_engine import GraphEngine, normalize_root_id

        return {"GraphEngine": GraphEngine, "normalize_root_id": normalize_root_id}[name]
    if name == "GraphCycleError":
        from .conditions import GraphCycleError

        return GraphCycleError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

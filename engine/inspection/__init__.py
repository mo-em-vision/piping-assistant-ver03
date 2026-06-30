"""Developer inspection framework — dev-only debugging instrumentation."""

from engine.inspection.dev_guard import inspection_enabled

__all__ = ["build_inspection_payload", "inspection_enabled"]


def build_inspection_payload(*args, **kwargs):
    from engine.inspection.builder import build_inspection_payload as _build

    return _build(*args, **kwargs)

"""Graph-native presentation layer (Phase 9) + Flow Guidance Layer (stub)."""

from .guidance_resolver import (
    GuidanceResolver,
    GuidanceValidationError,
    guidance_context_from_navigation,
    validate_guidance_text,
)
from .presentation_engine import build_presentation
from .response_composer import (
    ResponseComposer,
    append_presentation_to_transcript,
    presentation_blocks_for_transcript_append,
)

__all__ = [
    "GuidanceResolver",
    "GuidanceValidationError",
    "ResponseComposer",
    "append_presentation_to_transcript",
    "build_presentation",
    "guidance_context_from_navigation",
    "presentation_blocks_for_transcript_append",
    "validate_guidance_text",
]

"""Shared helpers for deterministic user-facing prompts."""

from __future__ import annotations


def format_numbered_choices(
    options: tuple[str, ...] | list[str],
    *,
    indent: str = "  ",
    option_indent: str | None = None,
) -> list[str]:
    """Format a list of choices as numbered lines."""
    if not options:
        return []
    child_indent = option_indent if option_indent is not None else f"{indent}  "
    lines = [f"{indent}Choose one:"]
    for index, label in enumerate(options, start=1):
        lines.append(f"{child_indent}{index}. {label}")
    return lines


def format_reply_hint(
    option_count: int,
    *,
    examples: tuple[str, ...] = (),
    indent: str = "  ",
) -> str:
    """Footer hint for how to reply to a numbered choice."""
    if option_count <= 0:
        return ""
    if option_count == 1:
        return f"{indent}Reply with 1 or type your choice."
    example = f" (e.g. {examples[0]})" if examples else ""
    return (
        f"{indent}Reply with the option number (1–{option_count})"
        f"{example}, or type your choice."
    )


def format_parameter_block(
    symbol: str,
    description: str,
    *,
    value: str | None = None,
    guidance: str | None = None,
    options: tuple[str, ...] | list[str] = (),
    indent: str = "  ",
) -> list[str]:
    """Render one formula parameter with symbol, description, and value/guidance on separate lines."""
    lines = [
        f"{indent}{symbol}",
        f"{indent}  Description: {description}",
    ]
    if value is not None:
        lines.append(f"{indent}  Value: {value}")
    if guidance:
        lines.append(f"{indent}  Needed: {guidance}")
    if options:
        lines.extend(
            format_numbered_choices(
                options,
                indent=f"{indent}  ",
                option_indent=f"{indent}    ",
            )
        )
    lines.append("")
    return lines

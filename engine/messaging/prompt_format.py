"""Shared helpers for deterministic user-facing prompts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PromptAssemblyContext:
    """Structured context for assembling a single parameter ask prompt."""

    parameter_id: str
    label: str
    symbol: str | None = None
    phase: str | None = None
    purpose: str | None = None
    usage_site: str | None = None
    units: tuple[str, ...] = ()
    options: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    next_step: str | None = None
    body: str | None = None


def render_parameter_prompt(ctx: PromptAssemblyContext) -> str:
    """Render a user-facing prompt from structured context."""
    if ctx.body and ctx.body.strip():
        base = ctx.body.strip()
    else:
        headline = f"Enter {ctx.label}"
        if ctx.symbol:
            headline += f" ({ctx.symbol})"
        parts: list[str] = [headline]
        if ctx.purpose:
            parts.append(ctx.purpose.rstrip("."))
        if ctx.usage_site:
            parts.append(ctx.usage_site.rstrip("."))
        base = ". ".join(parts) + "."

    lines = [base]
    if ctx.units:
        unit_text = ", ".join(ctx.units)
        lines.append(f"Include units ({unit_text}).")
    if ctx.examples:
        examples = ", ".join(f"`{item}`" for item in ctx.examples)
        lines.append(f"Examples: {examples}.")
    if ctx.warnings:
        for warning in ctx.warnings:
            lines.append(warning.rstrip(".") + ".")
    if ctx.next_step:
        lines.append(ctx.next_step.rstrip(".") + ".")
    if ctx.options:
        lines.append("")
        lines.extend(format_numbered_choices(ctx.options))
        lines.append("")
        lines.append(format_reply_hint(len(ctx.options)))
    return "\n".join(lines)


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

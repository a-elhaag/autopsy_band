"""Render a council result into clean HTML.

Remediation text is appended here, by FM-ID, *after* classification — never
shown to the agents (per agent.md Taxonomy Loading).
"""
from __future__ import annotations

from html import escape as esc

from ..taxonomy import loader


def to_html(result: dict) -> str:
    verdict = result.get("verdict", {})
    validated = result.get("validated_claims", [])
    scored = result.get("scored_claims", [])
    escalation = result.get("escalation", {})

    primary = verdict.get("primary_failure_mode", "FM-00")
    verdict_label = verdict.get("verdict", "Inconclusive")
    chain = verdict.get("causal_chain") or []
    spec = verdict.get("reconstructed_spec", "")

    sev_by_id = {s.get("failure_mode_id"): s for s in scored if isinstance(s, dict)}

    verdict_cls = {
        "Critical": "verdict-critical",
        "High": "verdict-high",
        "Medium": "verdict-medium",
        "Low": "verdict-low",
        "Inconclusive": "verdict-inconclusive",
    }.get(verdict_label, "verdict-inconclusive")

    parts: list[str] = []

    # ── Header ──
    parts.append('<div class="rpt-header">')
    parts.append(f'<span class="rpt-verdict {verdict_cls}">{esc(verdict_label)}</span>')
    parts.append(f'<h2 class="rpt-title">Autopsy Report</h2>')
    parts.append(
        f'<p class="rpt-primary"><span class="rpt-fmcode">{esc(primary)}</span>'
        f' {esc(loader.name_of(primary))}'
        f'<span class="rpt-cat">{esc(loader.category_of(primary))}</span></p>'
    )
    parts.append('</div>')

    # ── FM-00 short path ──
    if primary == "FM-00" or not validated:
        parts.append('<div class="rpt-section">')
        parts.append('<p class="rpt-fm00">No validated failure mode. Input lacked diagnostic signal — FM-00 is a correct result, not a tool failure.</p>')
        rem = loader.remediation_for("FM-00")
        if rem:
            parts.append(f'<p class="rpt-rem"><strong>Next step:</strong> {esc(rem)}</p>')
        parts.append('</div>')
        return "\n".join(parts)

    # ── Causal chain ──
    if chain:
        parts.append('<div class="rpt-section">')
        parts.append('<h3 class="rpt-section-title">Causal chain</h3>')
        parts.append('<div class="rpt-chain">')
        for i, step in enumerate(chain):
            parts.append(f'<span class="rpt-chain-step">{esc(step)}</span>')
            if i < len(chain) - 1:
                parts.append('<span class="rpt-chain-arrow">→</span>')
        parts.append('</div>')
        parts.append('</div>')

    # ── Findings ──
    parts.append('<div class="rpt-section">')
    parts.append('<h3 class="rpt-section-title">Findings</h3>')
    for claim in validated:
        fm = claim.get("failure_mode_id", "")
        sev = sev_by_id.get(fm, {})
        severity = sev.get("severity", "—")
        confidence = sev.get("confidence", "—")
        quote = claim.get("quote", "")
        loc = claim.get("location", "")
        rem = loader.remediation_for(fm)

        sev_cls = {
            "Critical": "sev-critical",
            "High": "sev-high",
            "Medium": "sev-medium",
            "Low": "sev-low",
        }.get(severity, "")

        parts.append('<div class="rpt-finding">')
        parts.append('<div class="rpt-finding-head">')
        parts.append(f'<span class="rpt-fmcode">{esc(fm)}</span>')
        parts.append(f'<span class="rpt-fname">{esc(loader.name_of(fm))}</span>')
        parts.append(f'<span class="rpt-sev {sev_cls}">{esc(severity)}</span>')
        parts.append(f'<span class="rpt-conf">{esc(str(confidence))}% confidence</span>')
        parts.append('</div>')
        if quote:
            parts.append(f'<blockquote class="rpt-quote">{esc(quote)}</blockquote>')
        meta = []
        if loc:
            meta.append(f'<span>Location: {esc(loc)}</span>')
        meta.append(f'<span>Category: {esc(loader.category_of(fm))}</span>')
        parts.append(f'<div class="rpt-meta">{"  ·  ".join(meta)}</div>')
        if rem:
            parts.append(f'<p class="rpt-rem"><strong>Fix:</strong> {esc(rem)}</p>')
        parts.append('</div>')
    parts.append('</div>')

    # ── Reconstructed spec ──
    if spec:
        parts.append('<div class="rpt-section rpt-spec-section">')
        parts.append('<h3 class="rpt-section-title">Reconstructed specification</h3>')
        parts.append(f'<div class="rpt-spec">{esc(spec)}</div>')
        parts.append('</div>')

    # ── Escalation ──
    if escalation.get("escalation"):
        ticket = escalation.get("ticket", {})
        parts.append('<div class="rpt-section rpt-escalation">')
        parts.append('<h3 class="rpt-section-title">⚠ Escalation required</h3>')
        parts.append(f'<p class="rpt-esc-summary">{esc(ticket.get("summary", ""))}</p>')
        parts.append('<div class="rpt-esc-meta">')
        parts.append(f'<span><strong>Mode:</strong> {esc(ticket.get("primary_failure_mode", primary))}</span>')
        parts.append(f'<span><strong>Reviewer:</strong> {esc(ticket.get("reviewer_role", ""))}</span>')
        parts.append('</div>')
        parts.append('</div>')

    return "\n".join(parts)


def to_markdown(result: dict) -> str:
    """Legacy — kept for Band transport compatibility."""
    return to_html(result)

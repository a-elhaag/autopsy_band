"""Render a council result into a Markdown Autopsy Report, then to HTML.

Remediation text is appended here, by FM-ID, *after* classification — never
shown to the agents (per agent.md Taxonomy Loading).
"""
from __future__ import annotations

import markdown as md

from ..taxonomy import loader


def to_markdown(result: dict) -> str:
    verdict = result.get("verdict", {})
    validated = result.get("validated_claims", [])
    scored = result.get("scored_claims", [])
    escalation = result.get("escalation", {})

    primary = verdict.get("primary_failure_mode", "FM-00")
    verdict_label = verdict.get("verdict", "Inconclusive")

    lines: list[str] = []
    lines.append("# Autopsy Report")
    lines.append("")
    lines.append(f"**Verdict:** {verdict_label}")
    lines.append("")
    lines.append(
        f"**Primary failure mode:** {primary} — {loader.name_of(primary)} "
        f"_({loader.category_of(primary)})_"
    )
    lines.append("")

    if primary == "FM-00" or not validated:
        lines.append(
            "> No validated failure mode could be established from the input. "
            "Per design, FM-00 is a high-accuracy result, not a tool failure — "
            "the input lacked enough diagnostic signal to reason about a failure."
        )
        lines.append("")
        lines.append("## Recommended next step")
        lines.append(loader.remediation_for("FM-00"))
        return "\n".join(lines)

    # Causal chain
    chain = verdict.get("causal_chain") or []
    if chain:
        lines.append("## Causal chain (root cause → downstream effect)")
        for step in chain:
            lines.append(f"- `{step}`")
        lines.append("")

    # Severity/confidence index
    sev_by_id = {s.get("failure_mode_id"): s for s in scored if isinstance(s, dict)}

    lines.append("## Validated findings")
    lines.append("")
    for claim in validated:
        fm = claim.get("failure_mode_id", "")
        sev = sev_by_id.get(fm, {})
        severity = sev.get("severity", "—")
        confidence = sev.get("confidence", "—")
        lines.append(f"### {fm} — {loader.name_of(fm)}")
        lines.append(
            f"_Category:_ {loader.category_of(fm)}  ·  "
            f"_Severity:_ {severity}  ·  _Confidence:_ {confidence}"
        )
        lines.append("")
        quote = claim.get("quote", "")
        if quote:
            lines.append("> " + quote.replace("\n", "\n> "))
        loc = claim.get("location")
        if loc:
            lines.append("")
            lines.append(f"_Location:_ {loc}")
        rem = loader.remediation_for(fm)
        if rem:
            lines.append("")
            lines.append(f"**Remediation:** {rem}")
        lines.append("")

    spec = verdict.get("reconstructed_spec", "")
    if spec:
        lines.append("## Reconstructed spec / decision")
        lines.append("")
        lines.append(spec)
        lines.append("")

    if escalation.get("escalation"):
        ticket = escalation.get("ticket", {})
        lines.append("## ⚠️ Human escalation ticket")
        lines.append("")
        lines.append(f"- **Summary:** {ticket.get('summary', '')}")
        lines.append(
            f"- **Primary failure mode:** {ticket.get('primary_failure_mode', primary)}"
        )
        lines.append(f"- **Recommended reviewer:** {ticket.get('reviewer_role', '')}")
        lines.append("")

    return "\n".join(lines)


def to_html(result: dict) -> str:
    return md.markdown(
        to_markdown(result), extensions=["fenced_code", "tables", "nl2br"]
    )

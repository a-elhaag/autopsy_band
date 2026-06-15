## Overview
6-agent council. Diagnoses failed AI builds via 17-mode failure taxonomy. Band SDK handles all inter-agent handoffs as structured data tables.

Input types: prompt+output pair, vague spec, code+description. Max 5000 chars. Stateless.

---

## Agent 1: Annotator

**Role:** Scan input, flag candidate failure modes, quote evidence verbatim.

**System prompt provides:**
- Taxonomy: `{id, name, definition}` only (no remediation text)
- Instruction: identify matching failure modes, extract exact quotes from input as evidence, output JSON

**Receives:** raw input (prompt+output / spec / code+description)

**Outputs:**
```json
[{"failure_mode_id": "FM-12", "quote": "...", "location": "..."}]
```

**Band handoff:** table → Verifier

---

## Agent 2: Verifier

**Role:** Proof gate. Reject any claim without a quote that exactly matches the original input.

**System prompt provides:**
- Same taxonomy defs
- Rule: claim survives only if quote is verbatim-present in original input; else drop

**Receives:** Annotator's table + original input text

**Outputs:**
```json
[{"failure_mode_id": "FM-12", "quote": "...", "location": "...", "validated": true}]
```

**Band handoff:** validated_claims table → Confidence Scorer, Reconstructor

---

## Agent 3: Confidence Scorer

**Role:** Assign severity and confidence per validated claim.

**System prompt provides:**
- Severity rubric: Critical / Moderate / Low — defined by impact + reversibility
- Confidence rubric: 0–100, based on quote directness and ambiguity

**Receives:** validated_claims + original input

**Outputs:**
```json
[{"failure_mode_id": "FM-12", "severity": "Critical", "confidence": 85}]
```

**Band handoff:** scored_claims table → Apex Synthesizer

---

## Agent 4: Reconstructor

**Role:** Draft what the spec/architecture/code should have been, based on validated failure modes.

**System prompt provides:**
- Instruction: for each validated claim, produce a corrected counterpart (spec line, arch decision, or code fix description — text only, no full code rewrite)

**Receives:** validated_claims + original input

**Outputs:**
```json
{"reconstructed_spec": "..."}
```

**Band handoff:** reconstruction → Apex Synthesizer

---

## Agent 5: Apex Synthesizer

**Role:** Merge scored claims + reconstruction into final diagnosis.

**System prompt provides:**
- Verdict logic:
  - **Critical** — high-severity validated claim(s), unrecoverable without redesign
  - **Recoverable** — validated claim(s) present, fixable without redesign
  - **Inconclusive** — claims present but low confidence / conflicting
  - **FM-00** — no validated claims (insufficient signal); explicitly a high-accuracy result, not a failure
- Causal chain instruction: order failure modes by root-cause → downstream effect

**Receives:** scored_claims + reconstructed_spec + original input

**Outputs:**
```json
{
  "primary_failure_mode": "FM-12",
  "causal_chain": ["FM-XX -> FM-YY -> FM-12"],
  "verdict": "Critical",
  "reconstructed_spec": "..."
}
```

**Band handoff:** verdict object → Human-Escalation

---

## Agent 6: Human-Escalation

**Role:** Route Critical verdicts to human review. Pass-through otherwise.

**System prompt provides:**
- Trigger rule: if verdict == "Critical" → generate escalation ticket (summary, primary failure mode, recommended reviewer role); else pass verdict unchanged

**Receives:** Apex Synthesizer output

**Outputs:**
```json
{
  "escalation": true,
  "ticket": {"summary": "...", "primary_failure_mode": "FM-12", "reviewer_role": "..."}
}
```
or
```json
{"escalation": false}
```

**Band handoff:** final → report renderer (Markdown Autopsy Report to user)

---

## Pipeline

```
Input → 1.Annotator → 2.Verifier → 3.ConfidenceScorer ─┐
                                  → 4.Reconstructor ────┤
                                                          → 5.Apex → 6.HumanEscalation → Report
```

## Failure Taxonomy (v1.0)

17 failure modes across 5 categories, derived from real enterprise AI engagements.

### Prompt & Framing
| ID | Name |
|----|------|
| FM-01 | Context Gap |
| FM-02 | God-Prompt Overload |
| FM-03 | Sycophantic Feasibility |
| FM-04 | Problem Framing Failure |

### Spec & Planning
| ID | Name |
|----|------|
| FM-05 | Missing Acceptance Criteria |
| FM-06 | Uncontrolled Evolution |
| FM-07 | Business Objective Misalignment |

### Architecture & Design
| ID | Name |
|----|------|
| FM-08 | Architecture-MVP Mismatch |
| FM-09 | Model Capability Mismatch |
| FM-10 | Integration Reality Gap |

### Context & Execution
| ID | Name |
|----|------|
| FM-11 | Context Collapse |
| FM-12 | Hallucinated Assumptions |
| FM-13 | No Verification Loop |
| FM-14 | Evaluation Blindness |

### Decision & Governance
| ID | Name |
|----|------|
| FM-15 | No Decision Ownership |
| FM-16 | False Confidence from Plausible Output |
| FM-17 | Shadow Logic |

### Null State
| ID | Name | Note |
|----|------|------|
| FM-00 | Insufficient Data | Input lacks enough diagnostic signal. Returning FM-00 is a high-accuracy result, not a tool failure. The Judge is explicitly instructed to prefer FM-00 over hallucinating a finding. |

---

## Taxonomy Loading

The taxonomy loads at server startup. Each agent receives only `{id, name, definition}` per failure mode — remediation text is stored separately and appended by FM-ID *after* classification. This keeps token cost low and separates diagnosis from prescription.

---

## Non-Goals

These are deliberate constraints, not gaps:
- Does not fix or rewrite code — diagnoses the upstream decision that caused the code to be wrong.
- Does not process single sentences — context-free inputs return Inconclusive by design.
- Does not connect to GitHub, Jira, or any external system — input is plain text only.
- Does not retain input — backend is stateless, every session is independent.

---

## Constraints
- No agent receives raw chat history — only original input + prior agent's structured output.
- No claim without verbatim quote (Agent 2 gate).
- FM-00 is a valid, encouraged outcome — not a fallback to avoid.
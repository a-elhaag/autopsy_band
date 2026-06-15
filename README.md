# Autopsy Band

Forensic 6-agent council that diagnoses **why** an AI build failed — at the
decision/spec level, not the code. Classifies input against a 17-mode failure
taxonomy and emits a Markdown Autopsy Report. See [agent.md](agent.md) for the design.

## Stack
- **Backend:** FastAPI, Jinja2 + HTMX (server-rendered, no JS build).
- **Model provider:** OpenRouter (OpenAI-compatible) via `app/model_client.py`.
  Provider-agnostic — a Foundry/Azure backend can slot in behind the same call.
- **Inter-agent transport:** **Band SDK** (`thenvoi`). The 6 agents run as
  distributed Band agents in one chat room; each agent.md handoff is a Band
  message carrying the diagnosis as structured `metadata`, routed by @mention.
  An in-process orchestrator runs the identical stage logic as a fallback/demo
  path so the app works without Band creds.

## Pipeline
```
Annotator → Verifier → (ConfidenceScorer ‖ Reconstructor) → Apex → Escalation
```
The Verifier's invariant — *no claim survives without a quote that is
verbatim-present in the input* — is enforced in code (`pipeline/verifier_gate.py`),
not just by the model. No validated claims → **FM-00** (a high-accuracy result,
not a failure).

## Run
```bash
cp .env.example .env          # set OPENROUTER_API_KEY
uv sync --extra dev
uv run uvicorn app.main:app --reload
# open http://localhost:8000
```

## Run on Band (real multi-agent transport)
```bash
uv sync --extra dev --extra band
# Register 6 agents on app.band.ai, add all to one chat room.
cp agent_config.example.yaml agent_config.yaml   # fill in UUIDs + keys
# In .env: BAND_ENABLED=1, BAND_CHAT_ID=..., BAND_INITIATOR_API_KEY=...,
#          THENVOI_REST_URL/THENVOI_WS_URL
uv run python -m app.band.run        # terminal 1: council process (6 Band agents)
uv run uvicorn app.main:app --reload # terminal 2: web app submits to the room
```
Handoff order on the bus:
`Annotator → Verifier → ConfidenceScorer → Reconstructor → ApexSynthesizer → HumanEscalation`.
(Scorer/Reconstructor are linearized over the bus — both depend only on
`validated_claims`, so it's data-equivalent to agent.md's parallel fan-out.)
HumanEscalation writes the final report to the result store; the web app polls it.

## Test
```bash
uv run pytest
```
16 tests: verifier gate, taxonomy loader, in-process end-to-end, and the Band
stage-graph step logic. Model client stubbed — no API key or Band creds needed.

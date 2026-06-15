from app.pipeline import verifier_gate

ORIGINAL = "PROMPT: build a CRM that does everything for everyone.\nOUTPUT: here is a full app."


def test_verbatim_quote_survives():
    claims = [{"failure_mode_id": "FM-02", "quote": "build a CRM that does everything"}]
    out = verifier_gate.gate(claims, ORIGINAL)
    assert len(out) == 1
    assert out[0]["validated"] is True


def test_whitespace_insensitive():
    claims = [{"failure_mode_id": "FM-02", "quote": "build a CRM   that does\neverything"}]
    assert len(verifier_gate.gate(claims, ORIGINAL)) == 1


def test_paraphrase_is_dropped():
    claims = [{"failure_mode_id": "FM-12", "quote": "the model invented a database"}]
    assert verifier_gate.gate(claims, ORIGINAL) == []


def test_missing_quote_dropped():
    assert verifier_gate.gate([{"failure_mode_id": "FM-01"}], ORIGINAL) == []


def test_case_insensitive():
    claims = [{"failure_mode_id": "FM-02", "quote": "BUILD A CRM"}]
    assert len(verifier_gate.gate(claims, ORIGINAL)) == 1

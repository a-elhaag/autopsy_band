from app.taxonomy import loader


def test_all_18_modes_present():
    ids = {m["id"] for m in loader.modes()}
    expected = {f"FM-{i:02d}" for i in range(0, 18)}
    assert ids == expected


def test_agents_only_see_id_name_definition():
    for m in loader.modes():
        assert set(m.keys()) == {"id", "name", "definition"}


def test_remediation_is_separate_and_complete():
    for m in loader.modes():
        assert loader.remediation_for(m["id"]), f"missing remediation for {m['id']}"


def test_category_lookup():
    assert loader.category_of("FM-12") == "Context & Execution"
    assert loader.category_of("FM-00") == "Null State"


def test_definitions_block_excludes_remediation():
    block = loader.definitions_block()
    assert "FM-00" in block
    # a remediation-only phrase must not leak into the agent-facing block
    assert "Provide more diagnostic signal" not in block

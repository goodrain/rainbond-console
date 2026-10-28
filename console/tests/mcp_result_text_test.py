import json

from console.services.mcp_result_text import render_result_text


def test_small_payload_is_unchanged():
    data = {"status": "ok", "total": 2}
    assert json.loads(render_result_text(data)) == data


def test_nested_lists_stay_valid_json_and_keep_totals():
    data = {
        "service": {"service_id": "s1"},
        "ports": {"items": [{"port": i, "note": "x" * 200} for i in range(40)], "total": 40},
        "envs": {"items": [{"name": f"E{i}", "value": "v" * 200} for i in range(40)], "total": 40},
    }
    text = render_result_text(data, max_chars=6000)
    assert len(text) <= 6000
    parsed = json.loads(text)
    assert parsed["ports"]["total"] == 40
    assert len(parsed["ports"]["items"]) < 40
    assert parsed["ports"]["_truncated"] is True
    assert parsed["envs"]["_dropped_items_count"] > 0


def test_paging_and_status_scalars_are_preserved():
    data = {
        "continue": "opaque-token",
        "status": "root_cause_confirmed",
        "total": 100,
        "resources": [{"resource": f"r{i}", "note": "x" * 120} for i in range(300)],
    }
    parsed = json.loads(render_result_text(data, max_chars=4000))
    assert parsed["continue"] == "opaque-token"
    assert parsed["status"] == "root_cause_confirmed"
    assert parsed["total"] == 100
    assert len(parsed["resources"]) < 300


def test_original_payload_is_not_mutated():
    data = {"items": [{"note": "x" * 500} for _ in range(100)]}
    render_result_text(data, max_chars=3000)
    assert len(data["items"]) == 100
    assert all(len(item["note"]) == 500 for item in data["items"])


def test_long_strings_are_cut_inside_the_value():
    data = {"logs": "L" * 40_000}
    text = render_result_text(data, max_chars=6000)
    assert len(text) <= 6000
    parsed = json.loads(text)
    assert "truncated" in parsed["logs"]
    assert parsed["logs"].startswith("LLLL")

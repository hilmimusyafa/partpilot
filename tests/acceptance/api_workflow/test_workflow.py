from copy import deepcopy
import pytest
from doubles import extraction
from helpers import BASE, answer_request, create, error, open_question, poll, post, success


def waiting(rig, *, conflicts=()):
    create(rig)
    rig.llm.script = [extraction(missing=() if conflicts else ["nameplate"], conflicts=conflicts)]
    rig.step()
    data = poll(rig)
    assert data["business_status"] == "NEEDS_CLARIFICATION"
    assert data["jobs"][-1]["status"] == "suspended_waiting_input"
    assert data["version"] > 1
    return data


def test_missing_info_suspends_and_idle_worker_is_noop(rig):
    data = waiting(rig)
    _, q = open_question(data)
    assert q["condition_kind"] == "MISSING_USER_INFO" and q["target_attribute"] == "nameplate"
    before = rig.repo.snapshot()
    calls = len(rig.llm.calls)
    rig.step()
    assert rig.repo.snapshot() == before and len(rig.llm.calls) == calls


def test_knowledge_gap_goes_direct_to_manual_review(rig):
    create(rig)
    rig.llm.script = [extraction(gap=True)]
    rig.step()
    data = poll(rig)
    assert data["business_status"] == data["lines"][0]["business_status"] == "MANUAL_REVIEW"
    assert not [q for q in data["lines"][0]["questions"] if q["status"] == "open"]
    assert data["lines"][0]["match"]["match_status"] != "matched"
    calls = len(rig.llm.calls)
    rig.step()
    assert len(rig.llm.calls) == calls


def test_conflict_is_visible_not_silently_matched(rig):
    data = waiting(rig, conflicts=["SYN text voltage conflicts with observed label"])
    line, q = open_question(data)
    assert q["condition_kind"] == "CONFLICTING_INFO"
    assert "SYN text voltage conflicts with observed label" in line["match"]["conflicts"]
    assert line["match"]["match_status"] != "matched"


def test_answer_replay_precedes_version_check_and_resumes_once(rig):
    data = waiting(rig)
    path, body = answer_request(data)
    original = post(rig, path, body, "SYN-answer-0001")
    accepted = success(original, 202)
    assert accepted["version"] == data["version"] + 1
    assert len(rig.repo.snapshot()["answers"]) == 1
    assert any(j["status"] == "queued" for j in accepted["jobs"])
    rig.llm.script = [extraction(gap=True)]
    rig.step()
    latest = poll(rig)
    assert latest["business_status"] == "MANUAL_REVIEW"
    assert rig.llm.calls[-1]["answers"] and body["answer_text"] in repr(rig.llm.calls[-1]["answers"])
    before = rig.repo.snapshot()
    replay = post(rig, path, body, "SYN-answer-0001")
    assert replay.status_code == 202 and replay.json() == original.json()
    assert replay.headers["idempotency-replayed"].lower() == "true"
    assert rig.repo.snapshot() == before


def test_answer_expected_version_conflict(rig):
    data = waiting(rig)
    path, body = answer_request(data)
    body["expected_version"] = data["version"] - 1
    before = rig.repo.snapshot()
    result = error(post(rig, path, body, "SYN-stale-0001"), 409, "VERSION_CONFLICT")
    assert result["current_version"] == data["version"]
    for n in ("work_orders", "jobs", "answers"):
        assert rig.repo.snapshot()[n] == before[n]


@pytest.mark.parametrize("field", ["question_id", "session_id", "turn_number", "parent"])
def test_answer_wrong_relationship_rejected_without_effect(rig, field):
    data = waiting(rig)
    path, body = answer_request(data)
    if field == "parent":
        path = path.replace("SYN-WO-001", "SYN-missing")
    else:
        body[field] = 2 if field == "turn_number" else "SYN-missing"
    before = rig.repo.snapshot()
    response = post(rig, path, body, "SYN-wrong-0001")
    assert response.status_code in {404, 409}, response.text
    error(response, response.status_code, "NOT_FOUND" if response.status_code == 404 else "INVALID_STATE")
    for n in ("work_orders", "jobs", "answers"):
        assert rig.repo.snapshot()[n] == before[n]


def test_answer_commit_failure_preserves_open_question(rig):
    data = waiting(rig)
    path, body = answer_request(data)
    before = rig.repo.snapshot()
    rig.repo.fail_commit = True
    error(post(rig, path, body, "SYN-answer-0001"), 503, "SERVICE_UNAVAILABLE", retryable=True)
    assert rig.repo.snapshot() == before
    rig.repo.fail_commit = False
    success(post(rig, path, body, "SYN-answer-0001"), 202)
    assert len(rig.repo.snapshot()["answers"]) == 1


def test_answer_key_conflict_and_answered_ticket_cannot_enqueue_again(rig):
    data = waiting(rig)
    path, body = answer_request(data)
    accepted = success(post(rig, path, body, "SYN-answer-0001"), 202)
    before = rig.repo.snapshot()
    different = dict(body, answer_text="SYN changed answer")
    error(post(rig, path, different, "SYN-answer-0001"), 409, "IDEMPOTENCY_CONFLICT")
    body["expected_version"] = accepted["version"]
    error(post(rig, path, body, "SYN-answer-0002"), 409, "INVALID_STATE")
    for n in ("work_orders", "jobs", "answers"):
        assert rig.repo.snapshot()[n] == before[n]


def test_three_distinct_turns_then_manual_review_no_fourth(rig):
    data = waiting(rig)
    attributes = ["nameplate", "mounting", "voltage"]
    session_ids, question_ids = set(), set()
    for turn, attribute in enumerate(attributes, 1):
        _, q = open_question(data)
        assert q["turn_number"] == turn and q["target_attribute"] == attribute
        session_ids.add(q["session_id"])
        question_ids.add(q["question_id"])
        path, body = answer_request(data, f"SYN answer for {attribute}")
        success(post(rig, path, body, f"SYN-answer-{turn:04d}"), 202)
        rig.llm.script = [extraction(missing=[attributes[turn] if turn < 3 else "oil_seal"])]
        rig.step()
        data = poll(rig)
    assert len(session_ids) == 1 and len(question_ids) == 3
    assert data["business_status"] == "MANUAL_REVIEW"
    assert len(rig.repo.snapshot()["answers"]) == 3
    assert not [q for q in data["lines"][0]["questions"] if q["status"] == "open"]
    calls = len(rig.llm.calls)
    rig.step()
    assert len(rig.llm.calls) == calls


def test_already_answered_attribute_not_asked_again(rig):
    data = waiting(rig)
    path, body = answer_request(data)
    success(post(rig, path, body, "SYN-answer-0001"), 202)
    rig.llm.script = [extraction(missing=["nameplate", "mounting"])]
    rig.step()
    data = poll(rig)
    assert all(q["target_attribute"] != "nameplate" for q in data["lines"][0]["questions"] if q["status"] == "open")


@pytest.mark.parametrize("mode", ["active", "manual"])
def test_match_cannot_duplicate_active_job_or_bypass_review(rig, mode):
    data = create(rig)
    if mode == "manual":
        rig.llm.script = [extraction(gap=True)]
        rig.step()
        data = poll(rig)
    line = data["lines"][0]
    path = f"{BASE}/{data['work_order_id']}/parts/{line['wo_part_id']}/match"
    before = rig.repo.snapshot()
    error(post(rig, path, {"expected_version": data["version"]}, "SYN-rematch-001"), 409, "INVALID_STATE")
    for n in ("work_orders", "jobs", "answers"):
        assert rig.repo.snapshot()[n] == before[n]


@pytest.mark.parametrize("failure", ["timeout", "invalid", "tool"])
def test_llm_failure_bounded_no_fabricated_success(rig, failure):
    create(rig)
    value = {"timeout": TimeoutError("SYN-timeout"), "invalid": "SYN-not-json",
             "tool": {"tool_calls": [{"name": "raw_sql", "arguments": "SYN-forbidden"}]}}[failure]
    rig.llm.script = [deepcopy(value) for _ in range(10)]
    # A finite worker tick must perform at most one call + two transport retries.
    rig.step()
    data = poll(rig)
    assert 1 <= len(rig.llm.calls) <= 3
    assert all(j["status"] in {"failed", "exhausted"} for j in data["jobs"])
    assert all(j["last_error_code"] for j in data["jobs"])
    assert data["business_status"] not in {"READY_FOR_FULFILLMENT", "DONE", "FULFILLED"}
    assert data["lines"][0]["match"]["match_status"] not in {"matched", "confirmed"}
    assert not data["lines"][0]["approval_ids"] and not data["lines"][0]["handoff_ids"]
    calls = len(rig.llm.calls)
    rig.step()
    assert len(rig.llm.calls) == calls


def test_multiline_manual_review_aggregate_wins(rig):
    from helpers import intake_body
    body = intake_body()
    body["parts_requested"].append(dict(body["parts_requested"][0], line_number=2))
    create(rig, body)
    rig.llm.script = [extraction(missing=["nameplate"]), extraction(gap=True)]
    # run_once claims at most one queued job; intake may enqueue per-line or per-WO.
    for _ in range(2):
        rig.step()
    data = poll(rig)
    assert {line["business_status"] for line in data["lines"]} == {"NEEDS_CLARIFICATION", "MANUAL_REVIEW"}
    assert data["business_status"] == "MANUAL_REVIEW"

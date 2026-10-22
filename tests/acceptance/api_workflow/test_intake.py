from copy import deepcopy
from decimal import Decimal
import pytest
from helpers import BASE, create, error, intake_body, poll, post, success


def test_multiline_atomic_acceptance(rig):
    body = intake_body()
    body["parts_requested"].append({"line_number": 2, "requested_text": "SYN second unknown motor", "qty_needed": "1.250", "uom": "PCS"})
    data = create(rig, body)
    assert data["version"] == 1 and data["business_status"] == "RECEIVED"
    assert [line["line_number"] for line in data["lines"]] == [1, 2]
    assert len({line["wo_part_id"] for line in data["lines"]}) == 2
    assert data["jobs"] and all(j["status"] == "queued" for j in data["jobs"])
    snapshot = rig.repo.snapshot()
    assert len(snapshot["work_orders"]) == 1 and snapshot["jobs"] and len(snapshot["idempotency"]) == 1
    # Stored model shape is free, but exact quantities must survive in repository.
    stored = repr(snapshot["work_orders"])
    assert "0.100" in stored and "1.250" in stored
    assert rig.llm.calls == []
    assert poll(rig) == data


@pytest.mark.parametrize("qty", ["0.001", "0.100", "1", "100.999"])
def test_positive_decimal_string(rig, qty):
    body = intake_body()
    body["parts_requested"][0]["qty_needed"] = qty
    create(rig, body)
    assert str(Decimal(qty)) in repr(rig.repo.snapshot()["work_orders"])


@pytest.mark.parametrize("qty", ["0", "0.000", "-1", "1.0001", "1e2", "NaN", ".1", "01", 0.1])
def test_invalid_decimal_rolls_back(rig, qty):
    body = intake_body()
    body["parts_requested"][0]["qty_needed"] = qty
    before = rig.repo.snapshot()
    error(post(rig, BASE, body), 422, "VALIDATION_ERROR")
    assert rig.repo.snapshot() == before


@pytest.mark.parametrize("defect", ["duplicate", "empty", "too_many", "asset", "site", "warehouse", "extra"])
def test_invalid_intake_no_partial_write(rig, defect):
    body = intake_body()
    if defect == "duplicate":
        body["parts_requested"] *= 2
    elif defect == "empty":
        body["parts_requested"] = []
    elif defect == "too_many":
        body["parts_requested"] = [dict(body["parts_requested"][0], line_number=i) for i in range(1, 52)]
    elif defect == "extra":
        body["org_id"] = "SYN-forged"
    else:
        body[{"asset": "asset_id", "site": "site_id", "warehouse": "target_warehouse_id"}[defect]] = "SYN-missing"
    before = rig.repo.snapshot()
    error(post(rig, BASE, body), 422, "VALIDATION_ERROR")
    assert rig.repo.snapshot() == before


def test_missing_key_is_400(rig):
    before = rig.repo.snapshot()
    error(rig.client.post(BASE, json=intake_body()), 400, "CONTEXT_REJECTED")
    assert rig.repo.snapshot() == before


def test_replay_returns_initial_snapshot_without_new_effect(rig):
    response = post(rig, BASE, intake_body())
    success(response, 202)
    before = rig.repo.snapshot()
    replay = post(rig, BASE, intake_body())
    assert replay.status_code == 202 and replay.json() == response.json()
    assert replay.headers["idempotency-replayed"].lower() == "true"
    assert rig.repo.snapshot() == before


def test_key_payload_conflict(rig):
    create(rig)
    before = rig.repo.snapshot()
    body = intake_body()
    body["priority"] = 2
    error(post(rig, BASE, body), 409, "IDEMPOTENCY_CONFLICT")
    for namespace in ("work_orders", "jobs", "answers"):
        assert rig.repo.snapshot()[namespace] == before[namespace]


def test_enqueue_commit_failure_is_503_then_same_key_can_retry(rig):
    before = rig.repo.snapshot()
    rig.repo.fail_commit = True
    error(post(rig, BASE, intake_body()), 503, "SERVICE_UNAVAILABLE", retryable=True)
    assert rig.repo.snapshot() == before
    rig.repo.fail_commit = False
    create(rig)
    assert len(rig.repo.snapshot()["idempotency"]) == 1


def test_poll_is_readonly_and_missing_is_404(rig):
    create(rig)
    before = rig.repo.snapshot()
    assert poll(rig) == poll(rig)
    error(rig.client.get(BASE + "/SYN-missing"), 404, "NOT_FOUND")
    assert rig.repo.snapshot() == before


def test_unwired_live_repository_fails_closed(rig):
    # Default factory must never silently replace missing live persistence with RAM.
    from fastapi.testclient import TestClient
    from partpilot.app import create_app
    app = create_app(repository=None, erp=rig.erp, llm=rig.llm)
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 55001)) as client:
        response = client.post(BASE, json=intake_body(), headers={"Idempotency-Key": "SYN-unwired-001"})
        error(response, 503, "SERVICE_UNAVAILABLE", retryable=True)

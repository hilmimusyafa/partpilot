from copy import deepcopy
import re
import json
from pathlib import Path
import subprocess

SCHEMA_PYTHON = "/srv/apps/hermes/hermes-agent/venv/bin/python3"


def validate_wire(name, body):
    command = [SCHEMA_PYTHON, "-B", str(Path(__file__).with_name("schema_check.py")), name]
    result = subprocess.run(command, input=json.dumps(body), text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr

BASE = "/api/v1/work-orders"
BUSINESS = {"RECEIVED", "EXTRACTING", "NEEDS_CLARIFICATION", "MANUAL_REVIEW",
            "MAPPING_PROPOSED", "READY_FOR_FULFILLMENT", "RESERVED_LOCAL", "TRANSFER_PLANNED",
            "IN_TRANSIT", "PROCUREMENT_REQUESTED", "FULFILLED", "DONE", "CANCELLED"}
JOBS = {"queued", "running", "succeeded", "suspended_waiting_input", "failed", "exhausted"}


def intake_body(wo="SYN-WO-001"):
    return {"work_order_id": wo, "asset_id": "SYN-ASSET-001", "site_id": "SYN-SITE-A",
            "target_warehouse_id": "SYN-WH-A", "maintenance_type": "corrective", "priority": 1,
            "parts_requested": [{"line_number": 1, "requested_text": "SYN synthetic motor needs identification",
                                 "qty_needed": "0.100", "uom": "PCS"}], "claimed_actor": "SYN-UI-operator"}


def post(rig, path, body, key="SYN-intake-0001"):
    return rig.client.post(path, json=deepcopy(body), headers={"Idempotency-Key": key})


def success(response, status=200):
    assert response.status_code == status, response.text
    result = response.json()
    validate_wire("WorkOrderResult", result)
    assert set(result) == {"status", "data", "request_id"}
    assert result["status"] == "success"
    assert re.fullmatch(r"SYN-[A-Za-z0-9_.:-]{1,96}", result["request_id"])
    assert response.headers["x-request-id"] == result["request_id"]
    data = result["data"]
    assert set(data) == {"work_order_id", "version", "business_status", "org_id", "site_id",
                         "target_warehouse_id", "lines", "jobs", "updated_at"}
    assert type(data["version"]) is int and data["version"] >= 1
    assert data["org_id"] == "00000000-0000-0000-0000-000000000001"
    assert data["business_status"] in BUSINESS
    for line in data["lines"]:
        assert line["business_status"] in BUSINESS
        assert set(line) == {"wo_part_id", "line_number", "business_status", "match", "questions",
                             "selected_proposal_id", "approval_ids", "handoff_ids"}
        assert line["approval_ids"] == line["handoff_ids"] == []
        for q in line["questions"]:
            assert set(q) == {"question_id", "session_id", "turn_number", "condition_kind",
                              "target_attribute", "question_text", "status"}
            assert 1 <= q["turn_number"] <= 3
            assert q["status"] in {"open", "answered", "escalated"}
    for job in data["jobs"]:
        assert set(job) == {"job_id", "status", "retry_count", "last_error_code"}
        assert job["status"] in JOBS
        assert type(job["retry_count"]) is int and 0 <= job["retry_count"] <= 3
    return data


def error(response, status, code, retryable=False):
    assert response.status_code == status, response.text
    body = response.json()
    validate_wire("Error", body)
    assert set(body) == {"status", "error_code", "message", "request_id", "retryable", "current_version"}
    assert body["status"] == "error" and body["error_code"] == code
    assert body["retryable"] is retryable
    assert re.fullmatch(r"SYN-[A-Za-z0-9_.:-]{1,96}", body["request_id"])
    assert not any(t in response.text.lower() for t in ("traceback", "postgres://", "password=", "dsn="))
    return body


def create(rig, body=None, key="SYN-intake-0001"):
    return success(post(rig, BASE, body or intake_body(), key), 202)


def poll(rig, wo="SYN-WO-001"):
    response = rig.client.get(f"{BASE}/{wo}")
    assert response.headers.get("cache-control") == "no-store"
    return success(response)


def open_question(data):
    line = data["lines"][0]
    questions = [q for q in line["questions"] if q["status"] == "open"]
    assert len(questions) == 1
    return line, questions[0]


def answer_request(data, text="SYN observed answer"):
    line, q = open_question(data)
    path = f"{BASE}/{data['work_order_id']}/parts/{line['wo_part_id']}/clarifications/answer"
    body = {"expected_version": data["version"], "question_id": q["question_id"],
            "session_id": q["session_id"], "turn_number": q["turn_number"], "answer_text": text}
    return path, body

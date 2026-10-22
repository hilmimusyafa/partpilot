"""FastAPI application entrypoint for PartPilot Backend Bundle v3."""

import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional
import asyncio
import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Install synchronous bridge on httpx.ASGITransport for httpx.Client compatibility (httpx >=0.28)
if not hasattr(httpx.ASGITransport, "_sync_bridge_installed"):
    httpx.ASGITransport.__enter__ = lambda self: self
    httpx.ASGITransport.__exit__ = lambda self, *args: None

    def _sync_handle_request(self: Any, request: Any) -> Any:
        async def _do() -> Any:
            res = await self.handle_async_request(request)
            body = await res.aread()
            return res, body

        res, body = asyncio.run(_do())
        res.stream = httpx.ByteStream(body)
        return res

    httpx.ASGITransport.handle_request = _sync_handle_request
    httpx.ASGITransport._sync_bridge_installed = True


from backend.wo.availability import evaluate_availability
from backend.wo.economics import evaluate_disruption
from backend.wo.models import (
    AnswersInput,
    AvailabilityInput,
    AvailabilityResult,
    CompanyPage,
    DisruptionInput,
    DisruptionResult,
    DraftCreate,
    DraftUpdate,
    ErrorEnvelope,
    MachinePage,
    ProductionLinePage,
    SafeError,
    Session,
    SitePage,
    StationPage,
    VersionInput,
    WarehousePage,
)
from backend.wo.repository import (
    RepositoryError,
    create_draft as repo_create_draft,
    get_session as repo_get_session,
    list_companies,
    list_machines,
    list_production_lines,
    list_sites,
    list_stations,
    list_warehouses,
    retry_work_order as repo_retry_work_order,
    submit_answers as repo_submit_answers,
    submit_draft as repo_submit_draft,
    update_draft as repo_update_draft,
)

app = FastAPI(
    title="PartPilot Backend Bundle v3 API",
    version="backend-bundle-v3",
    openapi_url="/api/v1/openapi.json",
    docs_url=None,
    redoc_url=None,
)

from backend.procurement.router import router as procurement_router
app.include_router(procurement_router)


def make_error_response(status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None, retriable: bool = False) -> JSONResponse:
    req_id = str(uuid.uuid4())
    content = {
        "error": {
            "code": code,
            "message": message,
            "retriable": retriable,
            "details": details or {},
        },
        "request_id": req_id,
    }
    return JSONResponse(status_code=status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    msg = "; ".join([f"{e.get('loc')}: {e.get('msg')}" for e in errors])
    code = "invalid_fields"
    for e in errors:
        loc = e.get("loc", ())
        if "cost_id" in loc or "evidence_ref" in loc:
            code = "duplicate_cost"
            break
        if "value" in loc and ("decimal" in str(e.get("msg")) or "numeric" in str(e.get("msg")) or "string" in str(e.get("msg"))):
            code = "numeric_range"
            break
    safe_errors = [
        {"loc": list(e.get("loc", ())), "msg": str(e.get("msg", "")), "type": str(e.get("type", ""))}
        for e in errors
    ]
    return make_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, code=code, message=msg, details={"validation_errors": safe_errors})



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return make_error_response(exc.status_code, code=exc.detail["code"], message=exc.detail.get("message", "Error"), details=exc.detail.get("details"))
    return make_error_response(exc.status_code, code="http_error", message=str(exc.detail))


@app.exception_handler(RepositoryError)
async def repository_exception_handler(request: Request, exc: RepositoryError) -> JSONResponse:
    return make_error_response(exc.status_code, code=exc.code, message=exc.message, details=exc.details)


def canonical_hash(obj: Any) -> str:
    """Compute deterministic SHA-256 hash of JSON-serializable object."""
    dumped = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------
# Work Order Routes
# ----------------------------------------------------------------------

@app.post("/api/v1/work-orders", status_code=status.HTTP_201_CREATED, response_model=Session)
async def create_draft(
    draft: DraftCreate,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Any:
    # Path traversal check on warehouse_id
    if draft.warehouse_id and (".." in draft.warehouse_id or "/" in draft.warehouse_id or "\\" in draft.warehouse_id):
        return make_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_warehouse", "Warehouse ID cannot contain path traversal characters")

    explicit_nulls = {
        field for field in ("site_id", "production_line_id", "station_id", "machine_id")
        if field in draft.model_fields_set and getattr(draft, field) is None
    }
    # Ancestry hierarchy validation (test_h02): explicit null ancestor with non-null descendant
    if "site_id" in explicit_nulls and (draft.production_line_id is not None or draft.station_id is not None or draft.machine_id is not None):
        return make_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "context_ancestry_mismatch", "Explicit null site_id with non-null descendant")
    if "production_line_id" in explicit_nulls and (draft.station_id is not None or draft.machine_id is not None):
        return make_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "context_ancestry_mismatch", "Explicit null production_line_id with non-null descendant")
    if "station_id" in explicit_nulls and draft.machine_id is not None:
        return make_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "context_ancestry_mismatch", "Explicit null station_id with non-null machine_id")

    status_code, res_data, is_replay = repo_create_draft(draft.model_dump(), idempotency_key=idempotency_key, explicit_nulls=explicit_nulls)
    response.status_code = status_code
    if is_replay:
        response.headers["Idempotent-Replay"] = "true"
        response.headers["X-Idempotent-Replay"] = "true"
    return res_data


@app.patch("/api/v1/work-orders/{session_id}", response_model=Session)
async def update_draft(
    session_id: str,
    update: DraftUpdate,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Any:
    explicit_nulls = {
        field for field in ("site_id", "production_line_id", "station_id", "machine_id")
        if field in update.model_fields_set and getattr(update, field) is None
    }
    status_code, res_data, is_replay = repo_update_draft(
        session_id,
        update.model_dump(exclude_unset=True),
        idempotency_key=idempotency_key,
        explicit_nulls=explicit_nulls,
    )
    response.status_code = status_code
    if is_replay:
        response.headers["Idempotent-Replay"] = "true"
        response.headers["X-Idempotent-Replay"] = "true"
    return res_data


@app.get("/api/v1/work-orders/{session_id}", response_model=Session)
async def get_session(session_id: str) -> Any:
    session = repo_get_session(session_id)
    if not session:
        return make_error_response(status.HTTP_404_NOT_FOUND, "session_not_found", f"Session {session_id} not found")
    return session


@app.post("/api/v1/work-orders/{session_id}/submit", status_code=status.HTTP_202_ACCEPTED, response_model=Session)
async def submit_work_order(
    session_id: str,
    body: VersionInput,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Any:
    status_code, res_data, is_replay = repo_submit_draft(
        session_id,
        body.expected_version,
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    response.headers["Location"] = f"/api/v1/work-orders/{session_id}"
    if is_replay:
        response.headers["Idempotent-Replay"] = "true"
        response.headers["X-Idempotent-Replay"] = "true"
    return res_data


@app.post("/api/v1/work-orders/{session_id}/answers", status_code=status.HTTP_202_ACCEPTED, response_model=Session)
async def submit_answers(
    session_id: str,
    answers_input: AnswersInput,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Any:
    answers_list = [a.model_dump() for a in answers_input.answers]
    status_code, res_data, is_replay = repo_submit_answers(
        session_id,
        answers_input.expected_version,
        answers_list,
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    response.headers["Location"] = f"/api/v1/work-orders/{session_id}"
    if is_replay:
        response.headers["Idempotent-Replay"] = "true"
        response.headers["X-Idempotent-Replay"] = "true"
    return res_data


@app.post("/api/v1/work-orders/{session_id}/retry", status_code=status.HTTP_202_ACCEPTED, response_model=Session)
async def retry_work_order(
    session_id: str,
    version_input: VersionInput,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Any:
    status_code, res_data, is_replay = repo_retry_work_order(
        session_id,
        version_input.expected_version,
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    response.headers["Location"] = f"/api/v1/work-orders/{session_id}"
    if is_replay:
        response.headers["Idempotent-Replay"] = "true"
        response.headers["X-Idempotent-Replay"] = "true"
    return res_data


# ----------------------------------------------------------------------
# Reference Routes
# ----------------------------------------------------------------------

@app.get("/api/v1/companies", response_model=CompanyPage)
async def get_companies(cursor: Optional[str] = None, limit: int = 100) -> Any:
    items, next_cursor = list_companies(cursor=cursor, limit=limit)
    return {"items": [i.model_dump() for i in items], "next_cursor": next_cursor}


@app.get("/api/v1/warehouses", response_model=WarehousePage)
async def get_warehouses(company_id: str = Query(...), cursor: Optional[str] = None, limit: int = 100) -> Any:
    items, next_cursor = list_warehouses(company_id=company_id, cursor=cursor, limit=limit)
    return {"items": [i.model_dump() for i in items], "next_cursor": next_cursor}


@app.get("/api/v1/sites", response_model=SitePage)
async def get_sites(company_id: str = Query(...), cursor: Optional[str] = None, limit: int = 100) -> Any:
    items, next_cursor = list_sites(company_id=company_id, cursor=cursor, limit=limit)
    return {"items": [i.model_dump() for i in items], "next_cursor": next_cursor}


@app.get("/api/v1/production-lines", response_model=ProductionLinePage)
async def get_production_lines(company_id: str = Query(...), site_id: str = Query(...), cursor: Optional[str] = None, limit: int = 100) -> Any:
    items, next_cursor = list_production_lines(company_id=company_id, site_id=site_id, cursor=cursor, limit=limit)
    return {"items": [i.model_dump() for i in items], "next_cursor": next_cursor}


@app.get("/api/v1/stations", response_model=StationPage)
async def get_stations(company_id: str = Query(...), site_id: str = Query(...), production_line_id: str = Query(...), cursor: Optional[str] = None, limit: int = 100) -> Any:
    items, next_cursor = list_stations(company_id=company_id, site_id=site_id, production_line_id=production_line_id, cursor=cursor, limit=limit)
    return {"items": [i.model_dump() for i in items], "next_cursor": next_cursor}


@app.get("/api/v1/machines", response_model=MachinePage)
async def get_machines(
    company_id: str = Query(...),
    site_id: str = Query(...),
    production_line_id: str = Query(...),
    station_id: str = Query(...),
    cursor: Optional[str] = None,
    limit: int = 100,
) -> Any:
    items, next_cursor = list_machines(company_id=company_id, site_id=site_id, production_line_id=production_line_id, station_id=station_id, cursor=cursor, limit=limit)
    return {"items": [i.model_dump() for i in items], "next_cursor": next_cursor}


# ----------------------------------------------------------------------
# Availability & Economics Routes
# ----------------------------------------------------------------------

@app.post("/api/v1/availability/evaluate", response_model=AvailabilityResult)
async def evaluate_availability_endpoint(body: AvailabilityInput) -> Any:
    session_data = repo_get_session(body.session_id)
    if not session_data:
        return make_error_response(status.HTTP_404_NOT_FOUND, "reference_not_found", f"Session {body.session_id} not found")

    session = Session(**session_data)
    if session.version != body.expected_version:
        return make_error_response(status.HTTP_409_CONFLICT, "version_conflict", f"Expected version {body.expected_version} does not match current {session.version}")

    if session.state != "identified":
        return make_error_response(status.HTTP_409_CONFLICT, "identity_not_established", f"Session is in state {session.state}; availability requires identified state")

    result = evaluate_availability(session)
    return result.model_dump()


@app.post("/api/v1/disruption/evaluate", response_model=DisruptionResult)
async def evaluate_disruption_endpoint(body: DisruptionInput) -> Any:
    try:
        result = evaluate_disruption(body)
        return result.model_dump()
    except ValueError as ve:
        err_msg = str(ve)
        code = "duplicate_cost" if "duplicate" in err_msg.lower() else "invalid_schedule"
        return make_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, code=code, message=err_msg)

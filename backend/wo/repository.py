"""Repository layer for PartPilot Backend Bundle v3.
Provides isolated PostgreSQL persistence, scoped candidate queries, session lifecycle,
events append-only tracking, distributed job claiming, and idempotency replay.
"""

import base64
import hashlib
import json
import os
import re
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import psycopg
from psycopg.rows import dict_row

from backend.wo.models import (
    Candidate,
    Company,
    Fact,
    KnowledgeRef,
    Machine,
    ProductionLine,
    Question,
    SafeError,
    Session,
    Site,
    Station,
    Warehouse,
)


def _observe_boundary(name: str, context: Dict[str, Any]) -> None:
    """Production no-op boundary hook. Private test harnesses monkeypatch this."""
    pass


class RepositoryError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ReferenceNotFoundError(RepositoryError):
    def __init__(self, message: str = "Reference not found"):
        super().__init__("reference_not_found", message, status_code=404)


class ContextAncestryMismatchError(RepositoryError):
    def __init__(self, message: str = "Context ancestry mismatch"):
        super().__init__("context_ancestry_mismatch", message, status_code=422)


class MachineContextUnavailableError(RepositoryError):
    def __init__(self, message: str = "Machine context unavailable"):
        super().__init__("machine_context_unavailable", message, status_code=422)


class InvalidProductionContextError(RepositoryError):
    def __init__(self, message: str = "Invalid production context"):
        super().__init__("invalid_production_context", message, status_code=422)


class IncompleteProductionContextError(RepositoryError):
    def __init__(self, message: str = "Incomplete production context"):
        super().__init__("incomplete_production_context", message, status_code=422)


class InvalidWarehouseError(RepositoryError):
    def __init__(self, message: str = "Invalid warehouse"):
        super().__init__("invalid_warehouse", message, status_code=422)


class InvalidCursorError(RepositoryError):
    def __init__(self, message: str = "Invalid cursor"):
        super().__init__("invalid_cursor", message, status_code=422)


class IdempotencyConflictError(RepositoryError):
    def __init__(self, message: str = "Idempotency-Key reused with different payload"):
        super().__init__("idempotency_conflict", message, status_code=409)


class VersionConflictError(RepositoryError):
    def __init__(self, message: str = "Version conflict"):
        super().__init__("version_conflict", message, status_code=409)


class StateConflictError(RepositoryError):
    def __init__(self, message: str = "State conflict"):
        super().__init__("state_conflict", message, status_code=409)


class RetriesExhaustedError(RepositoryError):
    def __init__(self, message: str = "Max 2 explicit retry attempts per session"):
        super().__init__("retries_exhausted", message, status_code=409)


class QueueFullError(RepositoryError):
    def __init__(self, message: str = "Queue full"):
        super().__init__("queue_full", message, status_code=503)


class DependencyUnavailableError(RepositoryError):
    def __init__(self, message: str = "Database connection unavailable"):
        super().__init__("dependency_unavailable", message, status_code=503)


def get_test_db_url() -> str:
    """Retrieve database connection URL."""
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        secrets_file = os.path.expanduser("~/.config/partpilot/db.env")
        if os.path.exists(secrets_file):
            with open(secrets_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("TEST_DATABASE_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
    if not url:
        raise DependencyUnavailableError("Database URL not configured")
    return url


def get_db_connection() -> psycopg.Connection:
    """Open connection to PostgreSQL."""
    try:
        url = get_test_db_url()
        conn = psycopg.connect(url, connect_timeout=3, autocommit=False)
        return conn
    except Exception as exc:
        raise DependencyUnavailableError("Database connection unavailable") from None


def canonical_hash(obj: Any) -> str:
    """Compute deterministic SHA-256 hash of JSON-serializable object."""
    dumped = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def encode_cursor(family: str, filters: Dict[str, str], last_id: str) -> str:
    payload = {"family": family, "filters": filters, "last_id": last_id}
    return base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True).encode()).decode()


def decode_cursor(cursor: str, family: str, filters: Dict[str, str]) -> str:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(raw)
        if data.get("family") != family:
            raise ValueError("family mismatch")
        if data.get("filters") != filters:
            raise ValueError("filters mismatch")
        last_id = data.get("last_id")
        if not last_id:
            raise ValueError("missing last_id")
        return str(last_id)
    except Exception:
        raise InvalidCursorError("Invalid cursor token")


# ----------------------------------------------------------------------
# Reference Hierarchy Queries
# ----------------------------------------------------------------------

def list_companies(cursor: Optional[str] = None, limit: int = 100) -> Tuple[List[Company], Optional[str]]:
    filters: Dict[str, str] = {}
    last_id = decode_cursor(cursor, "companies", filters) if cursor else None
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                query = "SELECT name FROM erp.company"
                params: List[Any] = []
                if last_id:
                    query += " WHERE name > %s"
                    params.append(last_id)
                query += " ORDER BY name ASC LIMIT 101;"
                cur.execute(query, params)
                rows = cur.fetchall()
                truncated = len(rows) > 100
                items = [Company(id=r[0], name=r[0]) for r in rows[:100]]
                next_cursor = encode_cursor("companies", filters, items[-1].id) if truncated and items else None
                return items, next_cursor
    finally:
        conn.close()


def list_warehouses(company_id: str, cursor: Optional[str] = None, limit: int = 100) -> Tuple[List[Warehouse], Optional[str]]:
    filters = {"company_id": company_id}
    last_id = decode_cursor(cursor, "warehouses", filters) if cursor else None
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT name FROM erp.company WHERE name = %s;", (company_id,))
                if not cur.fetchone():
                    raise ReferenceNotFoundError(f"Company {company_id} not found")

                query = "SELECT name FROM erp.warehouse WHERE company = %s AND NOT disabled AND NOT is_group"
                params: List[Any] = [company_id]
                if last_id:
                    query += " AND name > %s"
                    params.append(last_id)
                query += " ORDER BY name ASC LIMIT 101;"
                cur.execute(query, params)
                rows = cur.fetchall()
                truncated = len(rows) > 100
                items = [Warehouse(id=r[0], name=r[0], company_id=company_id) for r in rows[:100]]
                next_cursor = encode_cursor("warehouses", filters, items[-1].id) if truncated and items else None
                return items, next_cursor
    finally:
        conn.close()


def list_sites(company_id: str, cursor: Optional[str] = None, limit: int = 100) -> Tuple[List[Site], Optional[str]]:
    filters = {"company_id": company_id}
    last_id = decode_cursor(cursor, "sites", filters) if cursor else None
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT name FROM erp.company WHERE name = %s;", (company_id,))
                if not cur.fetchone():
                    raise ReferenceNotFoundError(f"Company {company_id} not found")

                query = "SELECT id, name, company FROM pp.production_site WHERE company = %s AND active"
                params: List[Any] = [company_id]
                if last_id:
                    query += " AND id > %s"
                    params.append(last_id)
                query += " ORDER BY id ASC LIMIT 101;"
                cur.execute(query, params)
                rows = cur.fetchall()
                truncated = len(rows) > 100
                items = [Site(id=r[0], name=r[1], company_id=r[2]) for r in rows[:100]]
                next_cursor = encode_cursor("sites", filters, items[-1].id) if truncated and items else None
                return items, next_cursor
    finally:
        conn.close()


def list_production_lines(company_id: str, site_id: str, cursor: Optional[str] = None, limit: int = 100) -> Tuple[List[ProductionLine], Optional[str]]:
    filters = {"company_id": company_id, "site_id": site_id}
    last_id = decode_cursor(cursor, "production-lines", filters) if cursor else None
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT name FROM erp.company WHERE name = %s;", (company_id,))
                if not cur.fetchone():
                    raise ReferenceNotFoundError(f"Company {company_id} not found")

                cur.execute("SELECT id, company FROM pp.production_site WHERE id = %s;", (site_id,))
                site_row = cur.fetchone()
                if not site_row or site_row[1] != company_id:
                    raise ReferenceNotFoundError(f"Site {site_id} not found in company {company_id}")

                query = "SELECT id, name, company, site_id, production_scope FROM pp.production_line WHERE company = %s AND site_id = %s AND production_scope = 'AC' AND active"
                params: List[Any] = [company_id, site_id]
                if last_id:
                    query += " AND id > %s"
                    params.append(last_id)
                query += " ORDER BY id ASC LIMIT 101;"
                cur.execute(query, params)
                rows = cur.fetchall()
                truncated = len(rows) > 100
                items = [ProductionLine(id=r[0], name=r[1], company_id=r[2], site_id=r[3], production_scope=r[4]) for r in rows[:100]]
                next_cursor = encode_cursor("production-lines", filters, items[-1].id) if truncated and items else None
                return items, next_cursor
    finally:
        conn.close()


def list_stations(company_id: str, site_id: str, production_line_id: str, cursor: Optional[str] = None, limit: int = 100) -> Tuple[List[Station], Optional[str]]:
    filters = {"company_id": company_id, "site_id": site_id, "production_line_id": production_line_id}
    last_id = decode_cursor(cursor, "stations", filters) if cursor else None
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT name FROM erp.company WHERE name = %s;", (company_id,))
                if not cur.fetchone():
                    raise ReferenceNotFoundError(f"Company {company_id} not found")

                cur.execute("SELECT id, company, site_id FROM pp.production_line WHERE id = %s;", (production_line_id,))
                line_row = cur.fetchone()
                if not line_row or line_row[1] != company_id:
                    raise ReferenceNotFoundError(f"Production line {production_line_id} not found in company {company_id}")
                if line_row[2] != site_id:
                    raise ContextAncestryMismatchError(f"Line {production_line_id} belongs to site {line_row[2]}, not {site_id}")

                query = """
                    SELECT ps.id, ps.name, ps.company, pl.site_id, ps.production_line_id
                    FROM pp.production_station ps
                    JOIN pp.production_line pl ON pl.company = ps.company AND pl.id = ps.production_line_id
                    WHERE ps.company = %s AND pl.site_id = %s AND ps.production_line_id = %s AND ps.active
                """
                params: List[Any] = [company_id, site_id, production_line_id]
                if last_id:
                    query += " AND ps.id > %s"
                    params.append(last_id)
                query += " ORDER BY ps.id ASC LIMIT 101;"
                cur.execute(query, params)
                rows = cur.fetchall()
                truncated = len(rows) > 100
                items = [Station(id=r[0], name=r[1], company_id=r[2], site_id=r[3], production_line_id=r[4]) for r in rows[:100]]
                next_cursor = encode_cursor("stations", filters, items[-1].id) if truncated and items else None
                return items, next_cursor
    finally:
        conn.close()


def list_machines(
    company_id: str,
    site_id: str,
    production_line_id: str,
    station_id: str,
    cursor: Optional[str] = None,
    limit: int = 100,
) -> Tuple[List[Machine], Optional[str]]:
    filters = {"company_id": company_id, "site_id": site_id, "production_line_id": production_line_id, "station_id": station_id}
    last_id = decode_cursor(cursor, "machines", filters) if cursor else None
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT name FROM erp.company WHERE name = %s;", (company_id,))
                if not cur.fetchone():
                    raise ReferenceNotFoundError(f"Company {company_id} not found")

                cur.execute("SELECT id, company FROM pp.production_station WHERE id = %s;", (station_id,))
                st_row = cur.fetchone()
                if not st_row or st_row[1] != company_id:
                    raise ReferenceNotFoundError(f"Station {station_id} not found in company {company_id}")

                query = """
                    SELECT a.name AS id, a.asset_name AS name, mc.company, pl.site_id, ps.production_line_id, mc.station_id,
                           ae.site_warehouse AS suggested_warehouse_id,
                           CASE WHEN ae.site_warehouse IS NOT NULL THEN 'pp.asset_ext' ELSE NULL END AS mapping_source,
                           'pp.machine_context' AS ancestry_source
                    FROM pp.machine_context mc
                    JOIN erp.asset a ON a.name = mc.asset
                    JOIN pp.production_station ps ON ps.company = mc.company AND ps.id = mc.station_id
                    JOIN pp.production_line pl ON pl.company = ps.company AND pl.id = ps.production_line_id
                    LEFT JOIN pp.asset_ext ae ON ae.asset = a.name
                    WHERE mc.company = %s
                      AND pl.site_id = %s
                      AND ps.production_line_id = %s
                      AND mc.station_id = %s
                      AND a.status NOT IN ('Cancelled', 'Sold', 'Scrapped')
                      AND ps.active AND pl.active
                """
                params: List[Any] = [company_id, site_id, production_line_id, station_id]
                if last_id:
                    query += " AND a.name > %s"
                    params.append(last_id)
                query += " ORDER BY a.name ASC LIMIT 101;"
                cur.execute(query, params)
                rows = cur.fetchall()
                truncated = len(rows) > 100
                items = [
                    Machine(
                        id=r[0],
                        name=r[1],
                        company_id=r[2],
                        site_id=r[3],
                        production_line_id=r[4],
                        station_id=r[5],
                        suggested_warehouse_id=r[6],
                        mapping_source=r[7],
                        ancestry_source=r[8],
                    )
                    for r in rows[:100]
                ]
                next_cursor = encode_cursor("machines", filters, items[-1].id) if truncated and items else None
                return items, next_cursor
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Ancestry Validation & Derivation
# ----------------------------------------------------------------------

def resolve_and_validate_ancestry(
    cur: Any,
    company_id: str,
    site_id: Optional[str],
    production_line_id: Optional[str],
    station_id: Optional[str],
    machine_id: Optional[str],
    warehouse_id: Optional[str] = None,
    is_submit: bool = False,
    explicit_nulls: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Derive omitted ancestors from PostgreSQL database and validate AC hierarchy strictly."""
    explicit_nulls = explicit_nulls or set()

    # 1. Company scope validation
    cur.execute("SELECT name FROM erp.company WHERE name = %s;", (company_id,))
    if not cur.fetchone():
        raise ReferenceNotFoundError(f"Company '{company_id}' not found")

    # 2. Check explicit null ancestor with non-null descendant
    if "site_id" in explicit_nulls and (production_line_id is not None or station_id is not None or machine_id is not None):
        raise ContextAncestryMismatchError("Explicit null site_id with non-null descendant")
    if "production_line_id" in explicit_nulls and (station_id is not None or machine_id is not None):
        raise ContextAncestryMismatchError("Explicit null production_line_id with non-null descendant")
    if "station_id" in explicit_nulls and machine_id is not None:
        raise ContextAncestryMismatchError("Explicit null station_id with non-null machine_id")

    derived_site_id = site_id
    derived_line_id = production_line_id
    derived_station_id = station_id
    derived_machine_id = machine_id
    ancestry_source: Optional[str] = None
    warehouse_mapping_source: Optional[str] = None

    # 3. Machine derivation
    if machine_id:
        cur.execute("SELECT name, company, status FROM erp.asset WHERE name = %s;", (machine_id,))
        asset_row = cur.fetchone()
        if not asset_row or asset_row[1] != company_id:
            raise ReferenceNotFoundError(f"Asset '{machine_id}' not found in company '{company_id}'")
        if asset_row[2] in ("Cancelled", "Sold", "Scrapped"):
            raise InvalidProductionContextError(f"Asset '{machine_id}' status '{asset_row[2]}' is disallowed")

        cur.execute("""
            SELECT mc.station_id, ps.production_line_id, pl.site_id, pl.production_scope,
                   ps.active AS st_active, pl.active AS pl_active, psi.active AS si_active
            FROM pp.machine_context mc
            JOIN pp.production_station ps ON ps.company = mc.company AND ps.id = mc.station_id
            JOIN pp.production_line pl ON pl.company = ps.company AND pl.id = ps.production_line_id
            JOIN pp.production_site psi ON psi.company = pl.company AND psi.id = pl.site_id
            WHERE mc.asset = %s AND mc.company = %s;
        """, (machine_id, company_id))
        mc_row = cur.fetchone()
        if not mc_row:
            cur.execute("SELECT asset FROM pp.machine_context WHERE asset = %s;", (machine_id,))
            if not cur.fetchone():
                raise MachineContextUnavailableError(f"Machine '{machine_id}' has no machine_context mapping")
            raise ReferenceNotFoundError(f"Machine context company mismatch for '{machine_id}'")

        if not (mc_row[4] and mc_row[5] and mc_row[6]):
            raise InvalidProductionContextError("Inactive ancestry node in hierarchy")
        if mc_row[3] != "AC":
            raise InvalidProductionContextError(f"Production line scope is '{mc_row[3]}', required 'AC'")

        st_id, pl_id, si_id = mc_row[0], mc_row[1], mc_row[2]
        if station_id is not None and station_id != st_id:
            raise ContextAncestryMismatchError(f"Supplied station '{station_id}' differs from machine station '{st_id}'")
        if production_line_id is not None and production_line_id != pl_id:
            raise ContextAncestryMismatchError(f"Supplied line '{production_line_id}' differs from machine line '{pl_id}'")
        if site_id is not None and site_id != si_id:
            raise ContextAncestryMismatchError(f"Supplied site '{site_id}' differs from machine site '{si_id}'")

        derived_station_id = st_id
        derived_line_id = pl_id
        derived_site_id = si_id
        ancestry_source = "pp.machine_context"

        cur.execute("SELECT site_warehouse FROM pp.asset_ext WHERE asset = %s;", (machine_id,))
        ae_row = cur.fetchone()
        if ae_row and ae_row[0]:
            if not warehouse_id:
                warehouse_id = ae_row[0]
                warehouse_mapping_source = "pp.asset_ext"
            else:
                warehouse_mapping_source = "explicit"
        elif warehouse_id:
            warehouse_mapping_source = "explicit"

    elif station_id:
        cur.execute("""
            SELECT ps.id, ps.company, ps.production_line_id, ps.active,
                   pl.site_id, pl.production_scope, pl.active AS pl_active, psi.active AS si_active
            FROM pp.production_station ps
            JOIN pp.production_line pl ON pl.company = ps.company AND pl.id = ps.production_line_id
            JOIN pp.production_site psi ON psi.company = pl.company AND psi.id = pl.site_id
            WHERE ps.id = %s;
        """, (station_id,))
        ps_row = cur.fetchone()
        if not ps_row or ps_row[1] != company_id:
            raise ReferenceNotFoundError(f"Station '{station_id}' not found in company '{company_id}'")
        if not (ps_row[3] and ps_row[6] and ps_row[7]):
            raise InvalidProductionContextError("Inactive station or ancestor node")
        if ps_row[5] != "AC":
            raise InvalidProductionContextError(f"Production line scope is '{ps_row[5]}', required 'AC'")

        pl_id, si_id = ps_row[2], ps_row[4]
        if production_line_id is not None and production_line_id != pl_id:
            raise ContextAncestryMismatchError(f"Supplied line '{production_line_id}' differs from station line '{pl_id}'")
        if site_id is not None and site_id != si_id:
            raise ContextAncestryMismatchError(f"Supplied site '{site_id}' differs from station site '{si_id}'")

        derived_line_id = pl_id
        derived_site_id = si_id
        ancestry_source = "pp.production_station"
        if warehouse_id:
            warehouse_mapping_source = "explicit"

    elif production_line_id:
        cur.execute("""
            SELECT pl.id, pl.company, pl.site_id, pl.production_scope, pl.active, psi.active AS si_active
            FROM pp.production_line pl
            JOIN pp.production_site psi ON psi.company = pl.company AND psi.id = pl.site_id
            WHERE pl.id = %s;
        """, (production_line_id,))
        pl_row = cur.fetchone()
        if not pl_row or pl_row[1] != company_id:
            raise ReferenceNotFoundError(f"Production line '{production_line_id}' not found in company '{company_id}'")
        if not (pl_row[4] and pl_row[5]):
            raise InvalidProductionContextError("Inactive line or site node")
        if pl_row[3] != "AC":
            raise InvalidProductionContextError(f"Production line scope is '{pl_row[3]}', required 'AC'")

        si_id = pl_row[2]
        if site_id is not None and site_id != si_id:
            raise ContextAncestryMismatchError(f"Supplied site '{site_id}' differs from line site '{si_id}'")

        derived_site_id = si_id
        ancestry_source = "pp.production_line"
        if warehouse_id:
            warehouse_mapping_source = "explicit"

    elif site_id:
        cur.execute("SELECT id, company, active FROM pp.production_site WHERE id = %s;", (site_id,))
        si_row = cur.fetchone()
        if not si_row or si_row[1] != company_id:
            raise ReferenceNotFoundError(f"Site '{site_id}' not found in company '{company_id}'")
        if not si_row[2]:
            raise InvalidProductionContextError("Inactive site node")
        ancestry_source = "pp.production_site"
        if warehouse_id:
            warehouse_mapping_source = "explicit"

    # Warehouse validation
    if warehouse_id:
        if ".." in warehouse_id or "/" in warehouse_id or "\\" in warehouse_id:
            raise InvalidWarehouseError("Warehouse ID contains path traversal")
        cur.execute("SELECT name, company, disabled, is_group FROM erp.warehouse WHERE name = %s;", (warehouse_id,))
        wh_row = cur.fetchone()
        if not wh_row or wh_row[1] != company_id:
            raise ReferenceNotFoundError(f"Warehouse '{warehouse_id}' not found in company '{company_id}'")
        if wh_row[2] or wh_row[3]:
            raise InvalidWarehouseError(f"Warehouse '{warehouse_id}' is disabled or group")

    if is_submit:
        if not warehouse_id:
            raise IncompleteProductionContextError("Submit requires warehouse")
        if not (derived_site_id and derived_line_id and derived_station_id and derived_machine_id):
            raise IncompleteProductionContextError("Submit requires complete production ancestry (site, line, station, machine)")

    snapshot = None
    if ancestry_source:
        snapshot = {
            "company_id": company_id,
            "site_id": derived_site_id,
            "production_line_id": derived_line_id,
            "station_id": derived_station_id,
            "machine_id": derived_machine_id,
        }

    context_source: Dict[str, Any] = {
        "production_ancestry": {
            "source": ancestry_source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "snapshot": snapshot,
        }
    }
    if warehouse_mapping_source:
        context_source["warehouse_mapping"] = {
            "source": warehouse_mapping_source,
            "suggested_warehouse_id": warehouse_id,
        }

    return {
        "site_id": derived_site_id,
        "production_line_id": derived_line_id,
        "station_id": derived_station_id,
        "machine_id": derived_machine_id,
        "warehouse_id": warehouse_id,
        "context_source": context_source,
    }


# ----------------------------------------------------------------------
# Session Serialization Helper
# ----------------------------------------------------------------------

def serialize_session(row: Dict[str, Any], latest_job_id: Optional[str] = None) -> Dict[str, Any]:
    sid = str(row["id"])
    res = row.get("result") or {}
    inp = row.get("input") or {}
    ctx = row.get("context_source") or {
        "production_ancestry": {"source": None, "resolved_at": None, "snapshot": None}
    }
    created_at = row["created_at"].isoformat() if row.get("created_at") else None
    updated_at = row["updated_at"].isoformat() if row.get("updated_at") else None

    facts = res.get("facts", [])
    conflicts = [{"message": c} if isinstance(c, str) else c for c in res.get("conflicts", [])]
    questions = res.get("questions", [])
    candidates = res.get("candidates", [])
    truncated = bool(res.get("truncated", False))
    identified_item_code = None
    if res.get("identified_candidate"):
        cand = res["identified_candidate"]
        if isinstance(cand, dict):
            identified_item_code = cand.get("item_code")
    knowledge_refs = res.get("knowledge_refs", [])
    error = res.get("error")

    data = {
        "api_version": "wo-text-v2",
        "id": sid,
        "session_id": sid,
        "version": row["version"],
        "state": row["state"],
        "company_id": row["company"],
        "site_id": row.get("site_id"),
        "production_line_id": row.get("production_line_id"),
        "station_id": row.get("station_id"),
        "machine_id": row.get("asset"),
        "warehouse_id": row.get("warehouse"),
        "input": inp,
        "context_source": ctx,
        "clarification_round": row["clarification_round"],
        "input_revision": row["input_revision"],
        "explicit_retries": row["explicit_retries"],
        "job_id": latest_job_id,
        "description": inp.get("description"),
        "quantity": inp.get("quantity", "1"),
        "urgency": inp.get("urgency") or "Medium",
        "notes": inp.get("notes"),
        "input_kind": inp.get("input_kind", "text"),
        "facts": facts,
        "conflicts": conflicts,
        "questions": questions,
        "candidates": candidates,
        "truncated": truncated,
        "identified_item_code": identified_item_code,
        "knowledge_refs": knowledge_refs,
        "error": error,
        "result": res,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    return data


# ----------------------------------------------------------------------
# Work Order Session CRUD & Transitions
# ----------------------------------------------------------------------

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT * FROM pp.wo_identification_session WHERE id = %s;", (session_id,))
                row = cur.fetchone()
                if not row:
                    return None
                cur.execute("SELECT id FROM pp.wo_identification_job WHERE session_id = %s ORDER BY created_at DESC LIMIT 1;", (session_id,))
                job_row = cur.fetchone()
                latest_job_id = str(job_row["id"]) if job_row else None
                return serialize_session(row, latest_job_id)
    finally:
        conn.close()


def check_idempotency(cur: Any, scope: str, key: str, req_hash: str) -> Optional[Tuple[int, Dict[str, Any]]]:
    cur.execute("SELECT request_hash, response_status, response FROM pp.wo_identification_idempotency WHERE scope = %s AND key = %s;", (scope, key))
    row = cur.fetchone()
    if not row:
        return None
    stored_hash, status_code, resp_data = row[0], row[1], row[2]
    if stored_hash == req_hash:
        return status_code, resp_data
    raise IdempotencyConflictError("Idempotency-Key reused with different payload")


def record_idempotency(cur: Any, scope: str, key: str, req_hash: str, status_code: int, response_data: Dict[str, Any], session_id: Optional[str] = None) -> None:
    cur.execute("""
        INSERT INTO pp.wo_identification_idempotency (scope, key, request_hash, response_status, response, session_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (scope, key) DO UPDATE
        SET request_hash = EXCLUDED.request_hash,
            response_status = EXCLUDED.response_status,
            response = EXCLUDED.response;
    """, (scope, key, req_hash, status_code, json.dumps(response_data, default=str), session_id))


def create_draft(draft_data: Dict[str, Any], idempotency_key: Optional[str] = None, explicit_nulls: Optional[Set[str]] = None) -> Tuple[int, Dict[str, Any], bool]:
    req_hash = canonical_hash(draft_data)
    company_id = draft_data["company_id"]
    scope = f"create_{company_id}"
    if explicit_nulls is None:
        explicit_nulls = {k for k in ("site_id", "production_line_id", "station_id", "machine_id") if k in draft_data and draft_data[k] is None}

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT pg_backend_pid();")
                backend_pid = cur.fetchone()[0]

                if idempotency_key:
                    replay = check_idempotency(cur, scope, idempotency_key, req_hash)
                    if replay:
                        return replay[0], replay[1], True

                ancestry = resolve_and_validate_ancestry(
                    cur,
                    company_id=company_id,
                    site_id=draft_data.get("site_id"),
                    production_line_id=draft_data.get("production_line_id"),
                    station_id=draft_data.get("station_id"),
                    machine_id=draft_data.get("machine_id"),
                    warehouse_id=draft_data.get("warehouse_id"),
                    is_submit=False,
                    explicit_nulls=explicit_nulls,
                )

                session_id = str(uuid.uuid4())
                input_payload = {
                    "company_id": company_id,
                    "machine_id": ancestry["machine_id"],
                    "warehouse_id": ancestry["warehouse_id"],
                    "description": draft_data.get("description"),
                    "quantity": draft_data.get("quantity", "1"),
                    "urgency": draft_data.get("urgency") or "Medium",
                    "notes": draft_data.get("notes"),
                    "input_kind": draft_data.get("input_kind", "text"),
                    "site_id": ancestry["site_id"],
                    "production_line_id": ancestry["production_line_id"],
                    "station_id": ancestry["station_id"],
                }

                cur.execute("""
                    INSERT INTO pp.wo_identification_session (
                        id, company, asset, warehouse, site_id, production_line_id, station_id,
                        input, context_source, state, version, input_revision, clarification_round, explicit_retries
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft', 1, 1, 0, 0)
                    RETURNING *;
                """, (
                    session_id, company_id, ancestry["machine_id"], ancestry["warehouse_id"],
                    ancestry["site_id"], ancestry["production_line_id"], ancestry["station_id"],
                    json.dumps(input_payload, default=str),
                    json.dumps(ancestry["context_source"], default=str),
                ))
                col_names = [desc[0] for desc in cur.description]
                row_vals = cur.fetchone()
                row = dict(zip(col_names, row_vals))

                cur.execute("""
                    INSERT INTO pp.wo_identification_event (session_id, seq, event_type, input_revision, payload)
                    VALUES (%s, 1, 'draft_created', 1, %s);
                """, (session_id, json.dumps({"state": "draft", "input": input_payload}, default=str)))

                res_data = serialize_session(row)

                if idempotency_key:
                    record_idempotency(cur, scope, idempotency_key, req_hash, 201, res_data, session_id=session_id)

                context = {
                    "session_id": session_id,
                    "input_revision": 1,
                    "backend_pid": backend_pid,
                }
                _observe_boundary("mutation_before_commit", context)

        return 201, res_data, False
    finally:
        conn.close()


def update_draft(session_id: str, update_data: Dict[str, Any], idempotency_key: Optional[str] = None, explicit_nulls: Optional[Set[str]] = None) -> Tuple[int, Dict[str, Any], bool]:
    req_hash = canonical_hash(update_data)
    scope = f"update_{session_id}"
    if explicit_nulls is None:
        explicit_nulls = {k for k in ("site_id", "production_line_id", "station_id", "machine_id") if k in update_data and update_data[k] is None}

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT pg_backend_pid();")
                backend_pid = cur.fetchone()[0]

                if idempotency_key:
                    replay = check_idempotency(cur, scope, idempotency_key, req_hash)
                    if replay:
                        return replay[0], replay[1], True

                cur.execute("SELECT * FROM pp.wo_identification_session WHERE id = %s FOR UPDATE;", (session_id,))
                col_names = [desc[0] for desc in cur.description]
                raw_row = cur.fetchone()
                if not raw_row:
                    raise ReferenceNotFoundError(f"Session {session_id} not found")
                row = dict(zip(col_names, raw_row))

                if update_data.get("expected_version") != row["version"]:
                    raise VersionConflictError(f"Expected version {update_data.get('expected_version')} != current {row['version']}")
                if row["state"] != "draft":
                    raise StateConflictError(f"Session is in state {row['state']}, only draft can be updated")

                current_input = row.get("input") or {}
                merged_input = dict(current_input)
                for k, v in update_data.items():
                    if k != "expected_version":
                        merged_input[k] = v

                ancestry = resolve_and_validate_ancestry(
                    cur,
                    company_id=row["company"],
                    site_id=merged_input.get("site_id"),
                    production_line_id=merged_input.get("production_line_id"),
                    station_id=merged_input.get("station_id"),
                    machine_id=merged_input.get("machine_id"),
                    warehouse_id=merged_input.get("warehouse_id"),
                    is_submit=False,
                    explicit_nulls=explicit_nulls,
                )
                merged_input["site_id"] = ancestry["site_id"]
                merged_input["production_line_id"] = ancestry["production_line_id"]
                merged_input["station_id"] = ancestry["station_id"]
                merged_input["machine_id"] = ancestry["machine_id"]
                merged_input["warehouse_id"] = ancestry["warehouse_id"]

                cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM pp.wo_identification_event WHERE session_id = %s;", (session_id,))
                next_seq = cur.fetchone()[0]

                cur.execute("""
                    UPDATE pp.wo_identification_session
                    SET asset = %s,
                        warehouse = %s,
                        site_id = %s,
                        production_line_id = %s,
                        station_id = %s,
                        input = %s,
                        context_source = %s,
                        version = version + 1,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING *;
                """, (
                    ancestry["machine_id"], ancestry["warehouse_id"], ancestry["site_id"],
                    ancestry["production_line_id"], ancestry["station_id"],
                    json.dumps(merged_input, default=str),
                    json.dumps(ancestry["context_source"], default=str),
                    session_id,
                ))
                updated_row = dict(zip([desc[0] for desc in cur.description], cur.fetchone()))

                cur.execute("""
                    INSERT INTO pp.wo_identification_event (session_id, seq, event_type, input_revision, payload)
                    VALUES (%s, %s, 'draft_updated', %s, %s);
                """, (session_id, next_seq, row["input_revision"], json.dumps({"state": "draft", "input": merged_input}, default=str)))

                res_data = serialize_session(updated_row)

                if idempotency_key:
                    record_idempotency(cur, scope, idempotency_key, req_hash, 200, res_data, session_id=session_id)

                context = {
                    "session_id": session_id,
                    "input_revision": row["input_revision"],
                    "backend_pid": backend_pid,
                }
                _observe_boundary("mutation_before_commit", context)

        return 200, res_data, False
    finally:
        conn.close()


def submit_draft(session_id: str, expected_version: int, idempotency_key: Optional[str] = None) -> Tuple[int, Dict[str, Any], bool]:
    req_hash = canonical_hash({"expected_version": expected_version})
    scope = f"submit_{session_id}"

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT pg_backend_pid();")
                backend_pid = cur.fetchone()[0]

                if idempotency_key:
                    replay = check_idempotency(cur, scope, idempotency_key, req_hash)
                    if replay:
                        return replay[0], replay[1], True

                cur.execute("SELECT * FROM pp.wo_identification_session WHERE id = %s FOR UPDATE;", (session_id,))
                col_names = [desc[0] for desc in cur.description]
                raw_row = cur.fetchone()
                if not raw_row:
                    raise ReferenceNotFoundError(f"Session {session_id} not found")
                row = dict(zip(col_names, raw_row))

                if expected_version != row["version"]:
                    raise VersionConflictError(f"Expected version {expected_version} != current {row['version']}")
                if row["state"] != "draft":
                    raise StateConflictError(f"Session is in state {row['state']}, only draft can be submitted")

                input_data = row.get("input") or {}
                # Quantity validation
                qty_str = input_data.get("quantity")
                try:
                    qty_num = float(qty_str) if qty_str is not None else 0.0
                    if qty_num <= 0 or qty_num > 999999.999:
                        raise RepositoryError("invalid_quantity", "Submit quantity must be positive and <= 999999.999", 422)
                except (ValueError, TypeError):
                    raise RepositoryError("invalid_quantity", "Invalid quantity format", 422)

                desc = input_data.get("description")
                if not desc or not desc.strip():
                    raise RepositoryError("invalid_fields", "Description cannot be empty on submit", 422)

                # Re-validate complete ancestry
                ancestry = resolve_and_validate_ancestry(
                    cur,
                    company_id=row["company"],
                    site_id=row.get("site_id"),
                    production_line_id=row.get("production_line_id"),
                    station_id=row.get("station_id"),
                    machine_id=row.get("asset"),
                    warehouse_id=row.get("warehouse"),
                    is_submit=True,
                )

                # Queue capacity check
                cur.execute("SELECT count(*) FROM pp.wo_identification_job WHERE status IN ('queued', 'running');")
                queued_count = cur.fetchone()[0]
                if queued_count >= 100:
                    raise QueueFullError("Backpressure limit reached (100 queued/running jobs)")

                raw_submission = dict(input_data)
                job_id = str(uuid.uuid4())

                cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM pp.wo_identification_event WHERE session_id = %s;", (session_id,))
                next_seq = cur.fetchone()[0]

                cur.execute("""
                    UPDATE pp.wo_identification_session
                    SET state = 'queued',
                        version = version + 1,
                        raw_submission = %s,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING *;
                """, (json.dumps(raw_submission, default=str), session_id))
                updated_row = dict(zip([desc[0] for desc in cur.description], cur.fetchone()))

                cur.execute("""
                    INSERT INTO pp.wo_identification_job (id, session_id, input_revision, status, attempts, available_at, fence)
                    VALUES (%s, %s, %s, 'queued', 0, now(), 0);
                """, (job_id, session_id, updated_row["input_revision"]))

                cur.execute("""
                    INSERT INTO pp.wo_identification_event (session_id, seq, event_type, input_revision, payload)
                    VALUES (%s, %s, 'submitted', %s, %s);
                """, (session_id, next_seq, updated_row["input_revision"], json.dumps({
                    "state": "queued",
                    "session_id": session_id,
                    "job_id": job_id,
                    "input_revision": updated_row["input_revision"],
                    "raw_submission": raw_submission,
                }, default=str)))

                res_data = serialize_session(updated_row, latest_job_id=job_id)

                if idempotency_key:
                    record_idempotency(cur, scope, idempotency_key, req_hash, 202, res_data, session_id=session_id)

                context = {
                    "session_id": session_id,
                    "job_id": job_id,
                    "input_revision": updated_row["input_revision"],
                    "backend_pid": backend_pid,
                }
                _observe_boundary("mutation_before_commit", context)

        return 202, res_data, False
    finally:
        conn.close()


def submit_answers(session_id: str, expected_version: int, answers_list: List[Dict[str, Any]], idempotency_key: Optional[str] = None) -> Tuple[int, Dict[str, Any], bool]:
    req_hash = canonical_hash({"expected_version": expected_version, "answers": answers_list})
    scope = f"answers_{session_id}"

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT pg_backend_pid();")
                backend_pid = cur.fetchone()[0]

                if idempotency_key:
                    replay = check_idempotency(cur, scope, idempotency_key, req_hash)
                    if replay:
                        return replay[0], replay[1], True

                cur.execute("SELECT * FROM pp.wo_identification_session WHERE id = %s FOR UPDATE;", (session_id,))
                col_names = [desc[0] for desc in cur.description]
                raw_row = cur.fetchone()
                if not raw_row:
                    raise ReferenceNotFoundError(f"Session {session_id} not found")
                row = dict(zip(col_names, raw_row))

                if expected_version != row["version"]:
                    raise VersionConflictError(f"Expected version {expected_version} != current {row['version']}")
                if row["state"] != "awaiting_clarification":
                    raise StateConflictError(f"Session is in state {row['state']}, not awaiting_clarification")

                current_qs = (row.get("result") or {}).get("questions", [])
                expected_qids = {q["id"] for q in current_qs}
                provided_qids = [a["question_id"] for a in answers_list]

                if not expected_qids or set(provided_qids) != expected_qids or len(provided_qids) != len(expected_qids):
                    raise RepositoryError("invalid_answers", "Provided answers do not match current question IDs", 409)

                # A human, never the model, may resolve the form/text quantity
                # conflict. Preserve raw_submission; record this correction.
                confirmed_quantity = None
                for question in current_qs:
                    if question.get('key') != 'quantity_conflict':continue
                    answer = next(a['answer'] for a in answers_list if a['question_id']==question['id']).strip()
                    if not re.fullmatch(r'\d{1,6}(?:\.\d{1,3})?',answer) or Decimal(answer)<=0:
                        raise RepositoryError('invalid_quantity_answer','Jawab konflik jumlah dengan angka positif saja',422)
                    confirmed_quantity = answer
                if confirmed_quantity is not None:
                    cur.execute("UPDATE pp.wo_identification_session SET input=jsonb_set(input,'{quantity}',to_jsonb(%s::text)) WHERE id=%s",(confirmed_quantity,session_id))

                cur.execute("SELECT count(*) FROM pp.wo_identification_job WHERE status IN ('queued', 'running');")
                queued_count = cur.fetchone()[0]
                if queued_count >= 100:
                    raise QueueFullError("Backpressure limit reached (100 queued/running jobs)")

                new_input_revision = row["input_revision"] + 1
                new_round = row["clarification_round"] + 1
                job_id = str(uuid.uuid4())

                cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM pp.wo_identification_event WHERE session_id = %s;", (session_id,))
                next_seq = cur.fetchone()[0]

                cur.execute("""
                    UPDATE pp.wo_identification_session
                    SET state = 'queued',
                        version = version + 1,
                        input_revision = %s,
                        clarification_round = %s,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING *;
                """, (new_input_revision, new_round, session_id))
                updated_row = dict(zip([desc[0] for desc in cur.description], cur.fetchone()))

                cur.execute("""
                    INSERT INTO pp.wo_identification_job (id, session_id, input_revision, status, attempts, available_at, fence)
                    VALUES (%s, %s, %s, 'queued', 0, now(), 0);
                """, (job_id, session_id, new_input_revision))

                cur.execute("""
                    INSERT INTO pp.wo_identification_event (session_id, seq, event_type, input_revision, payload)
                    VALUES (%s, %s, 'answers_submitted', %s, %s);
                """, (session_id, next_seq, new_input_revision, json.dumps({
                    "session_id": session_id,
                    "answers": answers_list,
                    "confirmed_quantity": confirmed_quantity,
                    "job_id": job_id,
                    "input_revision": new_input_revision,
                }, default=str)))

                res_data = serialize_session(updated_row, latest_job_id=job_id)

                if idempotency_key:
                    record_idempotency(cur, scope, idempotency_key, req_hash, 202, res_data, session_id=session_id)

                context = {
                    "session_id": session_id,
                    "job_id": job_id,
                    "input_revision": new_input_revision,
                    "backend_pid": backend_pid,
                }
                _observe_boundary("mutation_before_commit", context)

        return 202, res_data, False
    finally:
        conn.close()


def retry_work_order(session_id: str, expected_version: int, idempotency_key: Optional[str] = None) -> Tuple[int, Dict[str, Any], bool]:
    req_hash = canonical_hash({"expected_version": expected_version})
    scope = f"retry_{session_id}"

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT pg_backend_pid();")
                backend_pid = cur.fetchone()[0]

                if idempotency_key:
                    replay = check_idempotency(cur, scope, idempotency_key, req_hash)
                    if replay:
                        return replay[0], replay[1], True

                cur.execute("SELECT * FROM pp.wo_identification_session WHERE id = %s FOR UPDATE;", (session_id,))
                col_names = [desc[0] for desc in cur.description]
                raw_row = cur.fetchone()
                if not raw_row:
                    raise ReferenceNotFoundError(f"Session {session_id} not found")
                row = dict(zip(col_names, raw_row))

                if expected_version != row["version"]:
                    raise VersionConflictError(f"Expected version {expected_version} != current {row['version']}")
                if row["state"] != "failed":
                    raise StateConflictError(f"Session is in state {row['state']}, only failed session can be retried")
                if row["explicit_retries"] >= 2:
                    raise RetriesExhaustedError("Max 2 explicit retry attempts per session")

                cur.execute("SELECT count(*) FROM pp.wo_identification_job WHERE status IN ('queued', 'running');")
                queued_count = cur.fetchone()[0]
                if queued_count >= 100:
                    raise QueueFullError("Backpressure limit reached (100 queued/running jobs)")

                new_input_revision = row["input_revision"] + 1
                new_retries = row["explicit_retries"] + 1
                job_id = str(uuid.uuid4())

                cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM pp.wo_identification_event WHERE session_id = %s;", (session_id,))
                next_seq = cur.fetchone()[0]

                cur.execute("""
                    UPDATE pp.wo_identification_session
                    SET state = 'queued',
                        version = version + 1,
                        input_revision = %s,
                        explicit_retries = %s,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING *;
                """, (new_input_revision, new_retries, session_id))
                updated_row = dict(zip([desc[0] for desc in cur.description], cur.fetchone()))

                cur.execute("""
                    INSERT INTO pp.wo_identification_job (id, session_id, input_revision, status, attempts, available_at, fence)
                    VALUES (%s, %s, %s, 'queued', 0, now(), 0);
                """, (job_id, session_id, new_input_revision))

                cur.execute("""
                    INSERT INTO pp.wo_identification_event (session_id, seq, event_type, input_revision, payload)
                    VALUES (%s, %s, 'retried', %s, %s);
                """, (session_id, next_seq, new_input_revision, json.dumps({
                    "session_id": session_id,
                    "explicit_retries": new_retries,
                    "job_id": job_id,
                    "input_revision": new_input_revision,
                }, default=str)))

                res_data = serialize_session(updated_row, latest_job_id=job_id)

                if idempotency_key:
                    record_idempotency(cur, scope, idempotency_key, req_hash, 202, res_data, session_id=session_id)

                context = {
                    "session_id": session_id,
                    "job_id": job_id,
                    "input_revision": new_input_revision,
                    "backend_pid": backend_pid,
                }
                _observe_boundary("mutation_before_commit", context)

        return 202, res_data, False
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Candidate Queries
# ----------------------------------------------------------------------

def get_scoped_candidates(
    company: str,
    warehouse: str,
    category: str = "Bearing",
    item_code: Optional[str] = None,
    item_name: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Query active stock items in exact scope:
    b JOIN i JOIN w WHERE w.company=company AND b.warehouse=warehouse AND i.item_group='Bearing'
    LIMIT 101; returns (candidates[:100], truncated).
    """
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                query = """
                    SELECT i.item_code, i.item_name, i.brand, i.description,
                           b.actual_qty, b.reserved_qty,
                           GREATEST(b.actual_qty - b.reserved_qty, 0) AS available_qty,
                           i.stock_uom, i.item_group
                    FROM erp.bin b
                    JOIN erp.item i ON i.item_code = b.item_code
                    JOIN erp.warehouse w ON w.name = b.warehouse
                    WHERE w.company = %s
                      AND b.warehouse = %s
                      AND i.item_group = %s
                      AND NOT i.disabled AND NOT w.disabled AND NOT w.is_group
                """
                params: List[Any] = [company, warehouse, category]
                if item_code:
                    query += " AND i.item_code = %s"
                    params.append(item_code)
                if item_name:
                    query += " AND i.item_name = %s"
                    params.append(item_name)
                query += " ORDER BY i.item_code ASC LIMIT 101;"
                cur.execute(query, params)
                rows = cur.fetchall()
                truncated = len(rows) > 100
                results = []
                for r in rows[:100]:
                    results.append({
                        "item_code": r[0],
                        "item_name": r[1],
                        "brand": r[2],
                        "description": r[3],
                        "actual_qty": str(r[4]) if r[4] is not None else None,
                        "reserved_qty": str(r[5]) if r[5] is not None else None,
                        "available_qty": str(r[6]) if r[6] is not None else None,
                        "stock_uom": r[7], "item_group": r[8],
                    })
                return results, truncated
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Worker Claim and Process Operations
# ----------------------------------------------------------------------

def claim_next_job(worker_id: str = "worker-01") -> Optional[Dict[str, Any]]:
    """Claim next available job using FOR UPDATE SKIP LOCKED with short transaction."""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 2000;")
                cur.execute("SELECT pg_backend_pid();")
                backend_pid = cur.fetchone()[0]

                cur.execute("SELECT pg_advisory_xact_lock(72451109);")

                # Check global active claims limit (max 2)
                cur.execute("""
                    SELECT count(*) FROM pp.wo_identification_job
                    WHERE status = 'running' AND lease_until > now();
                """)
                active_global = cur.fetchone()[0]
                if active_global >= 2:
                    return None

                # Find claimable job
                cur.execute("""
                    SELECT id, session_id, input_revision, status, attempts, fence
                    FROM pp.wo_identification_job
                    WHERE (status = 'queued' OR (status = 'running' AND lease_until <= now()))
                      AND attempts < 2
                      AND available_at <= now()
                      AND session_id NOT IN (
                          SELECT session_id FROM pp.wo_identification_job
                          WHERE status = 'running' AND lease_until > now()
                      )
                    ORDER BY available_at ASC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED;
                """)
                row = cur.fetchone()
                if not row:
                    return None

                job_id, session_id, input_revision, prev_status, attempts, fence = row
                new_attempts = attempts + 1
                new_fence = fence + 1

                cur.execute("""
                    UPDATE pp.wo_identification_job
                    SET status = 'running',
                        worker_id = %s,
                        attempts = %s,
                        fence = %s,
                        lease_until = now() + interval '90 seconds',
                        updated_at = now()
                    WHERE id = %s;
                """, (worker_id, new_attempts, new_fence, job_id))

                cur.execute("""
                    UPDATE pp.wo_identification_session
                    SET state = 'processing',
                        updated_at = now()
                    WHERE id = %s AND state IN ('queued', 'processing');
                """, (session_id,))

        context = {
            "session_id": str(session_id),
            "job_id": str(job_id),
            "input_revision": input_revision,
            "fence": new_fence,
            "backend_pid": backend_pid,
        }
        _observe_boundary("claim_after_commit", context)

        return {
            "id": str(job_id),
            "session_id": str(session_id),
            "input_revision": input_revision,
            "status": "running",
            "attempts": new_attempts,
            "fence": new_fence,
            "worker_id": worker_id,
        }
    except Exception:
        return None
    finally:
        conn.close()


# In-memory backwards-compatibility stub
class MemoryStore:
    pass

STORE = MemoryStore()

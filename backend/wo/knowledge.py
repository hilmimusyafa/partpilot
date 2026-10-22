"""Knowledge boundary and catalog note loading for PartPilot Backend Bundle v3."""

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_NOTES_DIR = REPO_ROOT / "backend" / "knowledge" / "PartPilot" / "catalog-notes"

# Allowlisted warehouse note mapping (static scope allowlist; never request-supplied paths)
ALLOWLISTED_SCOPES = {
    ("SYN-WH-01", "Bearing"): "SYN-WH-01/bearing.md",
    ("SYN-WH-02", "Bearing"): "SYN-WH-02/bearing.md",
    ("SYN-WH-03", "Bearing"): "SYN-WH-03/bearing.md",
    ("SYN-WH-04", "Bearing"): "SYN-WH-04/bearing.md",
    ("SYN-WH-05", "Bearing"): "SYN-WH-05/bearing.md",
}


def load_scoped_note(warehouse_id: str, category: str = "Bearing") -> Dict[str, Any]:
    """Load scoped catalog note for (warehouse_id, category).
    Validates static allowlist, prevents path traversal, checks frontmatter headers,
    computes SHA-256 digest, and returns content snapshot.
    Returns status 'available' or 'knowledge_unavailable'.
    """
    if not warehouse_id or not category:
        return {
            "status": "knowledge_unavailable",
            "reason": "missing_scope",
            "path": None,
            "sha256": None,
            "source_status": None,
            "snapshot_version": None,
            "content_snapshot": None,
        }

    # Strict path traversal / malicious scope rejection
    if ".." in warehouse_id or "/" in warehouse_id or "\\" in warehouse_id:
        return {
            "status": "knowledge_unavailable",
            "reason": "path_traversal_rejected",
            "path": None,
            "sha256": None,
            "source_status": None,
            "snapshot_version": None,
            "content_snapshot": None,
        }

    scope_key = (warehouse_id, category)
    rel_subpath = ALLOWLISTED_SCOPES.get(scope_key)
    if not rel_subpath:
        return {
            "status": "knowledge_unavailable",
            "reason": f"unknown_scope_or_category_{warehouse_id}_{category}",
            "path": None,
            "sha256": None,
            "source_status": None,
            "snapshot_version": None,
            "content_snapshot": None,
        }

    note_path = CATALOG_NOTES_DIR / rel_subpath
    if not note_path.exists() or not note_path.is_file():
        return {
            "status": "knowledge_unavailable",
            "reason": "note_file_not_found",
            "path": str(note_path.relative_to(REPO_ROOT)),
            "sha256": None,
            "source_status": None,
            "snapshot_version": None,
            "content_snapshot": None,
        }

    try:
        raw_text = note_path.read_text(encoding="utf-8")
        sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        # Parse YAML frontmatter
        if raw_text.startswith("---"):
            parts = raw_text.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
            else:
                frontmatter = {}
        else:
            frontmatter = {}

        # Header validation
        fm_warehouse = frontmatter.get("warehouse")
        fm_category = frontmatter.get("category")
        if fm_warehouse != warehouse_id or fm_category != category or frontmatter.get("naming_status") == "unknown":
            return {
                "status": "knowledge_unavailable",
                "reason": "unknown_naming_rules" if frontmatter.get("naming_status") == "unknown" else "header_mismatch",
                "path": str(note_path.relative_to(REPO_ROOT)),
                "sha256": sha256,
                "source_status": frontmatter.get("source_status", "UNKNOWN"),
                "snapshot_version": "v1",
                "content_snapshot": raw_text,
                "frontmatter": frontmatter,
            }

        return {
            "status": "available",
            "reason": None,
            "path": str(note_path.relative_to(REPO_ROOT)),
            "sha256": sha256,
            "source_status": frontmatter.get("source_status", "UNKNOWN"),
            "snapshot_version": "v1",
            "content_snapshot": raw_text,
            "frontmatter": frontmatter,
            "warehouse_id": warehouse_id,
            "category": category,
        }

    except Exception as e:
        return {
            "status": "knowledge_unavailable",
            "reason": f"read_error_{type(e).__name__}",
            "path": str(note_path.relative_to(REPO_ROOT)),
            "sha256": None,
            "source_status": None,
            "snapshot_version": None,
            "content_snapshot": None,
        }
